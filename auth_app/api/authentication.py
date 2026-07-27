"""Authentication classes for the API.

The API contract carries the JWT in HttpOnly cookies only, so the
Authorization header is never consulted.
"""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

COOKIE_AUTH_CHALLENGE = 'Cookie realm="api"'


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate a request from the access token cookie."""

    def authenticate(self, request):
        """Return the user and token carried by the access cookie."""
        raw_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

    def authenticate_header(self, request):
        """Return the challenge that keeps a 401 from becoming 403.

        The return value has to stay non-None. DRF turns every 401
        into a 403 when no authenticator offers a challenge, which
        would erase the difference between "not authenticated" and
        "not the owner" that the endpoint documentation lists as two
        separate cases. This is not cosmetic, do not remove it.

        The inherited value would be 'Bearer realm="api"' and would
        invite a client to send the Authorization header the contract
        forbids. Naming the cookie instead says where this API looks
        for a token.
        """
        return COOKIE_AUTH_CHALLENGE
