#!/usr/bin/env bash
# One command for the CONNECTED machine: runs the whole audit and writes ONE text file you can send back.
#   cd <PROJECT_ROOT> && bash tools/audit/collect_report.sh            -> ./audit_report_<timestamp>.txt
# Secrets (DB passwords, SECRET_KEY, tokens) are masked. Exit code = run_all.sh's exit code (0 only if EVERYTHING ran and passed).
set -Eeuo pipefail
umask 077
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="${VEYA_ROOT:-$(cd "$HERE/../.." && pwd)}"
PY="${PYTHON:-python3}"; export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$ROOT/audit_report_$(date +%Y%m%d_%H%M%S).txt}"
export VEYA_AUDIT_LOGDIR="$(mktemp -d)"
trap 'rm -rf "$VEYA_AUDIT_LOGDIR"' EXIT
section() { printf '\n######## %s\n' "$1"; }
v() { if command -v "$1" >/dev/null 2>&1; then "$@" 2>&1 | head -n 1 || true; else echo "(not installed)"; fi; }

rc=0; gen_rc=0
bash "$HERE/run_all.sh" >"$VEYA_AUDIT_LOGDIR/_run_all.out" 2>&1 || rc=$?   # rc is recorded below and is this script's exit code

{
  echo "VEYA audit report — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "project root: $ROOT"
  section "ENVIRONMENT"
  echo "os:      $(uname -sr 2>/dev/null || echo unknown)"
  echo "python:  $("$PY" --version 2>&1)"
  echo "pip:     $(v "$PY" -m pip --version)"
  echo "node:    $(v node --version)"
  echo "npm:     $(v npm --version)"
  echo "tsc:     $(v tsc --version)"
  echo "docker:  $(v docker --version)"
  echo "psql:    $(v psql --version)"
  echo "python packages of interest:"
  "$PY" -m pip list 2>/dev/null | grep -iE '^(django|djangorestframework|djangorestframework-simplejwt|django-cors-headers|django-environ|psycopg|pillow|pytest|pytest-django) ' || echo "  (none of them installed)"
  section "run_all.sh OUTPUT"
  cat "$VEYA_AUDIT_LOGDIR/_run_all.out"
  section "DETAIL LOGS (first 300 lines each)"
  for f in "$VEYA_AUDIT_LOGDIR"/*.log; do
    [ -e "$f" ] || continue
    printf '\n--- %s\n' "$(basename "$f")"
    head -n 300 "$f"
  done
  section "RESULT"
  echo "run_all.sh exit code: $rc   (0 = everything ran and passed, 1 = something FAILED, 2 = nothing failed but some checks could not run)"
  case "$rc" in
    0) echo "VERDICT: all mandatory checks executed and passed";;
    1) echo "VERDICT: FAILURES — do not edit migrations or permission rules; send this file";;
    2) echo "VERDICT: INCOMPLETE — BLOCKED/NOT_RUN checks remain (see rows above)";;
    *) echo "VERDICT: the runner itself crashed";;
  esac
} 2>&1 | "$PY" "$HERE/mask_secrets.py" >"$OUT.partial" || gen_rc=$?
if [ "${gen_rc:-0}" -ne 0 ] || ! grep -q '^######## RESULT' "$OUT.partial"; then
  echo "report generation FAILED or is incomplete (generator exit ${gen_rc:-0}); partial output kept at $OUT.partial" >&2
  exit 3
fi
mv "$OUT.partial" "$OUT"

# Optional: also keep the FULL (masked) detail logs, e.g. the complete pytest output (the report keeps only 300 lines per log).
if [ -n "${VEYA_COLLECT_FULL_LOGS_DIR:-}" ]; then
  mkdir -p "$VEYA_COLLECT_FULL_LOGS_DIR"
  for f in "$VEYA_AUDIT_LOGDIR"/*.log "$VEYA_AUDIT_LOGDIR"/_run_all.out; do
    [ -e "$f" ] || continue
    "$PY" "$HERE/mask_secrets.py" <"$f" >"$VEYA_COLLECT_FULL_LOGS_DIR/$(basename "$f").txt"
  done
fi

echo "report written: $OUT   (run_all.sh exit code: $rc)"
exit "$rc"
