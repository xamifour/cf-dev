# cf-dev/cf_src/appsinn/cf_users/tests.py

"""Tests for multitenant users, organisations, and branches."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from django.contrib.auth.models import Permission

from .models import (
    Branch,
    BranchUser,
    Organization,
    OrganizationGroup,
    OrganizationGroupMembership,
    OrganizationUser,
)
from .permissions import user_has_org_perm
from .validators import validate_username

User = get_user_model()


class UsernameValidatorTests(TestCase):
    def test_valid_username(self):
        validate_username("johndoe_1")

    def test_rejects_short_username(self):
        with self.assertRaises(ValidationError):
            validate_username("short")


class MultiTenantAccessTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Org A",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        self.org_b = Organization.objects.create(
            name="Org B",
            address="2 Main",
            city="Kumasi",
            country="GH",
        )
        self.branch_a = Branch.objects.create(
            organization=self.org_a,
            name="Campus A",
            address="1 Main",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.branch_b = Branch.objects.create(
            organization=self.org_b,
            name="Campus B",
            address="2 Main",
            city="Kumasi",
            country="GH",
            is_default=True,
        )
        self.manager_a = User.objects.create_user(
            username="manager_a1",
            email="manager_a@example.com",
            password="ComplexPass123!",
            first_name="Mana",
            last_name="GerA",
            phone_number="+233201111111",
            address="Addr",
            city="Accra",
            country="GH",
        )
        self.member_b = User.objects.create_user(
            username="member_b12",
            email="member_b@example.com",
            password="ComplexPass123!",
            first_name="Mem",
            last_name="BerB",
            phone_number="+233202222222",
            address="Addr",
            city="Kumasi",
            country="GH",
        )
        OrganizationUser.objects.create(
            user=self.manager_a,
            organization=self.org_a,
            role="ADMIN",
            is_org_manager=True,
        )
        BranchUser.objects.create(
            user=self.member_b,
            branch=self.branch_b,
            role="VIEWER",
            is_org_manager=False,
        )
        # Clear cached_property after membership changes in same process.
        self.manager_a._invalidate_access_cache()
        self.member_b._invalidate_access_cache()

    def test_org_manager_sees_own_org_branches(self):
        self.assertIn(self.branch_a.pk, self.manager_a.accessible_branches)
        self.assertNotIn(self.branch_b.pk, self.manager_a.accessible_branches)

    def test_branch_member_scope(self):
        self.assertIn(self.branch_b.pk, self.member_b.accessible_branches)
        self.assertNotIn(self.branch_a.pk, self.member_b.accessible_branches)

    def test_tenant_manager_for_user(self):
        visible = Branch.objects.for_user(self.manager_a)
        self.assertEqual(list(visible), [self.branch_a])
        invisible = Branch.objects.for_user(self.member_b)
        self.assertEqual(list(invisible), [self.branch_b])

    def test_organization_owner_auto_created(self):
        self.assertTrue(hasattr(self.org_a, "owner_record"))
        self.assertEqual(self.org_a.owner_record.organization_user.user, self.manager_a)

    def test_is_org_member_vs_manager(self):
        plain = User.objects.create_user(
            username="plainuser1",
            email="plain@example.com",
            password="ComplexPass123!",
            first_name="Plain",
            last_name="User",
            phone_number="+233203333333",
            address="Addr",
            city="Accra",
            country="GH",
        )
        OrganizationUser.objects.create(
            user=plain,
            organization=self.org_a,
            role="AUDITOR",
            is_org_manager=False,
        )
        plain._invalidate_access_cache()
        self.assertTrue(plain.is_org_member(self.org_a))
        self.assertFalse(plain.is_org_manager(self.org_a))


class ScaleTenancyTests(TestCase):
    """Scale-safe tenant context and subquery scoping."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Scale Org",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name="Campus",
            address="1 Main",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.user = User.objects.create_user(
            username="scale_mgr1",
            email="scale@example.com",
            password="ComplexPass123!",
            first_name="Scale",
            last_name="Manager",
            phone_number="+233208888888",
            address="Addr",
            city="Accra",
            country="GH",
        )
        OrganizationUser.objects.create(
            user=self.user,
            organization=self.org,
            role="ADMIN",
            is_org_manager=True,
        )
        self.user._invalidate_access_cache()

    def test_superuser_does_not_materialise_all_org_ids(self):
        admin = User.objects.create_superuser(
            username="superuser1",
            email="super@example.com",
            password="ComplexPass123!",
            first_name="Super",
            last_name="User",
            phone_number="+233209999999",
            address="Addr",
            city="Accra",
            country="GH",
        )
        self.assertEqual(admin.organizations_managed, [])
        self.assertEqual(admin.accessible_branches, [])

    def test_for_user_uses_branch_access(self):
        qs = Branch.objects.for_user(self.user)
        self.assertIn(self.branch, qs)

    def test_sequence_codes_unique(self):
        from .sequences import format_sequence_code

        a = format_sequence_code("TST", 4, name="test_seq")
        b = format_sequence_code("TST", 4, name="test_seq")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("TST"))


class OrganizationCodeTests(TestCase):
    def test_code_auto_generated_on_create(self):
        org = Organization.objects.create(
            name="Auto Code Org",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        self.assertTrue(org.code)
        self.assertTrue(org.code.startswith("ORG"))
        self.assertGreaterEqual(len(org.code), 11)

    def test_codes_increment(self):
        first = Organization.objects.create(
            name="Org One",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        second = Organization.objects.create(
            name="Org Two",
            address="2 Main",
            city="Accra",
            country="GH",
        )
        self.assertTrue(first.code.startswith("ORG"))
        self.assertTrue(second.code.startswith("ORG"))
        self.assertNotEqual(first.code, second.code)
        n1 = int(first.code.replace("ORG", ""))
        n2 = int(second.code.replace("ORG", ""))
        self.assertEqual(n2, n1 + 1)

    def test_code_survives_missing_sequence(self):
        """If ORG_seq is missing/reset, still avoid reusing an existing code."""
        from .sequences import CodeSequence

        first = Organization.objects.create(
            name="Existing Org",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        # Simulate production desync: existing ORG00000001 but no sequence row.
        CodeSequence.objects.filter(name="ORG_seq").delete()
        second = Organization.objects.create(
            name="Next Org",
            address="2 Main",
            city="Accra",
            country="GH",
        )
        self.assertNotEqual(first.code, second.code)
        self.assertGreater(
            int(second.code.replace("ORG", "")),
            int(first.code.replace("ORG", "")),
        )

    def test_code_immutable_after_create(self):
        org = Organization.objects.create(
            name="Immutable Org",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        org.code = "ORG99999999"
        with self.assertRaises(ValidationError):
            org.save()


class PortalAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(
            name="Portal Org",
            address="1 Main",
            city="Accra",
            country="GH",
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name="Main Campus",
            address="1 Main",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.org_user = User.objects.create_user(
            username="portal_user",
            email="portal@example.com",
            password="ComplexPass123!",
            first_name="Portal",
            last_name="User",
            phone_number="+233205555555",
            address="Addr",
            city="Accra",
            country="GH",
        )
        OrganizationUser.objects.create(
            user=self.org_user,
            organization=self.org,
            role="ADMIN",
            is_org_manager=True,
        )
        self.org_user._invalidate_access_cache()

        self.staff_only = User.objects.create_user(
            username="staff_only1",
            email="staffonly@example.com",
            password="ComplexPass123!",
            first_name="Staff",
            last_name="Only",
            phone_number="+233206666666",
            address="Addr",
            city="Accra",
            country="GH",
            is_staff=True,
        )

    def test_root_serves_portal_login(self):
        response = self.client.get(reverse("portal_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organisation portal")
        self.assertContains(response, "Admin sign-in")

    def test_org_user_can_login_and_reach_dashboard(self):
        response = self.client.post(
            reverse("portal_login"),
            {"username": "portal_user", "password": "ComplexPass123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("portal_dashboard"))

        dashboard = self.client.get(reverse("portal_dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Portal Org")
        self.assertContains(dashboard, "Main Campus")

    def test_org_user_can_login_with_email(self):
        response = self.client.post(
            reverse("portal_login"),
            {"username": "portal@example.com", "password": "ComplexPass123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("portal_dashboard"))

    def test_staff_can_login_to_portal_without_org(self):
        """Staff accounts may use the organisation portal as well as /admin/."""
        response = self.client.post(
            reverse("portal_login"),
            {"username": "staff_only1", "password": "ComplexPass123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("portal_dashboard"))
        dashboard = self.client.get(reverse("portal_dashboard"))
        self.assertEqual(dashboard.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("portal_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("portal_login"), response.url)

    def test_admin_login_path_still_exists(self):
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)


class UsersVisibleToUserTests(TestCase):
    """Pastors / branch users should see peers, not only themselves."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Visible Org",
            address="Street",
            city="Accra",
            country="GH",
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name="Main",
            address="Street",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.pastor = User.objects.create_user(
            username="pastor_vis",
            email="pastor_v@example.com",
            password="ComplexPass123!",
            first_name="Pastor",
            last_name="Vis",
            phone_number="+233207777801",
            address="A",
            city="Accra",
            country="GH",
            is_staff=True,
        )
        self.member_user = User.objects.create_user(
            username="member_vis",
            email="member_v@example.com",
            password="ComplexPass123!",
            first_name="Member",
            last_name="Vis",
            phone_number="+233207777802",
            address="A",
            city="Accra",
            country="GH",
        )
        BranchUser.objects.create(
            user=self.pastor, branch=self.branch, role="ADMIN"
        )
        BranchUser.objects.create(
            user=self.member_user, branch=self.branch, role="VIEWER"
        )

    def test_pastor_sees_branch_peer_users(self):
        from .tenancy import users_visible_to_user_qs

        visible = users_visible_to_user_qs(self.pastor)
        self.assertTrue(visible.filter(pk=self.pastor.pk).exists())
        self.assertTrue(visible.filter(pk=self.member_user.pk).exists())


class OrganizationGroupsAndBranchUserTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Group Org",
            address="Street",
            city="Accra",
            country="GH",
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name="Main",
            address="Street",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.user = User.objects.create_user(
            username="branch_member1",
            email="bm1@example.com",
            password="ComplexPass123!",
            first_name="Branch",
            last_name="Member",
            phone_number="+233207777701",
            address="A",
            city="Accra",
            country="GH",
        )

    def test_new_org_gets_default_groups(self):
        names = set(
            OrganizationGroup.objects.filter(organization=self.org).values_list(
                "name", flat=True
            )
        )
        self.assertIn("Members", names)
        self.assertTrue(
            OrganizationGroup.objects.filter(
                organization=self.org, name="Members", is_default=True
            ).exists()
        )

    def test_branch_user_creates_org_user_viewer(self):
        self.assertFalse(
            OrganizationUser.objects.filter(
                user=self.user, organization=self.org
            ).exists()
        )
        BranchUser.objects.create(
            user=self.user, branch=self.branch, role=BranchUser.ROLE_VIEWER
        )
        ou = OrganizationUser.objects.get(user=self.user, organization=self.org)
        self.assertEqual(ou.role, "VIEWER")
        self.assertFalse(ou.is_org_manager)
        # Default Members group membership
        self.assertTrue(
            OrganizationGroupMembership.objects.filter(
                user=self.user,
                group__organization=self.org,
                group__name="Members",
            ).exists()
        )

    def test_org_group_grants_permission(self):
        BranchUser.objects.create(user=self.user, branch=self.branch)
        group = OrganizationGroup.objects.get(organization=self.org, name="Members")
        perm = Permission.objects.filter(codename="view_member").first()
        self.assertIsNotNone(perm)
        group.permissions.add(perm)
        # Clear cache then check
        if hasattr(self.user, "_org_group_perm_cache"):
            delattr(self.user, "_org_group_perm_cache")
        self.assertTrue(user_has_org_perm(self.user, "cf_people.view_member"))
        self.assertTrue(self.user.has_perm("cf_people.view_member"))
