# cf-dev/cf_src/appsinn/cf_people/tests.py

"""Tests for people domain models and User↔Member composition."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase

from cf_users.models import (
    Branch,
    BranchUser,
    Organization,
    OrganizationGroup,
    OrganizationGroupMembership,
    OrganizationUser,
)

from .models import Family, Member, SubBranch, Zone
from .services import create_member

User = get_user_model()


class MemberCompositionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Church One",
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
        self.operator = User.objects.create_user(
            username="staffuser1",
            email="staff@example.com",
            password="ComplexPass123!",
            first_name="Staff",
            last_name="User",
            phone_number="+233204444444",
            address="Addr",
            city="Accra",
            country="GH",
        )
        OrganizationUser.objects.create(
            user=self.operator,
            organization=self.org,
            role="ADMIN",
            is_org_manager=True,
        )
        self.operator._invalidate_access_cache()
        self.family = Family.objects.create(
            branch=self.branch,
            family_name="Mensah",
            primary_phone="+233200000001",
            home_address="Home",
        )

    def test_create_member_composes_user_identity(self):
        member = create_member(
            branch=self.branch,
            family=self.family,
            first_name="Kojo",
            last_name="Mensah",
            gender="MALE",
            password="ComplexPass123!",
        )
        # Prefix = first 3 letters of organisation name ("Church One" → CHU)
        self.assertTrue(member.member_number.startswith("CHU"))
        self.assertEqual(member.organization_id, self.org.pk)
        self.assertIsNotNone(member.user_id)
        self.assertEqual(member.first_name, "Kojo")
        self.assertEqual(member.last_name, "Mensah")
        self.assertEqual(member.user.first_name, "Kojo")
        self.assertTrue(member.user.check_password("ComplexPass123!"))
        self.assertTrue(member.user.is_church_member)
        self.assertEqual(member.user.get_member_profile(), member)

    def test_member_number_unique_per_organization_not_platform(self):
        org_b = Organization.objects.create(
            name="Church Two",
            address="Street",
            city="Kumasi",
            country="GH",
        )
        branch_b = Branch.objects.create(
            organization=org_b,
            name="Other",
            address="Street",
            city="Kumasi",
            country="GH",
            is_default=True,
        )
        m1 = create_member(
            branch=self.branch,
            first_name="Ama",
            last_name="One",
            gender="FEMALE",
        )
        m2 = create_member(
            branch=branch_b,
            first_name="Ama",
            last_name="Two",
            gender="FEMALE",
        )
        # Different orgs may reuse the same numeric sequence independently.
        self.assertEqual(m1.organization_id, self.org.pk)
        self.assertEqual(m2.organization_id, org_b.pk)
        self.assertNotEqual(m1.organization_id, m2.organization_id)
        # Explicit same number allowed across orgs.
        m2.member_number = m1.member_number
        # Bypass immutable-code guard by updating via queryset after create.
        Member.objects.filter(pk=m2.pk).update(member_number=m1.member_number)
        m2.refresh_from_db()
        self.assertEqual(m1.member_number, m2.member_number)

    def test_member_requires_user(self):
        with self.assertRaises(ValidationError):
            member = Member(
                branch=self.branch,
                family=self.family,
            )
            member.full_clean()

    def test_identity_not_stored_on_member_table(self):
        field_names = {f.name for f in Member._meta.get_fields()}
        self.assertNotIn("first_name", field_names)
        self.assertNotIn("last_name", field_names)
        self.assertIn("user", field_names)
        self.assertIn("membership_status", field_names)

    def test_tenant_filter_includes_accessible_branch_members(self):
        member = create_member(
            branch=self.branch,
            family=self.family,
            first_name="Ama",
            last_name="Mensah",
            gender="FEMALE",
        )
        qs = Member.objects.for_user(self.operator)
        self.assertIn(member, qs)

    def test_link_existing_user_as_member(self):
        user = User.objects.create_user(
            username="existing1",
            email="existing@example.com",
            password="ComplexPass123!",
            first_name="Existing",
            last_name="Person",
            phone_number="+233207777777",
            address="Addr",
            city="Accra",
            country="GH",
        )
        member = create_member(
            branch=self.branch,
            user=user,
            first_name="Existing",
            last_name="Person",
            gender="MALE",
        )
        self.assertEqual(member.user_id, user.pk)
        self.assertEqual(str(member), user.get_full_name())


class ZoneSubGroupHierarchyTests(TestCase):
    """Organisation → Branch → Zone → Sub group."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Hierarchy Church",
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

    def test_subgroup_requires_zone_under_branch(self):
        zone = Zone.objects.create(
            branch=self.branch,
            name="ZONE 13",
            code="Z13",
        )
        cell = SubBranch.objects.create(
            zone=zone,
            branch=self.branch,
            name="His Presence",
            group_type="CELL",
        )
        self.assertEqual(cell.zone_id, zone.pk)
        self.assertEqual(cell.branch_id, self.branch.pk)
        self.assertEqual(list(zone.sub_groups.all()), [cell])

    def test_subgroup_branch_synced_from_zone(self):
        zone = Zone.objects.create(branch=self.branch, name="East Zone")
        cell = SubBranch(
            zone=zone,
            name="Peace Cell",
            group_type="SATELLITE",
        )
        # branch omitted — save() copies from zone
        cell.save()
        cell.refresh_from_db()
        self.assertEqual(cell.branch_id, self.branch.pk)

    def test_zone_name_unique_per_branch(self):
        Zone.objects.create(branch=self.branch, name="ZONE 13", code="Z13")
        dup = Zone(branch=self.branch, name="ZONE 13", code="Z14")
        with self.assertRaises(ValidationError) as ctx:
            dup.full_clean()
        self.assertIn("name", ctx.exception.message_dict)

    def test_zone_code_unique_per_branch(self):
        Zone.objects.create(branch=self.branch, name="North", code="Z13")
        dup = Zone(branch=self.branch, name="South", code="Z13")
        with self.assertRaises(ValidationError) as ctx:
            dup.full_clean()
        self.assertIn("code", ctx.exception.message_dict)

    def test_zone_blank_codes_allowed_multiple(self):
        Zone.objects.create(branch=self.branch, name="Alpha", code="")
        Zone.objects.create(branch=self.branch, name="Beta", code=None)
        self.assertEqual(
            Zone.objects.filter(branch=self.branch, code__isnull=True).count(), 2
        )
