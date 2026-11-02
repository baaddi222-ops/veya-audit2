#!/usr/bin/env bash
# Installs the backend/mobile toolchains WHEN a package index is reachable. It never runs the tests, never runs
# migrations, never starts a server. Exit codes: 0 installed, 4 BLOCKED (no network / missing base tool), other = failure.
#   usage: tools/audit/bootstrap.sh [--backend-only|--mobile-only]
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
want_backend=yes; want_mobile=yes
[ "${1:-}" = "--backend-only" ] && want_mobile=no
[ "${1:-}" = "--mobile-only" ] && want_backend=no

reach() { python3 - "$1" <<'PY'
import sys, urllib.request
try:
    urllib.request.urlopen(sys.argv[1], timeout=8).read(1)
except Exception as e:
    print(f"unreachable: {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)
PY
}

if [ "$want_backend" = yes ]; then
  command -v python3 >/dev/null || { echo "BLOCKED: python3 not found"; exit 4; }
  reach "https://pypi.org/simple/pip/" || { echo "BLOCKED: PyPI is not reachable from this machine — cannot install Django & co. Use a machine/CI with network access."; exit 4; }
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install --upgrade pip
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements-dev.txt"
  echo "backend: installed into backend/.venv  (activate: source backend/.venv/bin/activate)"
fi
if [ "$want_mobile" = yes ]; then
  command -v node >/dev/null && command -v npm >/dev/null || { echo "BLOCKED: node/npm not found"; exit 4; }
  reach "https://registry.npmjs.org/expo" || { echo "BLOCKED: the npm registry is not reachable from this machine — cannot install Expo/Jest."; exit 4; }
  cd "$ROOT/mobile"
  if [ -f package-lock.json ]; then npm ci; else npm install && echo "created mobile/package-lock.json — commit it, then use 'npm ci' from now on"; fi
  echo "mobile: dependencies installed"
fi
