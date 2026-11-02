#!/usr/bin/env bash
# Failure-injection self-test for run_all.sh: copies the project, injects ONE deliberate defect per case,
# runs the copy's run_all.sh and asserts (a) the exact exit code and (b) the expected status row.
# Proves that a failing check can never be reported as success and that BLOCKED is never PASS.
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; SRC="$(cd "$HERE/../.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
CASES=0; BAD=0; IDX=0; TOTAL_DEFINED=0
RANGE_FROM=1; RANGE_TO=999
if [ -n "${SELFTEST_RANGE:-}" ]; then RANGE_FROM="${SELFTEST_RANGE%-*}"; RANGE_TO="${SELFTEST_RANGE#*-}"; fi
in_range() { IDX=$((IDX + 1)); TOTAL_DEFINED=$IDX; [ "$IDX" -ge "$RANGE_FROM" ] && [ "$IDX" -le "$RANGE_TO" ]; }

case_run() {   # name expected_exit grep_pattern mutation_python [ENV=VAL ...]
  local name=$1 want=$2 pattern=$3 mut=$4; shift 4
  in_range || return 0
  local dir="$WORK/$(printf '%s' "$name" | tr -c 'A-Za-z0-9' '_')"
  mkdir -p "$dir"; cp -r "$SRC/backend" "$SRC/mobile" "$SRC/tools" "$SRC/docs" "$SRC/cloud" "$SRC/.gitignore" "$dir/"
  find "$dir" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  ( cd "$dir" && python3 -c "$mut" )
  local out="$dir.out" rc=0
  if env "$@" bash "$dir/tools/audit/run_all.sh" >"$out" 2>&1; then rc=0; else rc=$?; fi
  CASES=$((CASES + 1))
  local ok=yes
  [ "$rc" -eq "$want" ] || ok=no
  grep -Eq -- "$pattern" "$out" || ok=no
  if [ "$ok" = yes ]; then printf 'ok    %-52s exit=%s\n' "$name" "$rc"
  else BAD=$((BAD + 1)); printf 'FAIL  %-52s exit=%s (wanted %s) pattern=%s\n' "$name" "$rc" "$want" "$pattern"; tail -25 "$out" | sed 's/^/      | /'; fi
}
EDIT='import sys,pathlib
def edit(path, old, new):
    p = pathlib.Path(path); t = p.read_text()
    assert old in t, "mutation target missing: %r in %s" % (old, path)
    p.write_text(t.replace(old, new, 1))
'
# --- baseline: in a sandbox without Django/node_modules the honest result is exit 2 (INCOMPLETE), never 0 and never 1
case_run "baseline (no defects)"               2 '^== RESULT: INCOMPLETE' 'pass'
# --- each injected defect must turn into exit 1 with the matching FAIL row
case_run "serializer exposes __all__"          1 '^FAIL +\[static\] +backend/scripts/verify_boundaries.py' "$EDIT"'edit("backend/posts/serializers.py", "fields = [\"body\", \"image_id\"]" if False else "fields = ['"'"'body'"'"', '"'"'image_id'"'"']", "fields = '"'"'__all__'"'"'")'
case_run "migration max_length drift"          1 '^FAIL +\[static\] +model <-> migration' "$EDIT"'edit("backend/engagement/migrations/0001_initial.py", "models.CharField(max_length=300)", "models.CharField(max_length=200)")'
case_run "image pipeline accepts GIF"          1 '^FAIL +\[executed\] +media/processing.py' "$EDIT"'edit("backend/media/processing.py", "{'"'"'JPEG'"'"', '"'"'PNG'"'"', '"'"'WEBP'"'"'}", "{'"'"'JPEG'"'"', '"'"'PNG'"'"', '"'"'WEBP'"'"', '"'"'GIF'"'"'}")'
case_run "image pipeline keeps EXIF orientation" 1 '^FAIL +\[executed\] +media/processing.py' "$EDIT"'edit("backend/media/processing.py", "ImageOps.exif_transpose(img)", "img")'
case_run "JWT decode bug re-introduced (naive atob)" 1 '^FAIL +\[shim\] +mobile pure-function tests' "$EDIT"'edit("mobile/src/auth/AuthContext.tsx", ".replace(/-/g, \"+\").replace(/_/g, \"/\")" if False else ".replace(/-/g, '"'"'+'"'"').replace(/_/g, '"'"'/'"'"')", "")'
case_run "TypeScript syntax error"             1 '^FAIL +\[static\] +mobile TypeScript syntax' 'open("mobile/src/posts/types.ts","a").write("\nconst broken = ;\n")'
case_run "real undefined identifier in TS"     1 '^FAIL +\[static\] +mobile TypeScript syntax' 'open("mobile/src/posts/types.ts","a").write("\nexport const bad: number = notDefinedAnywhere;\n")'
case_run "broken relative import in TS"        1 '^FAIL +\[static\] +mobile TypeScript syntax' 'open("mobile/src/posts/types.ts","a").write("\nimport { x } from \"./does-not-exist\";\nexport const y = x;\n")'
case_run ".env that is NOT git-ignored"        1 '^FAIL +\[static\] +repo hygiene' 'open("tools/audit/.env","w").write("DJANGO_SECRET_KEY=abc\n")'
case_run "private key file in the tree"         1 '^FAIL +\[static\] +repo hygiene' 'open("backend/cert.pem","w").write("x")'
# --- developer leftovers must NOT cause a false alarm: git-ignored backend/.env, __pycache__, .pytest_cache (exit 2, not 1)
case_run "git-ignored .env + pytest/pyc leftovers" 2 '^PASS +\[static\] +repo hygiene' 'import os; open("backend/.env","w").write("DJANGO_SECRET_KEY=abc\n"); os.makedirs("backend/.pytest_cache"); os.makedirs("backend/__pycache__")'
case_run "Google Fonts CDN in app source"      1 '^FAIL +\[static\] +repo hygiene' 'open("mobile/src/f.ts","w").write("export const u = \"https://fonts.googleapis.com/css2?family=Inter\";\n")'
case_run "verify script crashes (exit 7)"      1 '^FAIL +\[static\] +backend/scripts/verify_boundaries.py' 'open("backend/scripts/verify_boundaries.py","w").write("raise SystemExit(7)\n")'
case_run "required tool file deleted"          1 '^FAIL +\[shim\] +mobile pure-function tests' 'import os; os.remove("tools/audit/run_ts_tests.js")'
case_run "checker silently stops comparing"    1 '^FAIL +\[executed\] +audit tools self-tests' "$EDIT"'edit("tools/audit/check_migrations.py", "for k in sorted(set(sig['"'"'kw'"'"']) | set(msig['"'"'kw'"'"'])):", "for k in []:")'
case_run "interpreter missing (PYTHON=/nonexistent)" 1 '^FAIL +\[static\] +backend/scripts/verify_boundaries.py' 'pass' PYTHON=/nonexistent
# --- BLOCKED must stay BLOCKED (exit 2), never PASS and never FAIL
case_run "tsc+node+Pillow missing -> BLOCKED"  2 '^BLOCKED +\[static\] +mobile TypeScript syntax' 'pass' 'VEYA_AUDIT_FORCE_MISSING=tsc node PIL'
case_run "BLOCKED rows are not counted as PASS" 2 'BLOCKED +\[executed\] +media/processing.py' 'pass' 'VEYA_AUDIT_FORCE_MISSING=PIL'


# --- compliance logic: a regression in the age rule / token check / redaction must FAIL the audit (exit 1)
case_run "age rule off-by-one (under-age accepted)"  1 '^FAIL +\[executed\] +backend pure-logic tests' "$EDIT"'edit("backend/accounts/age.py", "if age < minimum:", "if age < minimum - 1:")'
case_run "unsubscribe token signature not checked"  1 '^FAIL +\[executed\] +backend pure-logic tests' "$EDIT"'edit("backend/mailing/tokens.py", "if not hmac.compare_digest(sig, _sig(secret, payload)):", "if False:")'
case_run "log redaction of JWTs removed"            1 '^FAIL +\[executed\] +backend pure-logic tests' "$EDIT"'edit("backend/securitylog/redaction.py", "[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]*'"'"'), '"'"'[jwt]'"'"'),", "XX'"'"'), '"'"'[jwt]'"'"'),")'
case_run "undefined name in backend code"           1 '^FAIL +\[static\] +backend Python static checks' 'open("backend/accounts/views.py","a").write("\nVALUE = this_name_does_not_exist\n")'
case_run "broken local import in backend code"      1 '^FAIL +\[static\] +backend Python static checks' 'open("backend/accounts/views.py","a").write("\nfrom accounts.models import NoSuchModel\n")'
case_run "pure module imports Django (testability lost)" 1 '^FAIL +\[executed\] +backend pure-logic tests' "$EDIT"'edit("backend/accounts/age.py", "from datetime import date", "from datetime import date\nimport django")'

# --- report tooling: secrets from backend/.env and the environment must never reach the shared report
case_report() {
  in_range || return 0
  local dir="$WORK/report_case"; mkdir -p "$dir"; cp -r "$SRC/backend" "$SRC/mobile" "$SRC/tools" "$SRC/docs" "$SRC/cloud" "$SRC/.gitignore" "$dir/"
  find "$dir" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  printf 'DJANGO_SECRET_KEY=zz-super-secret-key-9999\nDATABASE_URL=postgresql://u:dbpw-777@localhost/veya_audit\nEMAIL_HOST_PASSWORD=smtp-pass-4242\n' > "$dir/backend/.env"
  # a failing test that prints every secret -> run_all shows the log lines -> collect_report copies them into the report
  cat > "$dir/backend/tests/pure/test_leak.py" <<'PY'
import unittest
class Leak(unittest.TestCase):
    def test_leak(self):
        print("leaked: zz-super-secret-key-9999 dbpw-777 smtp-pass-4242 Bearer abcdef123456 eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMSJ9.sig_value_123")
        self.fail("deliberate failure with secrets in the output")
PY
  local out="$dir/report.txt" rc=0 pyout="$dir.out"
  CASES=$((CASES + 1))
  if DJANGO_SECRET_KEY=zz-super-secret-key-9999 bash "$dir/tools/audit/collect_report.sh" "$out" >"$pyout" 2>&1; then rc=0; else rc=$?; fi
  local ok=yes
  [ "$rc" -eq 1 ] || ok=no
  [ -s "$out" ] || ok=no
  grep -q "leaked:" "$out" || ok=no                                           # the failing log really is in the report ...
  for secret in zz-super-secret-key-9999 dbpw-777 smtp-pass-4242 abcdef123456 sig_value_123; do
    if grep -q -- "$secret" "$out" 2>/dev/null; then ok=no; echo "      secret leaked into report: $secret"; fi   # ... but masked
  done
  grep -q "VERDICT: FAILURES" "$out" || ok=no
  if [ "$ok" = yes ]; then printf 'ok    %-52s exit=%s\n' "report masks .env + env secrets" "$rc"
  else BAD=$((BAD + 1)); printf 'FAIL  %-52s exit=%s (wanted 1)\n' "report masks .env + env secrets" "$rc"; tail -15 "$pyout" | sed 's/^/      | /'; fi
}
case_report

case_report_incomplete() {
  in_range || return 0
  local dir="$WORK/report_incomplete"; mkdir -p "$dir"; cp -r "$SRC/backend" "$SRC/mobile" "$SRC/tools" "$SRC/docs" "$SRC/cloud" "$SRC/.gitignore" "$dir/"
  find "$dir" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  local out="$dir/report.txt" rc=0
  CASES=$((CASES + 1))
  if PYTHON=/nonexistent bash "$dir/tools/audit/collect_report.sh" "$out" >"$dir.out" 2>&1; then rc=0; else rc=$?; fi
  if [ "$rc" -eq 3 ] && [ ! -e "$out" ] && grep -q "report generation FAILED" "$dir.out"; then printf 'ok    %-52s exit=%s\n' "report generator failure is loud (exit 3)" "$rc"
  else BAD=$((BAD + 1)); printf 'FAIL  %-52s exit=%s (wanted 3, no report file)\n' "report generator failure is loud (exit 3)" "$rc"; tail -8 "$dir.out" | sed 's/^/      | /'; fi
}
case_report_incomplete

echo; echo "self-test: $CASES case(s) run (of $TOTAL_DEFINED defined${SELFTEST_RANGE:+, range $SELFTEST_RANGE}), $BAD failed"
[ "$BAD" -eq 0 ]
