#!/usr/bin/env python3
"""stdin -> stdout filter that removes secrets from a report before it is shared.
Masks: passwords inside URLs, SECRET/PASSWORD/TOKEN/API_KEY assignments, JWT-looking strings, the literal values of
DJANGO_SECRET_KEY / DATABASE_URL (+ its password) from the ENVIRONMENT, and the secret-looking values found in
backend/.env (so a value that appears in a traceback or log is masked even if it matches no pattern)."""
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

PATTERNS = [
    (re.compile(r'(://[^:/\s@]+:)[^@\s]+(@)'), r'\1***\2'),
    (re.compile(r'(?i)\b([A-Z0-9_]*(?:SECRET|PASSWORD|PASSWD|TOKEN|API_?KEY|PRIVATE_?KEY)[A-Z0-9_]*)\s*([=:])\s*\S+'), r'\1\2***'),
    (re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*'), '***jwt***'),
    (re.compile(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{6,}'), r'\1 ***'),
    (re.compile(r'(?i)\b(Authorization|Cookie|Set-Cookie)\s*:\s*\S.*'), r'\1: ***'),
]
SECRET_KEY_RE = re.compile(r'(?i)(SECRET|PASSWORD|PASSWD|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL|DATABASE_URL|DSN)')
# Literal (anywhere-in-text) replacement is only safe for values that cannot occur inside ordinary words/paths; a 4-letter
# password such as 'veya' would otherwise garble the whole report. Short passwords are still masked IN CONTEXT
# (inside URLs, KEY=value pairs) by PATTERNS above. Use throwaway passwords of 8+ characters.
MIN_LITERAL = 8


def _add_value(out, key, value):
    value = value.strip().strip('"\'')
    if not value or len(value) < MIN_LITERAL or not SECRET_KEY_RE.search(key):
        return
    out.add(value)
    if '://' in value:
        try:
            pw = urlparse(value).password
        except ValueError:
            pw = None
        if pw and len(pw) >= MIN_LITERAL:
            out.add(pw)


def literals_from_env(env=None, env_file=None):
    env = os.environ if env is None else env
    out = set()
    for key, value in env.items():
        _add_value(out, key, str(value))
    if env_file and Path(env_file).is_file():
        for line in Path(env_file).read_text(errors='ignore').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            _add_value(out, key.strip(), value)
    return sorted(out, key=len, reverse=True)


def mask(text, literals=()):
    for lit in literals:
        text = text.replace(lit, '***')
    for rx, rep in PATTERNS:
        text = rx.sub(rep, text)
    return text


if __name__ == '__main__':
    root = Path(os.environ.get('VEYA_ROOT', Path(__file__).resolve().parents[2]))
    lits = literals_from_env(env_file=root / 'backend' / '.env')
    for line in sys.stdin:
        sys.stdout.write(mask(line, lits))
