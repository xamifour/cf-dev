# cf-dev/cf_src/appsinn/cf_communications/tests.py

"""Tests for communications channels and models."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from cf_communications.models import (
    BirthdayGreetingLog,
    BroadcastMessage,
    Notification,
    NotificationTemplate,
)
from cf_communications.tasks import resolve_birthday_copy, send_birthday_messages
from cf_communications.utils import send_email
from cf_users.models import Branch, Organization, OrganizationUser

User = get_user_model()


class UtilsTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        CF_HTML_EMAIL=False,
    )
    def test_send_email(self):
        sent = send_email(
            subject="Hello",
            body_text="Body",
            recipients=["a@example.com"],
        )
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Hello")


class ModelImportTests(TestCase):
    def test_models_importable(self):
        self.assertTrue(Notification._meta.db_table.startswith("cf_operations_"))
        self.assertTrue(BroadcastMessage._meta.app_label == "cf_communications")
        self.assertTrue(NotificationTemplate._meta.app_label == "cf_communications")

    def test_create_broadcast(self):
        org = Organization.objects.create(
            name="Comm Org",
            address="1 St",
            city="Accra",
            country="GH",
        )
        Branch.objects.create(
            organization=org,
            name="Main",
            address="1 St",
            city="Accra",
            country="GH",
            is_default=True,
        )
        msg = BroadcastMessage.objects.create(
            organization=org,
            title="Sunday update",
            body="Service at 9am",
            channels=["email"],
        )
        self.assertEqual(str(msg), "Sunday update")


class BirthdayMessageTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Birthday Church",
            address="1 St",
            city="Accra",
            country="GH",
            birthday_greetings_enabled=True,
            birthday_subject="Happy Birthday, {name}!",
            birthday_message=(
                "Dear {name},\n\nHappy Birthday from {org} ({branch})!\n\n— {year}"
            ),
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name="Main",
            address="1 St",
            city="Accra",
            country="GH",
            is_default=True,
            birthday_greetings_enabled=True,
        )
        today = timezone.localdate()
        self.today = today
        self.user = User.objects.create_user(
            username="bdayuser1",
            email="bday@example.com",
            password="ComplexPass123!",
            first_name="Birthday",
            last_name="Person",
            phone_number="+233209090901",
            address="Addr",
            city="Accra",
            country="GH",
            birth_date=date(1990, today.month, today.day),
            notify_via_email=True,
            notify_via_inapp=True,
        )
        OrganizationUser.objects.create(
            user=self.user,
            organization=self.org,
            role="MEMBER",
        )

    def test_resolve_uses_org_template(self):
        title, body = resolve_birthday_copy(self.branch, self.user, self.today)
        self.assertIn("Birthday Person", title)
        self.assertIn("Birthday Church", body)
        self.assertIn("Main", body)

    def test_branch_overrides_org_message(self):
        self.branch.birthday_subject = "Branch says hi {name}"
        self.branch.birthday_message = "From branch {branch} only"
        self.branch.save()
        title, body = resolve_birthday_copy(self.branch, self.user, self.today)
        self.assertEqual(title, "Branch says hi Birthday Person")
        self.assertEqual(body, "From branch Main only")

    def test_skips_when_no_typed_message(self):
        self.org.birthday_message = ""
        self.org.save()
        self.branch.birthday_message = ""
        self.branch.save()
        self.assertIsNone(resolve_birthday_copy(self.branch, self.user, self.today))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        CF_HTML_EMAIL=False,
        CELERY_TASK_ALWAYS_EAGER=True,
    )
    def test_sends_birthday_once_per_year(self):
        result = send_birthday_messages(for_date=self.today.isoformat())
        self.assertEqual(result["sent"], 1)
        self.assertEqual(BirthdayGreetingLog.objects.filter(user=self.user).count(), 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user, title__icontains="Birthday"
            ).exists()
        )
        self.assertGreaterEqual(len(mail.outbox), 1)

        result2 = send_birthday_messages(for_date=self.today.isoformat())
        self.assertEqual(result2["sent"], 0)
        self.assertEqual(BirthdayGreetingLog.objects.filter(user=self.user).count(), 1)

    def test_disabled_on_organisation(self):
        self.org.birthday_greetings_enabled = False
        self.org.save()
        result = send_birthday_messages(for_date=self.today.isoformat())
        self.assertEqual(result["sent"], 0)
