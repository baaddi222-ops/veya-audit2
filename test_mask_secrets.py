import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('mask_secrets', Path(__file__).resolve().parents[1] / 'mask_secrets.py')
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)


class Mask(unittest.TestCase):
    def test_password_in_url(self):
        out = ms.mask('DATABASE_URL=postgresql://veya:hunter2@localhost:5432/veya')
        self.assertNotIn('hunter2', out)
        self.assertIn('localhost:5432/veya', out)

    def test_secret_assignments(self):
        for line in ['DJANGO_SECRET_KEY=abcdef123456', 'password: s3cr3t!', 'API_KEY = zzz999', 'auth_token=tok_123']:
            out = ms.mask(line)
            self.assertIn('***', out, line)
            for bad in ('abcdef123456', 's3cr3t', 'zzz999', 'tok_123'):
                self.assertNotIn(bad, out)

    def test_bearer_basic_and_header_values(self):
        for line, bad in [('sent Bearer abcdef123456 to server', 'abcdef123456'), ('Authorization: Basic dXNlcjpwYXNz', 'dXNlcjpwYXNz'),
                          ('Cookie: sessionid=abc123def; csrftoken=zzz999', 'abc123def'), ('Set-Cookie: sid=topsecretvalue; Path=/', 'topsecretvalue')]:
            out = ms.mask(line)
            self.assertNotIn(bad, out, line)

    def test_jwt_shape(self):
        out = ms.mask('Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMSJ9.abcDEF_123')
        self.assertNotIn('eyJhbGci', out)

    def test_literal_values_from_environment(self):
        lits = ms.literals_from_env({'DJANGO_SECRET_KEY': 'LONG-SECRET-VALUE', 'DATABASE_URL': 'postgresql://u:p4ssWord99@h/db'})
        out = ms.mask('the key LONG-SECRET-VALUE and p4ssWord99 appear here', lits)
        self.assertNotIn('LONG-SECRET-VALUE', out)
        self.assertNotIn('p4ssWord99', out)

    def test_short_db_password_does_not_garble_the_report(self):
        # regression: DATABASE_URL=postgresql://veya:veya@... used to turn every "veya" in the report into ***
        lits = ms.literals_from_env({'DATABASE_URL': 'postgresql://veya:veya@localhost:5432/veya_audit'})
        out = ms.mask('project veya2/backend, db url postgresql://veya:veya@localhost:5432/veya_audit', lits)
        self.assertIn('veya2/backend', out)
        self.assertNotIn(':veya@', out)                 # still masked in URL context

    def test_values_from_a_dotenv_file_are_masked_even_without_a_pattern(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / '.env'
            f.write_text('# comment\nDJANGO_SECRET_KEY="k3y-from-file-123"\nDATABASE_URL=postgresql://u:filePW99@localhost/db\n'
                         'EMAIL_HOST_PASSWORD=smtp-pass-777\nALLOWED_HOSTS=localhost\nSHORT_SECRET=abc\n')
            lits = ms.literals_from_env({}, f)
            out = ms.mask('trace: key k3y-from-file-123, pw filePW99, smtp smtp-pass-777, host localhost', lits)
            for bad in ('k3y-from-file-123', 'filePW99', 'smtp-pass-777'):
                self.assertNotIn(bad, out)
            self.assertIn('localhost', out)                 # non-secret settings are untouched

    def test_missing_dotenv_is_fine(self):
        self.assertEqual(ms.literals_from_env({}, '/definitely/not/here/.env'), [])

    def test_generic_secret_like_environment_variables_are_masked(self):
        lits = ms.literals_from_env({'EMAIL_HOST_PASSWORD': 'smtp-pass-777', 'PATH': '/usr/bin:/bin', 'HOME': '/root'})
        out = ms.mask('x smtp-pass-777 y /usr/bin:/bin', lits)
        self.assertNotIn('smtp-pass-777', out)
        self.assertIn('/usr/bin:/bin', out)

    def test_harmless_text_unchanged(self):
        s = 'PASS     [static]  model <-> migration consistency'
        self.assertEqual(ms.mask(s), s)


if __name__ == '__main__':
    unittest.main()
