# cf-dev/cf_src/appsinn/cf_social/tests.py

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from cf_people.models import Zone
from cf_users.models import Branch, BranchUser, Organization, OrganizationUser

from . import services
from .models import Discussion, DiscussionMessage, Follow, Post, SocialProfile

User = get_user_model()


class SocialMVPTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.alice = User.objects.create_user(
            username="alice_social",
            email="alice_s@example.com",
            password="ComplexPass123!",
            first_name="Alice",
            last_name="S",
            phone_number="+233201111101",
            address="A",
            city="Accra",
            country="GH",
        )
        self.bob = User.objects.create_user(
            username="bob_social",
            email="bob_s@example.com",
            password="ComplexPass123!",
            first_name="Bob",
            last_name="S",
            phone_number="+233201111102",
            address="B",
            city="Accra",
            country="GH",
        )
        # Profiles from signal
        self.assertTrue(SocialProfile.objects.filter(user=self.alice).exists())

    def test_feed_requires_login(self):
        r = self.client.get(reverse("cf_social:feed"))
        self.assertEqual(r.status_code, 302)

    def test_create_post_and_feed(self):
        self.client.force_login(self.alice)
        r = self.client.post(
            reverse("cf_social:feed"),
            {"body": "Hello church network!", "visibility": "PUBLIC"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Post.objects.filter(author=self.alice).exists())
        r = self.client.get(reverse("cf_social:feed"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Hello church network!")

    def test_follow_and_like_comment(self):
        post = Post.objects.create(
            author=self.bob, body="Bob's post", visibility=Post.VISIBILITY_PUBLIC
        )
        services.follow_user(self.alice, self.bob)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())
        liked = services.toggle_like(self.alice, post)
        self.assertTrue(liked)
        post.refresh_from_db()
        self.assertEqual(post.likes_count, 1)
        c = services.add_comment(self.alice, post, "Amen!")
        self.assertIsNotNone(c)
        post.refresh_from_db()
        self.assertEqual(post.comments_count, 1)

    def test_unfollow_from_profile(self):
        services.follow_user(self.alice, self.bob)
        self.assertTrue(
            Follow.objects.filter(follower=self.alice, following=self.bob).exists()
        )
        self.client.force_login(self.alice)
        r = self.client.get(reverse("cf_social:profile", args=[self.bob.username]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Following")
        self.assertContains(r, "Unfollow")
        r = self.client.post(
            reverse("cf_social:follow_toggle", args=[self.bob.username]),
            {"action": "unfollow"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(
            Follow.objects.filter(follower=self.alice, following=self.bob).exists()
        )

    def test_follow_toggle_without_action(self):
        """Omitting action toggles: follow then unfollow."""
        self.client.force_login(self.alice)
        url = reverse("cf_social:follow_toggle", args=[self.bob.username])
        self.client.post(url, {})
        self.assertTrue(
            Follow.objects.filter(follower=self.alice, following=self.bob).exists()
        )
        self.client.post(url, {})
        self.assertFalse(
            Follow.objects.filter(follower=self.alice, following=self.bob).exists()
        )

    def test_block_hides_from_feed(self):
        Post.objects.create(author=self.bob, body="Secret", visibility="PUBLIC")
        self.client.force_login(self.alice)
        from .models import Block

        Block.objects.create(blocker=self.alice, blocked=self.bob)
        r = self.client.get(reverse("cf_social:feed"))
        self.assertNotContains(r, "Secret")

    def test_direct_message(self):
        msg = services.send_direct_message(self.alice, self.bob, "Hi Bob")
        self.assertIsNotNone(msg)
        self.client.force_login(self.bob)
        r = self.client.get(reverse("cf_social:inbox"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "alice_social")

    def test_search_people(self):
        self.client.force_login(self.alice)
        r = self.client.get(reverse("cf_social:search"), {"q": "bob"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "bob_social")


class DiscussionAudienceTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Org A Church",
            address="A",
            city="Accra",
            country="GH",
        )
        self.org_b = Organization.objects.create(
            name="Org B Church",
            address="B",
            city="Kumasi",
            country="GH",
        )
        self.branch_a = Branch.objects.create(
            organization=self.org_a,
            name="Branch A",
            address="A",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.branch_b = Branch.objects.create(
            organization=self.org_b,
            name="Branch B",
            address="B",
            city="Kumasi",
            country="GH",
            is_default=True,
        )
        self.zone_a = Zone.objects.create(
            branch=self.branch_a, name="Zone Alpha", code="ZA"
        )
        self.alice = User.objects.create_user(
            username="alice_disc",
            email="alice_d@example.com",
            password="ComplexPass123!",
            first_name="Alice",
            last_name="D",
            phone_number="+233201111201",
            address="A",
            city="Accra",
            country="GH",
        )
        self.bob = User.objects.create_user(
            username="bob_disc",
            email="bob_d@example.com",
            password="ComplexPass123!",
            first_name="Bob",
            last_name="D",
            phone_number="+233201111202",
            address="B",
            city="Kumasi",
            country="GH",
        )
        OrganizationUser.objects.create(
            user=self.alice, organization=self.org_a, role="VIEWER"
        )
        BranchUser.objects.create(
            user=self.alice, branch=self.branch_a, role="VIEWER"
        )
        OrganizationUser.objects.create(
            user=self.bob, organization=self.org_b, role="VIEWER"
        )
        BranchUser.objects.create(
            user=self.bob, branch=self.branch_b, role="VIEWER"
        )

    def test_platform_discussion_visible_to_all(self):
        d = services.create_discussion(
            self.alice,
            title="Platform prayer",
            body="Join us",
            audience=Discussion.AUDIENCE_PLATFORM,
        )
        self.assertTrue(services.can_view_discussion(self.alice, d))
        self.assertTrue(services.can_view_discussion(self.bob, d))
        self.assertIn(d, list(services.discussions_for(self.bob)))

    def test_org_discussion_scoped(self):
        d = services.create_discussion(
            self.alice,
            title="Org A only",
            audience=Discussion.AUDIENCE_ORGANIZATION,
            organization=self.org_a,
        )
        self.assertTrue(services.can_view_discussion(self.alice, d))
        self.assertFalse(services.can_view_discussion(self.bob, d))

    def test_branch_and_zone_discussion_scoped(self):
        d_branch = services.create_discussion(
            self.alice,
            title="Branch A",
            audience=Discussion.AUDIENCE_BRANCH,
            branch=self.branch_a,
        )
        d_zone = services.create_discussion(
            self.alice,
            title="Zone Alpha chat",
            audience=Discussion.AUDIENCE_ZONE,
            zone=self.zone_a,
        )
        self.assertEqual(d_zone.branch_id, self.branch_a.pk)
        self.assertEqual(d_zone.organization_id, self.org_a.pk)
        self.assertTrue(services.can_view_discussion(self.alice, d_branch))
        self.assertTrue(services.can_view_discussion(self.alice, d_zone))
        self.assertFalse(services.can_view_discussion(self.bob, d_branch))
        self.assertFalse(services.can_view_discussion(self.bob, d_zone))

    def test_requires_scope_fk(self):
        with self.assertRaises(ValidationError):
            services.create_discussion(
                self.alice,
                title="Missing org",
                audience=Discussion.AUDIENCE_ORGANIZATION,
            )

    def test_reply_and_lock(self):
        d = services.create_discussion(
            self.alice,
            title="Open thread",
            audience=Discussion.AUDIENCE_PLATFORM,
        )
        msg = services.add_discussion_message(self.bob, d, "Amen!")
        self.assertIsNotNone(msg)
        d.refresh_from_db()
        self.assertEqual(d.messages_count, 1)
        d.is_locked = True
        d.save(update_fields=["is_locked"])
        self.assertIsNone(services.add_discussion_message(self.bob, d, "Too late"))

    def test_discussion_list_view(self):
        services.create_discussion(
            self.alice,
            title="Visible list item",
            audience=Discussion.AUDIENCE_PLATFORM,
        )
        client = Client()
        client.force_login(self.bob)
        r = client.get(reverse("cf_social:discussion_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Visible list item")
