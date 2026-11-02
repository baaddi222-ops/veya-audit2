"""Unit tests (stdlib only) for db_guard.py and scan_repo.py."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
PROJECT = AUDIT.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, AUDIT / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DbGuard(unittest.TestCase):
    def setUp(self):
        self.g = load('db_guard')

    def test_local_dev_db_accepted(self):
        self.assertIsNone(self.g.check('postgresql://u:p@localhost:5432/veya'))

    def test_remote_host_refused(self):
        self.assertIn('not local', self.g.check('postgresql://u:p@db.example.com:5432/veya'))

    def test_production_name_refused(self):
        self.assertIn('production', self.g.check('postgresql://u:p@localhost/veya_prod'))

    def test_missing_url_refused(self):
        self.assertIn('not set', self.g.check(None))

    def test_migrate_requires_flag_and_throwaway_name(self):
        url = 'postgresql://u:p@127.0.0.1/veya'
        self.assertIn('VEYA_AUDIT_ALLOW_MIGRATE', self.g.check(url, True, None))
        self.assertIn('veya_audit', self.g.check(url, True, '1'))                       # real dev name refused
        self.assertIsNone(self.g.check('postgresql://u:p@127.0.0.1/veya_audit_1', True, '1'))
        self.assertIsNone(self.g.check('postgresql://u:p@127.0.0.1/something_test', True, '1'))

    def test_cli_exit_codes(self):
        env = {**os.environ, 'DATABASE_URL': 'postgresql://u:p@prod.example.com/x', 'VEYA_ROOT': str(PROJECT)}
        r = subprocess.run([sys.executable, str(AUDIT / 'db_guard.py')], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)
        env['DATABASE_URL'] = 'postgresql://u:p@localhost/veya'
        r = subprocess.run([sys.executable, str(AUDIT / 'db_guard.py')], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class ScanRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / 'p'
        # copy only SOURCE files: a developer's own .env / caches / venv must never make these tests fail
        shutil.copytree(PROJECT, self.root, ignore=shutil.ignore_patterns(
            '__pycache__', '.audit_logs', 'node_modules', '.venv', 'venv', '.env', '.pytest_cache', 'db.sqlite3', 'media_files', 'staticfiles', '.expo'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scan(self, *flags):
        r = subprocess.run([sys.executable, str(AUDIT / 'scan_repo.py'), *flags, str(self.root)], capture_output=True, text=True)
        return r.returncode, r.stdout

    def test_clean_project_passes_in_both_modes(self):
        self.assertEqual(self.scan()[0], 0, self.scan()[1])
        self.assertEqual(self.scan('--archive')[0], 0, self.scan('--archive')[1])

    def test_gitignored_env_tolerated_in_working_tree_but_not_in_archive(self):
        (self.root / 'backend' / '.env').write_text('DJANGO_SECRET_KEY=abc\n')     # backend/.gitignore lists .env
        self.assertEqual(self.scan()[0], 0)
        rc, out = self.scan('--archive')
        self.assertEqual(rc, 1)
        self.assertIn('backend/.env', out)

    def test_env_that_is_not_gitignored_is_a_finding(self):
        (self.root / 'tools' / '.env').write_text('X=1\n')
        rc, out = self.scan()
        self.assertEqual(rc, 1)
        self.assertIn('NOT git-ignored', out)

    def test_private_key_detected(self):
        (self.root / 'mobile' / 'src' / 'k.ts').write_text('const k = "-----BEGIN PRIVATE KEY-----";\n')
        rc, out = self.scan()
        self.assertEqual(rc, 1)
        self.assertIn('private key', out)

    def test_hardcoded_credential_detected(self):
        (self.root / 'backend' / 'config' / 'x.py').write_text("API_KEY = 'a1b2c3d4e5f6a7b8'\n")
        rc, out = self.scan()
        self.assertEqual(rc, 1)
        self.assertIn('hard-coded credential', out)

    def test_google_fonts_detected(self):
        (self.root / 'mobile' / 'src' / 'f.ts').write_text("const u = 'https://fonts.googleapis.com/css2?family=Inter';\n")
        rc, out = self.scan()
        self.assertEqual(rc, 1)
        self.assertIn('third-party font', out)

    def test_session_recorder_detected(self):
        (self.root / 'mobile' / 'src' / 'h.ts').write_text("import 'https://static.hotjar.com/c/hotjar.js';\n")
        self.assertEqual(self.scan()[0], 1)

    def test_console_in_mobile_detected(self):
        (self.root / 'mobile' / 'src' / 'c.ts').write_text("console.log(token);\n")
        rc, out = self.scan()
        self.assertEqual(rc, 1)
        self.assertIn('console.', out)

    def test_build_dirs_tolerated_in_working_tree_but_flagged_in_archive(self):
        (self.root / 'mobile' / 'node_modules').mkdir()
        (self.root / 'mobile' / 'node_modules' / 'x.js').write_text("console.log('dep'); fonts.googleapis.com\n")
        (self.root / 'backend' / '__pycache__').mkdir()
        (self.root / 'backend' / '.pytest_cache').mkdir()
        self.assertEqual(self.scan()[0], 0)                     # dependencies are not scanned, and are not a failure
        rc, out = self.scan('--archive')
        self.assertEqual(rc, 1)
        self.assertIn('node_modules', out)
        self.assertIn('__pycache__', out)

    def test_key_files_always_detected(self):
        (self.root / 'backend' / 'cert.pem').write_text('x')
        for flags in ((), ('--archive',)):
            rc, out = self.scan(*flags)
            self.assertEqual(rc, 1)
            self.assertIn('cert.pem', out)

    def test_audit_reports_are_tolerated_in_the_working_tree_only_because_they_are_gitignored(self):
        (self.root / '.gitignore').write_text('audit_report_*.txt\n.audit_logs/\n')     # self-contained: do not depend on the copy
        (self.root / 'audit_report_20261028.txt').write_text('environment details')
        self.assertEqual(self.scan()[0], 0)                       # ignored by .gitignore -> tolerated in the working tree
        rc, out = self.scan('--archive')
        self.assertEqual(rc, 1)
        self.assertIn('audit_report_20261028.txt', out)

    def test_shipped_root_gitignore_covers_local_audit_output(self):
        lines = (PROJECT / '.gitignore').read_text().split()
        self.assertIn('audit_report_*.txt', lines)
        self.assertIn('.audit_logs/', lines)

    def test_sqlite_tolerated_if_gitignored_flagged_in_archive(self):
        (self.root / 'backend' / 'db.sqlite3').write_bytes(b'x')
        self.assertEqual(self.scan()[0], 0)
        self.assertEqual(self.scan('--archive')[0], 1)


if __name__ == '__main__':
    unittest.main()
