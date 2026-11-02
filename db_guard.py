#!/usr/bin/env python3
"""Refuses to let audit tooling touch anything that does not look like a local throw-away database.
  python3 db_guard.py            -> DATABASE_URL host must be local (localhost/127.0.0.1/::1/db/postgres)
  python3 db_guard.py --for-migrate -> additionally: env VEYA_AUDIT_ALLOW_MIGRATE=1 AND database name starts with
                                      'veya_audit' or ends with '_test'
Reads DATABASE_URL from the environment, else from backend/.env. Exit 0 = allowed, 3 = refused (reason on stdout)."""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', 'db', 'postgres'}


def load_url(backend_dir: Path):
    url = os.environ.get('DATABASE_URL')
    if url:
        return url
    env = backend_dir / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith('DATABASE_URL='):
                return line.split('=', 1)[1].strip().strip('"\'')
    return None


def check(url, for_migrate=False, allow_flag=None):
    if not url:
        return 'DATABASE_URL is not set (env or backend/.env)'
    u = urlparse(url)
    host = (u.hostname or '').lower()
    name = (u.path or '').lstrip('/')
    if host not in LOCAL_HOSTS:
        return f'refused: database host {host!r} is not local (allowed: {sorted(LOCAL_HOSTS)})'
    if any(w in name.lower() for w in ('prod', 'production', 'live')):
        return f'refused: database name {name!r} looks like production'
    if for_migrate:
        if allow_flag != '1':
            return 'refused: set VEYA_AUDIT_ALLOW_MIGRATE=1 to allow `migrate` on a throw-away database'
        if not (name.startswith('veya_audit') or name.endswith('_test')):
            return f"refused: for `migrate` the database name must start with 'veya_audit' or end with '_test' (got {name!r})"
    return None


def main(argv):
    backend = Path(os.environ.get('VEYA_ROOT', Path(__file__).resolve().parents[2])) / 'backend'
    problem = check(load_url(backend), '--for-migrate' in argv, os.environ.get('VEYA_AUDIT_ALLOW_MIGRATE'))
    if problem:
        print(problem)
        return 3
    print('database target accepted as local / throw-away')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
