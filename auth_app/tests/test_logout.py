"""Tests for POST /api/logout/."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from auth_app.api.views import LOGOUT_SUCCESS_MESSAGE

from .helpers import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    WWW_AUTHENTICATE_CHALLENGE,
    create_user,
    log_in,
)

CONTRACT_DETAIL = (
    "Log-Out successfully! All Tokens will be deleted. "
    "Refresh token is now invalid."
)

JSON_CONTENT_TYPE = "application/json"


class LogoutTests(TestCase):
    """Cover the documented cases of the logout endpoint."""

    def setUp(self):
        """Resolve the endpoint and log the test client in."""
        self.url = reverse("logout")
        create_user()
        log_in(self.client)

    def log_out(self):
        """Send the body-less request the frontend sends."""
        return self.client.generic(
            "POST",
            self.url,
            headers={"Content-Type": JSON_CONTENT_TYPE},
        )

    def assert_cookie_cleared(self, response, name):
        """Assert one auth cookie is emptied and expired."""
        cookie = response.cookies[name]
        self.assertEqual(cookie.value, "")
        self.assertEqual(int(cookie["max-age"]), 0)
        self.assertEqual(cookie["path"], "/")
        self.assertEqual(cookie["samesite"], "Lax")

    def test_logout_answers_the_contract_message(self):
        """A logout answers 200 with the exact detail string."""
        response = self.log_out()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"detail": CONTRACT_DETAIL})
        self.assertEqual(LOGOUT_SUCCESS_MESSAGE, CONTRACT_DETAIL)

    def test_logout_clears_both_cookies(self):
        """Both auth cookies are removed from the client."""
        response = self.log_out()
        self.assert_cookie_cleared(response, ACCESS_COOKIE)
        self.assert_cookie_cleared(response, REFRESH_COOKIE)
        self.assertFalse(self.client.cookies[ACCESS_COOKIE].value)

    def test_logout_blacklists_the_refresh_token(self):
        """The refresh token is invalidated server-side."""
        self.assertEqual(BlacklistedToken.objects.count(), 0)
        self.log_out()
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_logout_accepts_a_request_without_content_type(self):
        """A request with neither body nor content type works."""
        response = self.client.post(
            self.url,
            data="",
            content_type=JSON_CONTENT_TYPE,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_survives_a_missing_refresh_cookie(self):
        """A lost refresh cookie still logs the client out."""
        del self.client.cookies[REFRESH_COOKIE]
        response = self.log_out()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.count(), 0)

    def test_logout_survives_an_unusable_refresh_cookie(self):
        """A damaged refresh cookie still logs the client out."""
        self.client.cookies[REFRESH_COOKIE] = "not-a-token"
        response = self.log_out()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.count(), 0)

    def test_logout_requires_authentication(self):
        """An unauthenticated logout answers 401 and not 403."""
        self.client.cookies.clear()
        response = self.log_out()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response["WWW-Authenticate"],
            WWW_AUTHENTICATE_CHALLENGE,
        )
