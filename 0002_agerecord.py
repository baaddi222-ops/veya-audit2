# Hand-written — verify with `makemigrations --check --dry-run` (see docs/RUN_BLOCKED_CHECKS.md).
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='AgeRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('birth_year', models.PositiveSmallIntegerField()),
                ('birth_month', models.PositiveSmallIntegerField()),
                ('minimum_age_applied', models.PositiveSmallIntegerField()),
                ('rule_version', models.PositiveSmallIntegerField(default=1)),
                ('checked_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='age_record', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(model_name='agerecord', constraint=models.CheckConstraint(
            condition=models.Q(('birth_month__gte', 1), ('birth_month__lte', 12)), name='agerecord_month_valid')),
        migrations.AddConstraint(model_name='agerecord', constraint=models.CheckConstraint(
            condition=models.Q(('birth_year__gte', 1900), ('birth_year__lte', 2200)), name='agerecord_year_valid')),
    ]
