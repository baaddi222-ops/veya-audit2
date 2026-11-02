#!/usr/bin/env bash
# Verifies a release archive exactly as a recipient would receive it:
#   bash tools/audit/verify_archive.sh path/to/archive.zip
# 1) extracts to a temp dir  2) scan_repo.py --archive (strict: no .env/keys/db/build dirs)  3) run_all.sh on the extracted copy.
# Exit: 0 only if the strict scan passed AND run_all.sh exited 0; 1 if the scan failed or run_all FAILED; 2 if only BLOCKED/NOT_RUN remain.
set -Eeuo pipefail
ZIP="${1:?usage: verify_archive.sh archive.zip}"
PY="${PYTHON:-python3}"; export PYTHONDONTWRITEBYTECODE=1
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
command -v unzip >/dev/null || { echo "unzip not found"; exit 4; }
unzip -q "$ZIP" -d "$TMP"
ROOT="$(find "$TMP" -maxdepth 2 -type d -name tools -printf '%h\n' | head -n 1)"
[ -n "$ROOT" ] || { echo "no project (tools/) found inside $ZIP"; exit 1; }
HERE="$ROOT/tools/audit"
scan_rc=0; "$PY" "$HERE/scan_repo.py" --archive "$ROOT" || scan_rc=$?
run_rc=0; bash "$HERE/run_all.sh" >"$TMP/run_all.out" 2>&1 || run_rc=$?
grep -E '^== (SUMMARY|RESULT)' "$TMP/run_all.out" || true
echo "archive scan exit: $scan_rc | run_all.sh exit: $run_rc"
[ "$scan_rc" -eq 0 ] || exit 1
exit "$run_rc"
