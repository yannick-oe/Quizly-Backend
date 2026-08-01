"""Tests for POST /api/token/refresh/."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from auth_app.api.views import TOKEN_REFRESH_SUCCESS_MESSAGE

from .helpers import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    WWW_AUTHENTICATE_CHALLENGE,
    create_user,
    log_in,
)

CONTRACT_DETAIL = "Token refreshed"

INVALID_TOKEN = "not-a-token"


class TokenRefreshTests(TestCase):
    """Cover the documented cases of the refresh endpoint."""

    def setUp(self):
        """Log the test client in and keep its first token pair."""
        self.url = reverse("token_refresh")
        create_user()
        login = log_in(self.client)
        self.old_access = login.cookies[ACCESS_COOKIE].value
        self.old_refresh = login.cookies[REFRESH_COOKIE].value

    def refresh(self):
        """Send the body-less request the frontend sends."""
        return self.client.generic("POST", self.url)

    def assert_auth_cookie(self, response, name):
        """Assert one auth cookie carries the documented flags."""
        cookie = response.cookies[name]
        self.assertTrue(cookie.value)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["path"], "/")

    def test_refresh_answers_the_contract_message(self):
        """A valid refresh answers 200 with the fixed message."""
        response = self.refresh()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"detail": CONTRACT_DETAIL})
        self.assertEqual(TOKEN_REFRESH_SUCCESS_MESSAGE, CONTRACT_DETAIL)

    def test_refresh_rewrites_both_cookies(self):
        """Rotation replaces the access and the refresh cookie."""
        response = self.refresh()
        self.assert_auth_cookie(response, ACCESS_COOKIE)
        self.assert_auth_cookie(response, REFRESH_COOKIE)
        self.assertNotEqual(
            response.cookies[REFRESH_COOKIE].value,
            self.old_refresh,
        )

    def test_refresh_issues_a_working_access_token(self):
        """The new access cookie authenticates the next request."""
        self.refresh()
        self.assertNotEqual(
            self.client.cookies[ACCESS_COOKIE].value,
            self.old_access,
        )
        response = self.client.generic("POST", reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_carrying_no_body_is_enough(self):
        """The refresh token is read from the cookie, not a body."""
        response = self.refresh()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("refresh", response.json())

    def test_refresh_without_a_cookie_is_rejected(self):
        """A client without the cookie answers 401 and not 403."""
        self.client.cookies.clear()
        response = self.refresh()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response["WWW-Authenticate"],
            WWW_AUTHENTICATE_CHALLENGE,
        )

    def test_refresh_with_an_unusable_token_is_rejected(self):
        """A damaged refresh cookie answers 401."""
        self.client.cookies[REFRESH_COOKIE] = INVALID_TOKEN
        response = self.refresh()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_after_logout_is_rejected(self):
        """A refresh token that logout blacklisted answers 401."""
        self.client.generic("POST", reverse("logout"))
        self.client.cookies[REFRESH_COOKIE] = self.old_refresh
        response = self.refresh()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotated_refresh_token_is_rejected(self):
        """The replaced refresh token stops working after use."""
        self.refresh()
        self.client.cookies[REFRESH_COOKIE] = self.old_refresh
        response = self.refresh()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
