"""Authentication classes for the API."""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate a request from the access token cookie."""

    def authenticate(self, request):
        """Return the user and token carried by the access cookie."""
        raw_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
