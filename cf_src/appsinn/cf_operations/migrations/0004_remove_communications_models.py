# cf-dev/cf_src/appsinn/cf_operations/migrations/0004_remove_communications_models.py

"""
Remove communications models from cf_operations state only.

Physical tables remain and are owned by cf_communications (same db_table names).
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cf_operations", "0003_initial"),
        ("cf_communications", "0001_initial_from_operations"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="notification",
                    name="broadcast",
                ),
                migrations.RemoveField(
                    model_name="notification",
                    name="branch",
                ),
                migrations.RemoveField(
                    model_name="notification",
                    name="organization",
                ),
                migrations.RemoveField(
                    model_name="notification",
                    name="recipient",
                ),
                migrations.AlterUniqueTogether(
                    name="notificationtemplate",
                    unique_together=None,
                ),
                migrations.RemoveField(
                    model_name="notificationtemplate",
                    name="branch",
                ),
                migrations.RemoveField(
                    model_name="notificationtemplate",
                    name="created_by",
                ),
                migrations.RemoveField(
                    model_name="notificationtemplate",
                    name="modified_by",
                ),
                migrations.DeleteModel(
                    name="BroadcastMessage",
                ),
                migrations.DeleteModel(
                    name="Notification",
                ),
                migrations.DeleteModel(
                    name="NotificationTemplate",
                ),
            ],
            database_operations=[],
        ),
    ]
