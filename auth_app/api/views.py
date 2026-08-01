"""Views for the authentication endpoints."""

from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView as BaseTokenRefreshView,
)

from .authentication import CookieJWTAuthentication
from .cookies import delete_auth_cookies, set_auth_cookies
from .serializers import (
    REFRESH_TOKEN_FIELD,
    CookieTokenRefreshSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegistrationSerializer,
)

REGISTRATION_SUCCESS_MESSAGE = "User created successfully!"

LOGIN_SUCCESS_MESSAGE = "Login successfully!"

LOGOUT_SUCCESS_MESSAGE = (
    "Log-Out successfully! All Tokens will be deleted. "
    "Refresh token is now invalid."
)

TOKEN_REFRESH_SUCCESS_MESSAGE = "Token refreshed"


def _refresh_cookie_data(request):
    """Return the refresh cookie value as serializer input data."""
    raw_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    return {REFRESH_TOKEN_FIELD: raw_token or ""}


class RegistrationView(generics.CreateAPIView):
    """Create a user account."""

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def create(self, request, *args, **kwargs):
        """Create the account and answer with the fixed message."""
        response = super().create(request, *args, **kwargs)
        response.data = {"detail": REGISTRATION_SUCCESS_MESSAGE}
        return response


class LoginView(TokenObtainPairView):
    """Authenticate a user and hand out the two auth cookies."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """Log the user in and attach both auth cookies."""
        response = super().post(request, *args, **kwargs)
        tokens = response.data
        set_auth_cookies(response, tokens["access"], tokens["refresh"])
        response.data = {
            "detail": LOGIN_SUCCESS_MESSAGE,
            "user": tokens["user"],
        }
        return response


class LogoutView(APIView):
    """Log a user out and invalidate the refresh token."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Blacklist the refresh token and clear both cookies."""
        serializer = LogoutSerializer(data=_refresh_cookie_data(request))
        serializer.is_valid(raise_exception=True)
        response = Response({"detail": LOGOUT_SUCCESS_MESSAGE})
        delete_auth_cookies(response)
        return response


class TokenRefreshView(BaseTokenRefreshView):
    """Rotate the token pair carried by the refresh cookie."""

    permission_classes = [AllowAny]
    serializer_class = CookieTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        """Rotate the tokens and rewrite both auth cookies."""
        response = super().post(request, *args, **kwargs)
        tokens = response.data
        set_auth_cookies(response, tokens["access"], tokens["refresh"])
        response.data = {"detail": TOKEN_REFRESH_SUCCESS_MESSAGE}
        return response
