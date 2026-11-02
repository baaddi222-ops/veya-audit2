#!/usr/bin/env bash
# ONE command for a CLOUD environment (GitHub Actions, GitHub Codespaces, Google Cloud Shell, ...): installs dependencies,
# runs the whole audit against a THROW-AWAY PostgreSQL and writes ONE masked report. Built for working from a phone.
#   bash tools/audit/cloud_run.sh              # database already provided via DATABASE_URL (CI service container)
#   bash tools/audit/cloud_run.sh --start-db   # start a throw-away Postgres with docker (Codespaces / Cloud Shell)
#   bash tools/audit/cloud_run.sh --check      # print the plan and exit 0 (installs nothing, touches nothing)
# Exit: run_all.sh's code (0 = everything ran and passed, 1 = failure, 2 = something still blocked) | 4 = BLOCKED (no network) | 5 = setup failed
# Never uses production data/secrets: the DB is a local throw-away; DJANGO_SECRET_KEY is generated for this run only.
set -Eeuo pipefail
umask 077
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="${VEYA_ROOT:-$(cd "$HERE/../.." && pwd)}"
OUT="${VEYA_CLOUD_OUT:-$ROOT/cloud_out}"
START_DB=no; CHECK=no
for arg in "$@"; do
  case "$arg" in
    --start-db) START_DB=yes;;
    --check) CHECK=yes;;
    *) echo "unknown option: $arg (use --start-db or --check)" >&2; exit 2;;
  esac
done
DB_PASSWORD="audit_pw_8f3k2x"    # throw-away, only for the local test database (never reuse anywhere real)
export DATABASE_URL="${DATABASE_URL:-postgresql://veya:${DB_PASSWORD}@localhost:5432/veya_audit}"

plan() {
  local dbline="use DATABASE_URL (must be a local throw-away database)"
  [ "$START_DB" = yes ] && dbline="start a throw-away postgres:16 container with docker"
  cat <<EOF
VEYA cloud audit plan (root: $ROOT)
  1. check that PyPI and the npm registry are reachable (else exit 4 = BLOCKED)
  2. database: $dbline
  3. create backend/.venv and pip install -r backend/requirements-dev.txt
  4. npm install in mobile/ (creates package-lock.json -> copied to $OUT)
  5. export throw-away DJANGO_SECRET_KEY / VEYA_AUDIT_ALLOW_MIGRATE=1 (database name must be veya_audit*)
  6. bash tools/audit/collect_report.sh  (runs run_all.sh: manage.py check, makemigrations --check, showmigrations, pytest, migrate, tsc, jest ...)
  7. results in $OUT : audit_report.txt (masked), logs/ (full masked logs), package-lock.json, SUMMARY.md
EOF
}
if [ "$CHECK" = yes ]; then plan; exit 0; fi

reach() { python3 - "$1" <<'PY'
import sys, urllib.request
try:
    urllib.request.urlopen(sys.argv[1], timeout=10).read(1)
except Exception as e:
    print(f"unreachable: {type(e).__name__}", file=sys.stderr); sys.exit(1)
PY
}
mkdir -p "$OUT/logs"
command -v python3 >/dev/null && command -v node >/dev/null && command -v npm >/dev/null || { echo "BLOCKED: python3, node and npm are required"; exit 4; }
reach https://pypi.org/simple/pip/ && reach https://registry.npmjs.org/expo || { echo "BLOCKED: PyPI / npm registry are not reachable from this environment (no network) — nothing was installed or run."; exit 4; }

if [ "$START_DB" = yes ]; then
  command -v docker >/dev/null || { echo "BLOCKED: docker not available here; provide DATABASE_URL to a local throw-away Postgres instead"; exit 4; }
  docker rm -f veya-audit-db >/dev/null 2>&1 || true
  docker run -d --name veya-audit-db -e POSTGRES_USER=veya -e POSTGRES_PASSWORD="$DB_PASSWORD" -e POSTGRES_DB=veya_audit -p 5432:5432 postgres:16 >/dev/null
fi

python3 -m venv "$ROOT/backend/.venv"
# shellcheck disable=SC1091
. "$ROOT/backend/.venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$ROOT/backend/requirements-dev.txt" || { echo "setup failed: pip install"; exit 5; }
( cd "$ROOT/mobile" && npm install --no-audit --no-fund --loglevel=error ) || { echo "setup failed: npm install"; exit 5; }
[ -f "$ROOT/mobile/package-lock.json" ] && cp "$ROOT/mobile/package-lock.json" "$OUT/package-lock.json"

echo "waiting for the database..."
python3 - <<'PY' || { echo "setup failed: database not reachable at DATABASE_URL"; exit 5; }
import os, sys, time
import psycopg
url = os.environ["DATABASE_URL"]
for _ in range(60):
    try:
        psycopg.connect(url, connect_timeout=3).close(); sys.exit(0)
    except Exception:
        time.sleep(2)
sys.exit(1)
PY

export DJANGO_SECRET_KEY="$(python3 -c 'import secrets;print(secrets.token_urlsafe(50))')"
export DJANGO_SETTINGS_MODULE="config.settings.dev" ALLOWED_HOSTS="127.0.0.1,localhost" VEYA_AUDIT_ALLOW_MIGRATE=1
export VEYA_COLLECT_FULL_LOGS_DIR="$OUT/logs"

rc=0
bash "$HERE/collect_report.sh" "$OUT/audit_report.txt" || rc=$?

{
  echo "# VEYA audit — result"
  echo
  echo "**run_all.sh exit code: $rc** (0 = all checks ran and passed · 1 = a check FAILED · 2 = something still blocked/not run)"
  echo
  [ "$START_DB" = yes ] && echo "_Database: throw-away postgres:16 container (docker)._" || echo "_Database: DATABASE_URL (local throw-away)._"
  echo
  echo '```'
  grep -E '^(PASS|FAIL|BLOCKED|NOT_RUN) |^== (SUMMARY|RESULT)' "$OUT/audit_report.txt" 2>/dev/null | cut -c1-200 || true
  echo '```'
  echo
  echo "Full masked report: audit_report.txt · full logs: logs/ · generated lock file: package-lock.json (commit it so 'npm ci' works)"
} > "$OUT/SUMMARY.md"
[ -n "${GITHUB_STEP_SUMMARY:-}" ] && { cat "$OUT/SUMMARY.md"; echo; echo '<details><summary>Masked report (first 400 lines)</summary>'; echo; echo '```'; head -n 400 "$OUT/audit_report.txt" 2>/dev/null; echo '```'; echo '</details>'; } >> "$GITHUB_STEP_SUMMARY"

echo "done. run_all.sh exit code: $rc ; results in $OUT"
exit "$rc"
