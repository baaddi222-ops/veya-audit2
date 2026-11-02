"""Safe tests for cloud_run.sh: only the paths that install nothing and touch nothing (syntax, --check, bad option)."""
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'cloud_run.sh'
WORKFLOW = Path(__file__).resolve().parents[3] / 'cloud' / 'audit.yml'


def run(*args):
    return subprocess.run(['bash', str(SCRIPT), *args], capture_output=True, text=True, timeout=30)


class CloudRun(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(subprocess.run(['bash', '-n', str(SCRIPT)], capture_output=True).returncode, 0)

    def test_check_prints_the_plan_and_exits_zero(self):
        r = run('--check')
        self.assertEqual(r.returncode, 0)
        for step in ('reachable', 'pip install', 'npm install', 'collect_report.sh', 'SUMMARY.md'):
            self.assertIn(step, r.stdout)
        self.assertIn('use DATABASE_URL', r.stdout)
        self.assertNotIn('nouse', r.stdout)

    def test_start_db_changes_the_plan(self):
        self.assertIn('throw-away postgres:16', run('--check', '--start-db').stdout)

    def test_unknown_option_is_refused(self):
        r = run('--bogus')
        self.assertEqual(r.returncode, 2)

    def test_workflow_uses_no_repository_secrets_and_least_privilege(self):
        y = WORKFLOW.read_text()
        import re
        self.assertIsNone(re.search(r'\$\{\{\s*secrets\.', y), 'the workflow must not read repository secrets')
        self.assertIsNone(re.search(r'\$\{\{\s*github\.token', y))
        self.assertIn('contents: read', y)
        self.assertIn('retention-days: 7', y)
        self.assertIn('if: always()', y)

    def test_workflow_database_is_a_local_throwaway_with_a_guarded_name(self):
        y = WORKFLOW.read_text()
        self.assertIn('POSTGRES_DB: veya_audit', y)
        self.assertIn('@localhost:5432/veya_audit', y)


if __name__ == '__main__':
    unittest.main()
