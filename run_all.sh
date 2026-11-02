#!/usr/bin/env bash
# VEYA audit runner. Every check reports exactly one of:
#   PASS     the check ran and succeeded
#   FAIL     the check ran and failed (or crashed)
#   BLOCKED  the check could not run here (missing tool / dependency / network / unsafe DB target)
#   NOT_RUN  deliberately not run (needs an explicit opt-in or a missing prerequisite file)
# and an evidence kind:  executed | static | shim   (shim = custom runner, NOT Jest / NOT Django)
#
# Exit code:  0 = every check PASSED   1 = at least one FAIL   2 = no FAIL, but something BLOCKED / NOT_RUN
#             (so a blocked environment can NEVER look like a pass)       other non-zero = the runner itself crashed
# Nothing here installs packages, touches production, or applies migrations without an explicit opt-in.
set -Eeuo pipefail
trap 'echo "run_all.sh: runner crashed near line $LINENO (exit $?)" >&2' ERR

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${VEYA_ROOT:-$(cd "$HERE/../.." && pwd)}"
BACKEND="$ROOT/backend"; MOBILE="$ROOT/mobile"
umask 077                          # logs may contain test output: owner-only
export PYTHONDONTWRITEBYTECODE=1   # the audit must not dirty the tree it is checking
LOGDIR="${VEYA_AUDIT_LOGDIR:-${TMPDIR:-/tmp}/veya_audit_$(printf '%s' "$ROOT" | cksum | cut -d' ' -f1)}"; JSOUT="$LOGDIR/js"
mkdir -p "$LOGDIR"
PY="${PYTHON:-python3}"

N_PASS=0; N_FAIL=0; N_BLOCKED=0; N_NOTRUN=0

report() {            # status kind name [note]
  printf '%-8s %-9s %s%s\n' "$1" "[$2]" "$3" "${4:+ — $4}"
  case "$1" in
    PASS) N_PASS=$((N_PASS + 1));; FAIL) N_FAIL=$((N_FAIL + 1));;
    BLOCKED) N_BLOCKED=$((N_BLOCKED + 1));; NOT_RUN) N_NOTRUN=$((N_NOTRUN + 1));;
  esac
}
slug() { printf '%s' "$1" | tr -c 'A-Za-z0-9\n' '_'; }
# test hook so the self-test can simulate a missing tool without touching PATH
have() { case " ${VEYA_AUDIT_FORCE_MISSING:-} " in *" $1 "*) return 1;; esac; command -v "$1" >/dev/null 2>&1; }
pymod() { case " ${VEYA_AUDIT_FORCE_MISSING:-} " in *" $1 "*) return 1;; esac; "$PY" -c "import $1" >/dev/null 2>&1; }

run_cmd() {           # name kind cmd...   — exit code of cmd decides; nothing is piped, nothing is masked
  local name=$1 kind=$2; shift 2
  local log="$LOGDIR/$(slug "$name").log" rc=0
  if "$@" >"$log" 2>&1; then rc=0; else rc=$?; fi
  if [ "$rc" -eq 0 ]; then
    report PASS "$kind" "$name"
  else
    report FAIL "$kind" "$name" "exit $rc, log: ${log#"$ROOT"/}"
    show_log "$log"
  fi
}
show_log() { local n=0 line; while IFS= read -r line && [ "$n" -lt 40 ]; do printf '    | %s\n' "$line"; n=$((n + 1)); done <"$1" || true; }
blocked() { report BLOCKED "$2" "$1" "$3"; }
notrun()  { report NOT_RUN "$2" "$1" "$3"; }

echo "== VEYA audit — root: $ROOT"
echo "== environment: $("$PY" --version 2>&1) | node $(have node && node --version || echo none) | tsc $(have tsc && tsc --version || echo none)"
echo

# ---------------------------------------------------------------- A. checks that need only Python
echo "-- A. offline checks (python only)"
for s in verify_boundaries.py verify_serializer_boundaries.py verify_placeholder_username.py; do
  if [ -f "$BACKEND/scripts/$s" ]; then run_cmd "backend/scripts/$s" static "$PY" "$BACKEND/scripts/$s"
  else report FAIL static "backend/scripts/$s" "file missing"; fi
done
if [ -f "$HERE/check_migrations.py" ]; then
  run_cmd "model <-> migration consistency (ast; NOT Django's autodetector)" static "$PY" "$HERE/check_migrations.py" "$BACKEND"
else report FAIL static "check_migrations.py" "file missing"; fi
if [ -f "$HERE/check_python_static.py" ]; then
  run_cmd "backend Python static checks (syntax, local imports, undefined names)" static "$PY" "$HERE/check_python_static.py" "$BACKEND"
else report FAIL static "check_python_static.py" "file missing"; fi
if [ -d "$BACKEND/tests/pure" ]; then
  run_cmd "backend pure-logic tests (age rules, security-log helpers, redaction, tokens, e-mail policy)" executed "$PY" -m unittest discover -s "$BACKEND/tests/pure" -t "$BACKEND"
else report FAIL executed "backend pure-logic tests" "backend/tests/pure missing"; fi
if [ -d "$HERE/tests" ]; then
  run_cmd "audit tools self-tests (checker, db_guard, scan_repo)" executed "$PY" -m unittest discover -s "$HERE/tests"
else report FAIL executed "audit tools self-tests" "tests/ missing"; fi
if [ -f "$HERE/scan_repo.py" ]; then
  run_cmd "repo hygiene: secrets, build dirs, console.*, third-party fonts/CDN/analytics" static "$PY" "$HERE/scan_repo.py" "$ROOT"
else report FAIL static "scan_repo.py" "file missing"; fi

# ---------------------------------------------------------------- B. image pipeline (needs Pillow)
echo; echo "-- B. image pipeline (real Pillow, Django stubbed)"
if pymod PIL; then
  if [ -f "$HERE/run_media_harness.py" ]; then
    VEYA_BACKEND="$BACKEND" run_cmd "media/processing.py + media/signing.py harness" executed "$PY" "$HERE/run_media_harness.py"
  else report FAIL executed "media harness" "file missing"; fi
else blocked "media/processing.py + media/signing.py harness" executed "Pillow is not installed"; fi

# ---------------------------------------------------------------- C. mobile, offline
echo; echo "-- C. mobile (offline)"
ts_syntax_check() {   # tsc's own exit code is inspected, never ignored; see classification below
  rm -rf "$JSOUT"
  # Use the project's PINNED compiler (mobile/package.json: typescript ~5.6.3) when installed; the runner's global
  # tsc may be a much newer major (CI run: 7.0.2) that has REMOVED moduleResolution=node10 (TS5108).
  local TSC=tsc; [ -x "$MOBILE/node_modules/.bin/tsc" ] && TSC="$MOBILE/node_modules/.bin/tsc"
  local tsmajor; tsmajor="$("$TSC" --version | sed -E 's/[^0-9]*([0-9]+)\..*/\1/')"
  if [ "${tsmajor:-0}" -ge 7 ]; then echo "global tsc major $tsmajor has removed moduleResolution=node10 and project deps (pinned TS 5.6) are not installed: cannot run the syntax check"; return 1; fi
  local deprec=""; if [ "${tsmajor:-0}" -ge 6 ]; then deprec='"ignoreDeprecations":"6.0",'; fi
  cat >"$LOGDIR/tsconfig.emit.json" <<JSON
{"compilerOptions":{$deprec"outDir":"$JSOUT","rootDir":"$MOBILE/src","module":"commonjs","target":"es2020","jsx":"react",
"skipLibCheck":true,"moduleResolution":"node","esModuleInterop":true,"types":[],"lib":["es2020","dom"],"noEmitOnError":false},
"include":["$MOBILE/src/**/*"]}
JSON
  local out="$LOGDIR/tsc_emit.log" rc=0
  if "$TSC" -p "$LOGDIR/tsconfig.emit.json" >"$out" 2>&1; then rc=0; else rc=$?; fi
  # syntax errors (TS1xxx) and the TS5107-style config errors are never acceptable; everything else goes through
  # the strict classifier (only 'package not installed' consequences are tolerated).
  local cls=0
  "$PY" "$HERE/classify_tsc.py" "$out" || cls=$?
  [ "$cls" -eq 0 ] || { echo "tsc reported real errors (see above)"; return 1; }
  [ -f "$JSOUT/__tests__/decodeUserId.test.js" ] || { echo "emit produced no output"; return 1; }
  echo "ok: transpiled; no real errors. TYPES ARE NOT VERIFIED (packages not installed)."
}
TS_OK=no
if have tsc && [ -d "$MOBILE/src" ]; then
  log="$LOGDIR/tsc_syntax.log"
  if ts_syntax_check >"$log" 2>&1; then TS_OK=yes; report PASS static "mobile TypeScript syntax + transpile (types NOT verified)"
  else report FAIL static "mobile TypeScript syntax + transpile" "log: ${log#"$ROOT"/}"; show_log "$log"; fi
else blocked "mobile TypeScript syntax + transpile" static "tsc not available"; fi

if ! have node; then blocked "mobile pure-function tests (shim runner, NOT Jest)" shim "node not available"
elif [ ! -f "$HERE/run_ts_tests.js" ]; then report FAIL shim "mobile pure-function tests" "run_ts_tests.js missing"
elif [ "$TS_OK" != yes ]; then notrun "mobile pure-function tests (shim runner, NOT Jest)" shim "needs the TypeScript transpile above to PASS"
else run_cmd "mobile pure-function tests (shim runner, NOT Jest)" shim node "$HERE/run_ts_tests.js" "$JSOUT"; fi

# ---------------------------------------------------------------- D. real Django / PostgreSQL / pytest
echo; echo "-- D. Django + PostgreSQL + pytest (real)"
django_blockers=(); missing_mods=()
for m in django rest_framework rest_framework_simplejwt environ corsheaders psycopg pytest pytest_django; do
  pymod "$m" || missing_mods+=("$m")
done
[ "${#missing_mods[@]}" -eq 0 ] || django_blockers+=("python modules not installed: ${missing_mods[*]}")
{ [ -n "${DJANGO_SECRET_KEY:-}" ] && [ -n "${DATABASE_URL:-}" ]; } || [ -f "$BACKEND/.env" ] || django_blockers+=("no DJANGO_SECRET_KEY/DATABASE_URL in env or backend/.env")
DJ_NAMES=("manage.py check" "makemigrations --check --dry-run" "showmigrations" "pytest (all backend tests incl. permissions/integration over the API client)" "migrate on a fresh throw-away database")
if [ "${#django_blockers[@]}" -gt 0 ]; then
  reason="$(IFS='; '; echo "${django_blockers[*]}")"
  for n in "${DJ_NAMES[@]}"; do blocked "$n" executed "$reason"; done
else
  guard_rc=0; guard_out="$("$PY" "$HERE/db_guard.py")" || guard_rc=$?
  if [ "$guard_rc" -ne 0 ]; then
    for n in "${DJ_NAMES[@]}"; do blocked "$n" executed "DB guard: $guard_out"; done
  else
    mg() { ( cd "$BACKEND" && "$PY" manage.py "$@" ); }
    run_cmd "manage.py check" executed mg check
    run_cmd "makemigrations --check --dry-run" executed mg makemigrations --check --dry-run
    run_cmd "showmigrations" executed mg showmigrations
    run_cmd "pytest (all backend tests incl. permissions/integration over the API client)" executed bash -c "cd '$BACKEND' && '$PY' -m pytest -q -ra"
    mg_rc=0; mg_out="$("$PY" "$HERE/db_guard.py" --for-migrate)" || mg_rc=$?
    if [ "$mg_rc" -eq 0 ]; then run_cmd "migrate on a fresh throw-away database" executed mg migrate
    else notrun "migrate on a fresh throw-away database" executed "$mg_out"; fi
  fi
fi

# ---------------------------------------------------------------- E. real Jest / tsc (need node_modules)
echo; echo "-- E. mobile (real toolchain)"
if [ ! -f "$MOBILE/package-lock.json" ]; then
  notrun "npm ci" executed "no package-lock.json shipped: run 'npm install' once (needs network) and commit the lock file"
elif [ ! -d "$MOBILE/node_modules" ]; then notrun "npm ci" executed "lock file present but node_modules missing: run 'npm ci' (needs network)"
else report PASS executed "dependencies present (node_modules + package-lock.json)"; fi
if [ -x "$MOBILE/node_modules/.bin/tsc" ] && ! have __force_no_npm__ && [ -z "${VEYA_AUDIT_FORCE_MISSING:-}" ]; then
  run_cmd "npx tsc --noEmit (real project types)" executed bash -c "cd '$MOBILE' && npx tsc --noEmit"
else blocked "npx tsc --noEmit (real project types)" executed "mobile/node_modules not installed"; fi
if [ -x "$MOBILE/node_modules/.bin/jest" ] && [ -z "${VEYA_AUDIT_FORCE_MISSING:-}" ]; then
  run_cmd "npx jest --runInBand (real Jest incl. AuthContext.test.tsx)" executed bash -c "cd '$MOBILE' && npx jest --runInBand"
else blocked "npx jest --runInBand (real Jest incl. AuthContext.test.tsx)" executed "mobile/node_modules not installed"; fi
blocked "Expo app on emulator/device + end-to-end walkthrough" executed "needs a running backend + emulator/device (manual; see docs/RUN_BLOCKED_CHECKS.md)"

# ---------------------------------------------------------------- summary
echo
echo "== SUMMARY: PASS=$N_PASS FAIL=$N_FAIL BLOCKED=$N_BLOCKED NOT_RUN=$N_NOTRUN"
if [ "$N_FAIL" -gt 0 ]; then
  echo "== RESULT: FAIL — $N_FAIL check(s) failed (exit 1)"; exit 1
elif [ $((N_BLOCKED + N_NOTRUN)) -gt 0 ]; then
  echo "== RESULT: INCOMPLETE — nothing failed, but $((N_BLOCKED + N_NOTRUN)) mandatory check(s) did not run. NOT certified (exit 2)"; exit 2
fi
echo "== RESULT: PASS — every check ran and passed (exit 0)"; exit 0
