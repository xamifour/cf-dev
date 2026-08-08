# cf-dev/cf_src/appsinn/cf_finance/migrations/0003_member_user_composition.py

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cf_finance", "0002_initial"),
        ("cf_people", "0003_member_user_composition"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="employee",
            options={
                "ordering": ("member__user__last_name", "member__user__first_name"),
                "verbose_name": "employee",
                "verbose_name_plural": "employees",
            },
        ),
    ]
