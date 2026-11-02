#!/usr/bin/env python3
"""Repository hygiene + compliance scan (stdlib only). Exit 1 if anything is found.
Two modes:
  default (working tree; used by run_all.sh): build/env directories (node_modules, .venv, __pycache__, .pytest_cache ...) are skipped,
      and a `.env` / `*.sqlite3` file is tolerated ONLY when a .gitignore in its folder or a parent ignores it (it can't be committed).
  --archive (strict; use on a zip's extracted contents): ANY .env, key file, database, or build/env directory is a finding.
Always checked: private keys / certificates / service files, hard-coded credentials (tests, docs, migrations excluded),
  console.* in mobile source (may log tokens), third-party font / CDN / analytics / session-recording hosts (fonts must be self-hosted).
Usage: python3 scan_repo.py [--archive] [project_root]"""
import fnmatch
import re
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
ARCHIVE = '--archive' in sys.argv[1:]
ROOT = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[2]
ENV_LIKE = {'.env', 'db.sqlite3'}   # (+ audit_report_*.txt, see below)
ENV_LIKE_SUFFIX = ('.sqlite3',)
ALWAYS_BAD_NAMES = {'google-services.json', 'GoogleService-Info.plist'}
ALWAYS_BAD_SUFFIX = ('.pem', '.key', '.p12', '.jks', '.keystore', '.pfx')
BAD_DIRS = {'node_modules', '.venv', 'venv', '__pycache__', '.expo', 'media_files', '.audit_logs', '.pytest_cache', 'staticfiles'}
CODE_SUFFIX = {'.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.sh', '.html', '.css', '.yml', '.yaml', '.toml', '.cfg', '.ini'}
SKIP_PARTS = {'tests', '__tests__', 'migrations', 'docs', 'tools', 'scripts'}
SECRET_RES = [
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AWS access key id'),
    (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'), 'private key block'),
    (re.compile(r'\bsk-[A-Za-z0-9]{20,}'), 'API secret key (sk-...)'),
    (re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}'), 'Slack token'),
    (re.compile(r'\bghp_[A-Za-z0-9]{30,}'), 'GitHub token'),
    (re.compile(r'(?i)(?:secret|api[_-]?key|token|passw(?:or)?d|private[_-]?key)\s*[:=]\s*[\'"]([^\'"\s]{8,})[\'"]'), 'hard-coded credential'),
]
PLACEHOLDER = re.compile(r'(?i)change-me|example|placeholder|your[-_]|xxxx|<.*>')
THIRD_PARTY = re.compile(
    r'fonts\.googleapis\.com|fonts\.gstatic\.com|use\.typekit\.net|fast\.fonts\.net|cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|'
    r'googletagmanager\.com|google-analytics\.com|connect\.facebook\.net|hotjar\.com|fullstory\.com|logrocket\.com|mouseflow\.com|'
    r'clarity\.ms|smartlook\.com', re.I)
findings = []


def rel(p): return p.relative_to(ROOT).as_posix()


def gitignored(p: Path) -> bool:
    """True if a .gitignore in p's folder or any parent (up to ROOT) matches p (simple patterns: names, globs, dir/)."""
    d = p.parent
    while True:
        gi = d / '.gitignore'
        if gi.exists():
            relpath = p.relative_to(d).as_posix()
            for raw in gi.read_text().splitlines():
                pat = raw.strip()
                if not pat or pat.startswith('#') or pat.startswith('!'):
                    continue
                pat = pat.rstrip('/')
                if fnmatch.fnmatch(p.name, pat) or fnmatch.fnmatch(relpath, pat) or pat in relpath.split('/'):
                    return True
        if d == ROOT or ROOT not in d.parents:
            return False
        d = d.parent


for p in ROOT.rglob('*'):
    parts = set(p.relative_to(ROOT).parts)
    in_bad_dir = bool(parts & BAD_DIRS)
    if p.is_dir():
        if p.name in BAD_DIRS and ARCHIVE:
            findings.append(f'{rel(p)}/: directory must not be part of the archive')
        continue
    if in_bad_dir:
        continue                      # not descended into: working-tree mode tolerates; archive mode already flagged the directory
    name = p.name
    if name in ALWAYS_BAD_NAMES or name.endswith(ALWAYS_BAD_SUFFIX) or re.match(r'(?i)serviceaccount.*\.json$', name) or name.startswith('id_rsa'):
        findings.append(f'{rel(p)}: secret / credential / key file in the tree')
        continue
    if name in ENV_LIKE or name.endswith(ENV_LIKE_SUFFIX) or (name.startswith('audit_report_') and name.endswith('.txt')):
        if ARCHIVE:
            findings.append(f'{rel(p)}: environment/database file must not be in an archive')
        elif not gitignored(p):
            findings.append(f'{rel(p)}: environment/database file that is NOT git-ignored (could be committed)')
        continue
    if p.suffix.lower() not in CODE_SUFFIX or parts & SKIP_PARTS:
        continue
    try:
        text = p.read_text(errors='ignore')
    except OSError:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        for rx, label in SECRET_RES:
            if rx.search(line) and not PLACEHOLDER.search(line):
                findings.append(f'{rel(p)}:{lineno}: {label}')
        if THIRD_PARTY.search(line):
            findings.append(f'{rel(p)}:{lineno}: third-party font/CDN/analytics/session-recording host (self-host instead)')
        if rel(p).startswith('mobile/') and re.search(r'\bconsole\.(log|debug|info|warn|error)\b', line):
            findings.append(f'{rel(p)}:{lineno}: console.* call in mobile source (may log tokens)')

gi = ROOT / 'mobile' / '.gitignore'
if gi.exists() and '.env' not in gi.read_text().split():
    findings.append('mobile/.gitignore: does not ignore .env')

mode = 'archive' if ARCHIVE else 'working tree'
if findings:
    print(f'FAIL ({mode}) — {len(findings)} finding(s):')
    for f in findings:
        print('  -', f)
    sys.exit(1)
print(f'OK ({mode}) — no secrets, key files, console.* calls or third-party font/CDN/analytics hosts found.')
