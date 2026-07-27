"""Authentication classes for the API.

The API contract carries the JWT in HttpOnly cookies only, so the
Authorization header is never consulted.
"""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate a request from the access token cookie.

    authenticate_header() is deliberately inherited instead of
    overridden. Without a WWW-Authenticate header DRF turns every 401
    into a 403, which would erase the difference between "not
    authenticated" and "not the owner" that the endpoint
    documentation lists as two separate cases.
    """

    def authenticate(self, request):
        """Return the user and token carried by the access cookie."""
        raw_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
