from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Invitation, Provider, Season


class ProviderInvitationTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.season = Season.objects.create(
            name="2026 Football Season",
            year=2026,
            bid_open=now - timedelta(hours=1),
            bid_close=now + timedelta(days=7),
        )
        self.provider = Provider.objects.create(
            company_name="Test Pizza",
            contact_name="Alex Manager",
            email="alex@testpizza.example",
        )
        self.invitation = Invitation.objects.create(
            season=self.season,
            provider=self.provider,
            token="test-token-123",
            expires_at=self.season.bid_close,
        )

    def test_invitation_page_is_public(self):
        response = self.client.get(reverse("invitation", args=[self.invitation.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Pizza")

    def test_invitation_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("invitation", args=[self.invitation.token]),
            {"password": "A-strong-test-password-123!", "password_confirm": "A-strong-test-password-123!"},
        )
        self.assertRedirects(response, reverse("home"))
        self.invitation.refresh_from_db()
        self.provider.refresh_from_db()
        self.assertIsNotNone(self.invitation.accepted_at)
        self.assertIsNotNone(self.provider.user)
        self.assertTrue(self.provider.user.check_password("A-strong-test-password-123!"))
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_invitation_cannot_be_reused(self):
        self.invitation.accepted_at = timezone.now()
        self.invitation.save(update_fields=["accepted_at"])
        response = self.client.get(reverse("invitation", args=[self.invitation.token]))
        self.assertContains(response, "already been used")

    def test_expired_invitation_is_rejected(self):
        self.invitation.expires_at = timezone.now() - timedelta(minutes=1)
        self.invitation.save(update_fields=["expires_at"])
        response = self.client.get(reverse("invitation", args=[self.invitation.token]))
        self.assertContains(response, "expired")
