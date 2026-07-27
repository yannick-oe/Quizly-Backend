"""Tests for POST /api/register/."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from auth_app.api.views import REGISTRATION_SUCCESS_MESSAGE

from .helpers import ACCESS_COOKIE, REFRESH_COOKIE

VALID_PAYLOAD = {
    "username": "newcomer",
    "password": "s3cret-passphrase",
    "confirmed_password": "s3cret-passphrase",
    "email": "newcomer@example.com",
}

EXISTING_USERNAME = "resident"

EXISTING_EMAIL = "Resident@Example.com"

EXISTING_PASSWORD = "another-passphrase"


class RegistrationTests(TestCase):
    """Cover the documented cases of the registration endpoint."""

    def setUp(self):
        """Resolve the endpoint and occupy one username and email."""
        self.url = reverse("register")
        User.objects.create_user(
            username=EXISTING_USERNAME,
            password=EXISTING_PASSWORD,
            email=EXISTING_EMAIL,
        )

    def register(self, **overrides):
        """Send a registration request with the given changes."""
        payload = dict(VALID_PAYLOAD)
        payload.update(overrides)
        return self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
        )

    def test_valid_request_creates_the_account(self):
        """A valid request answers 201 with the fixed message."""
        response = self.register()
        expected = {"detail": REGISTRATION_SUCCESS_MESSAGE}
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), expected)
        self.assertTrue(
            User.objects.filter(username=VALID_PAYLOAD["username"]).exists()
        )

    def test_password_is_stored_hashed(self):
        """The new account verifies the password it was sent."""
        self.register()
        user = User.objects.get(username=VALID_PAYLOAD["username"])
        self.assertNotEqual(user.password, VALID_PAYLOAD["password"])
        self.assertTrue(user.check_password(VALID_PAYLOAD["password"]))

    def test_registration_sets_no_auth_cookies(self):
        """Registration hands out an account, not a session."""
        response = self.register()
        self.assertNotIn(ACCESS_COOKIE, response.cookies)
        self.assertNotIn(REFRESH_COOKIE, response.cookies)

    def test_password_mismatch_is_rejected(self):
        """Two differing passwords answer 400 on the second field."""
        response = self.register(confirmed_password="something-else")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirmed_password", response.json())

    def test_duplicate_username_is_rejected(self):
        """A taken username answers 400 under the username key."""
        response = self.register(username=EXISTING_USERNAME)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.json())

    def test_duplicate_email_is_rejected(self):
        """A taken email answers 400 under the email key."""
        response = self.register(email=EXISTING_EMAIL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())

    def test_duplicate_email_ignores_case(self):
        """An email that differs only in case counts as taken."""
        response = self.register(email=EXISTING_EMAIL.lower())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())

    def test_blank_email_is_rejected(self):
        """An empty email answers 400 under the email key."""
        response = self.register(email="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())

    def test_missing_email_is_rejected(self):
        """A payload without an email field answers 400."""
        payload = {
            key: value
            for key, value in VALID_PAYLOAD.items()
            if key != "email"
        }
        response = self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())
