"""Self-tests for tools/audit/check_migrations.py using only the standard library:
    python3 -m unittest discover -s tools/audit/tests -v
Each test copies backend/ to a temp dir, injects ONE deliberate defect (the mutation target text must
exist, otherwise the test fails — so a test can never pass vacuously), and asserts the checker reports it.
The checker is only trusted as far as these tests show; it is still not Django's autodetector."""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[2] / 'backend'
spec = importlib.util.spec_from_file_location('check_migrations', HERE.parent / 'check_migrations.py')
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / 'backend'
        shutil.copytree(BACKEND, self.root, ignore=shutil.ignore_patterns('__pycache__', '.venv', 'media_files'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def mutate(self, rel, old, new, count=1):
        p = self.root / rel
        text = p.read_text()
        self.assertIn(old, text, f'mutation target not found in {rel!r}: {old!r} (test would be vacuous)')
        p.write_text(text.replace(old, new, count))

    def run_checker(self):
        return cm.Project(self.root).run()

    def assert_reports(self, needle):
        p = self.run_checker()
        self.assertTrue(any(needle in x for x in p.problems),
                        f'expected a problem containing {needle!r}; got: {p.problems}')


class CleanTree(Base):
    def test_clean_project_has_no_problems_and_nothing_unverified(self):
        p = self.run_checker()
        self.assertEqual(p.problems, [])
        self.assertEqual(p.unverified, [])
        on_disk = sorted(d.name for d in self.root.iterdir()
                         if d.is_dir() and (d / 'models.py').exists() and d.name not in cm.NOT_APPS)
        self.assertEqual(p.apps, on_disk)                                     # auto-discovery misses no app
        self.assertTrue({'accounts', 'securitylog', 'mailing', 'media', 'notifications'} <= set(p.apps))

    def test_cli_exit_code_zero_on_clean_tree(self):
        self.assertEqual(cm.main(['x', str(self.root)]), 0)


class FieldDefects(Base):
    def test_wrong_max_length(self):
        self.mutate('engagement/migrations/0001_initial.py', "('body', models.CharField(max_length=300))", "('body', models.CharField(max_length=200))")
        self.assert_reports('max_length')

    def test_wrong_field_type(self):
        self.mutate('engagement/models.py', 'body = models.CharField(max_length=300)', 'body = models.TextField(max_length=300)')
        self.assert_reports('type model=TextField')

    def test_wrong_default(self):
        self.mutate('follows/models.py', "default=ACCEPTED", "default=PENDING")
        self.assert_reports('default')

    def test_wrong_choices(self):
        self.mutate('safety/models.py', "('spam', 'Spam'),", "('spam', 'Spamm'),")
        self.assert_reports('choices')

    def test_missing_validator(self):
        self.mutate('profiles/models.py', "            validate_not_reserved,\n", "")
        self.assert_reports('validators')

    def test_null_changed(self):
        self.mutate('posts/models.py', "image = models.OneToOneField('media.Image', null=True,", "image = models.OneToOneField('media.Image',")
        self.assert_reports('null')

    def test_wrong_related_name(self):
        self.mutate('posts/migrations/0001_initial.py', "related_name='posts'", "related_name='postz'")
        self.assert_reports('related_name')

    def test_wrong_on_delete(self):
        self.mutate('posts/migrations/0001_initial.py', "django.db.models.deletion.CASCADE", "django.db.models.deletion.SET_NULL")
        self.assert_reports('on_delete')

    def test_wrong_fk_target(self):
        self.mutate('engagement/migrations/0001_initial.py', "to='posts.post')),\n                ('profile'", "to='posts.postt')),\n                ('profile'")
        self.assert_reports('target model=')

    def test_extra_field_in_model(self):
        self.mutate('notifications/models.py', "    read_at = models.DateTimeField(null=True, blank=True)\n", "    read_at = models.DateTimeField(null=True, blank=True)\n    extra = models.CharField(max_length=5)\n")
        self.assert_reports('extra: missing in migrations')

    def test_extra_field_in_migration(self):
        self.mutate('media/migrations/0001_initial.py', "('size_bytes', models.PositiveIntegerField()),", "('size_bytes', models.PositiveIntegerField()),\n                ('extra', models.IntegerField(default=0)),")
        self.assert_reports('in migrations but not in model')


class InheritedFields(Base):
    def test_missing_is_superuser(self):
        p = self.root / 'accounts/migrations/0001_initial.py'
        text = p.read_text()
        start = text.index("('is_superuser'")
        end = text.index("),\n", start) + 3
        p.write_text(text[:start] + text[end:])
        self.assert_reports('is_superuser: inherited from PermissionsMixin but missing')

    def test_wrong_password_length(self):
        self.mutate('accounts/migrations/0001_initial.py', "('password', models.CharField(max_length=128", "('password', models.CharField(max_length=64")
        self.assert_reports('password.max_length')


class MetaDefects(Base):
    def test_wrong_index_name(self):
        self.mutate('safety/migrations/0001_initial.py', "name='blocks_blocked_idx'", "name='blocks_wrong_idx'")
        self.assert_reports('blocks_blocked_idx')

    def test_wrong_constraint_name(self):
        self.mutate('follows/migrations/0001_initial.py', "name='follows_no_self_follow'", "name='follows_no_self_x'")
        self.assert_reports('follows_no_self_follow')

    def test_constraint_condition_negation_dropped(self):
        self.mutate('follows/migrations/0001_initial.py', "condition=models.Q(('follower', models.F('following')), _negated=True),", "condition=models.Q(('follower', models.F('following'))),")
        self.assert_reports('definition differs')

    def test_constraint_regex_changed(self):
        self.mutate('posts/models.py', "body__regex=r'\\S'", "body__regex=r'\\s'")
        self.assert_reports('definition differs')

    def test_ordering_added_to_model_only(self):
        self.mutate('posts/models.py', "    class Meta:\n", "    class Meta:\n        ordering = ['-created_at']\n")
        self.assert_reports('Meta.ordering')


class DependencyDefects(Base):
    def test_missing_cross_app_dependency(self):
        self.mutate('posts/migrations/0002_post_image.py', ", ('media', '0001_initial')", "")
        self.assert_reports('does not depend on app "media"')

    def test_dependency_on_nonexistent_migration(self):
        self.mutate('media/migrations/0001_initial.py', "('profiles', '0001_initial')", "('profiles', '0009_nope')")
        self.assert_reports('depends on missing migration profiles.0009_nope')

    def test_dependency_cycle(self):
        self.mutate('profiles/migrations/0001_initial.py', "migrations.swappable_dependency(settings.AUTH_USER_MODEL),", "migrations.swappable_dependency(settings.AUTH_USER_MODEL),\n        ('media', '0001_initial'),")
        self.assert_reports('dependency cycle')

    def test_missing_auth_dependency_for_m2m(self):
        self.mutate('accounts/migrations/0001_initial.py', "('auth', '0012_alter_user_first_name_max_length'),", "")
        self.assert_reports('does not depend on app "auth"')

    def test_model_without_migration_files(self):
        for f in (self.root / 'notifications/migrations').glob('0*.py'):
            f.unlink()
        self.assert_reports('notifications: has models but no migration files')


class Uninterpretable(Base):
    def test_unsupported_operation_is_reported_not_ignored(self):
        self.mutate('notifications/migrations/0001_initial.py', "    ]\n", "        migrations.RenameModel(old_name='A', new_name='B'),\n    ]\n", count=1)
        # the last "    ]\n" in the file closes `operations`; make sure we changed that one
        text = (self.root / 'notifications/migrations/0001_initial.py').read_text()
        self.assertIn('RenameModel', text)
        p = self.run_checker()
        self.assertTrue(any('RenameModel' in x for x in p.unverified), p.unverified)
        self.assertEqual(cm.main(['x', str(self.root)]), 2 if not p.problems else 1)


if __name__ == '__main__':
    unittest.main()
