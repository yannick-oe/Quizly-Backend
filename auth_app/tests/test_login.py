"""Tests for POST /api/login/."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from auth_app.api.serializers import INVALID_CREDENTIALS_MESSAGE
from auth_app.api.views import LOGIN_SUCCESS_MESSAGE

from .helpers import (
    ACCESS_COOKIE,
    EMAIL,
    PASSWORD,
    REFRESH_COOKIE,
    USERNAME,
    WWW_AUTHENTICATE_CHALLENGE,
    create_user,
)

WRONG_PASSWORD = "not-the-passphrase"

UNKNOWN_USERNAME = "nobody"


class LoginTests(TestCase):
    """Cover the documented cases of the login endpoint."""

    def setUp(self):
        """Resolve the endpoint and create the account to log in."""
        self.url = reverse("login")
        self.user = create_user()

    def log_in(self, **payload):
        """Send a login request carrying the given credentials."""
        return self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
        )

    def valid_login(self):
        """Send a login request with the correct credentials."""
        return self.log_in(username=USERNAME, password=PASSWORD)

    def assert_auth_cookie(self, response, name):
        """Assert one auth cookie carries the documented flags."""
        cookie = response.cookies[name]
        self.assertTrue(cookie.value)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["path"], "/")
        self.assertFalse(cookie["secure"])

    def test_valid_credentials_answer_with_the_user(self):
        """A valid login answers 200 with detail and user."""
        response = self.valid_login()
        expected_user = {
            "id": self.user.id,
            "username": USERNAME,
            "email": EMAIL,
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"detail": LOGIN_SUCCESS_MESSAGE, "user": expected_user},
        )

    def test_response_keeps_the_documented_field_order(self):
        """The body lists detail before user, and id first."""
        payload = self.valid_login().json()
        self.assertEqual(list(payload), ["detail", "user"])
        self.assertEqual(
            list(payload["user"]),
            ["id", "username", "email"],
        )

    def test_login_sets_both_auth_cookies(self):
        """Both tokens arrive as cookies with the right flags."""
        response = self.valid_login()
        self.assert_auth_cookie(response, ACCESS_COOKIE)
        self.assert_auth_cookie(response, REFRESH_COOKIE)

    def test_no_token_reaches_the_response_body(self):
        """Neither token value appears anywhere in the body."""
        response = self.valid_login()
        body = response.content.decode()
        self.assertNotIn(response.cookies[ACCESS_COOKIE].value, body)
        self.assertNotIn(response.cookies[REFRESH_COOKIE].value, body)

    def test_wrong_password_is_rejected(self):
        """A wrong password answers 401 with a generic detail."""
        response = self.log_in(username=USERNAME, password=WRONG_PASSWORD)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {"detail": INVALID_CREDENTIALS_MESSAGE},
        )

    def test_unknown_user_is_rejected_the_same_way(self):
        """An unknown user answers with the identical 401 body."""
        response = self.log_in(
            username=UNKNOWN_USERNAME,
            password=PASSWORD,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {"detail": INVALID_CREDENTIALS_MESSAGE},
        )

    def test_missing_password_answers_400(self):
        """An incomplete body answers 400 in the field format."""
        response = self.log_in(username=USERNAME)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.json())

    def test_failed_login_is_not_downgraded_to_403(self):
        """A failed login answers 401 with a WWW-Authenticate header."""
        response = self.log_in(username=USERNAME, password=WRONG_PASSWORD)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response["WWW-Authenticate"],
            WWW_AUTHENTICATE_CHALLENGE,
        )
