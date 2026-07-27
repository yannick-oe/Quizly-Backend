"""Views for the authentication endpoints."""

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import CookieJWTAuthentication
from .cookies import delete_auth_cookies, set_auth_cookies
from .serializers import (
    CookieTokenRefreshSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegistrationSerializer,
    UserSerializer,
)

REGISTRATION_SUCCESS_MESSAGE = "User created successfully!"

LOGIN_SUCCESS_MESSAGE = "Login successfully!"

LOGOUT_SUCCESS_MESSAGE = (
    "Log-Out successfully! All Tokens will be deleted. "
    "Refresh token is now invalid."
)

TOKEN_REFRESH_SUCCESS_MESSAGE = "Token refreshed"

REFRESH_TOKEN_FIELD = "refresh"


def _refresh_cookie_data(request):
    """Return the refresh cookie value as serializer input data."""
    raw_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    return {REFRESH_TOKEN_FIELD: raw_token or ""}


class CookieChallengeMixin:
    """Keep DRF from downgrading a 401 into a 403.

    DRF coerces 401 into 403 whenever a view has no authenticator to
    build a WWW-Authenticate header from, and the endpoints a logged
    out client calls have none by design. Answering with the challenge
    the rest of the API sends keeps the documented 401.
    """

    def get_authenticate_header(self, request):
        """Return the challenge that the API authenticator sends."""
        return CookieJWTAuthentication().authenticate_header(request)


class RegistrationView(APIView):
    """Create a user account.

    Authentication is switched off rather than left at the default.
    DRF authenticates before it checks permissions, so an expired
    access token cookie would answer 401 on one of the two endpoints
    a logged out visitor needs.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Create the account and answer with the fixed message."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": REGISTRATION_SUCCESS_MESSAGE},
            status=status.HTTP_201_CREATED,
        )


class LoginView(CookieChallengeMixin, APIView):
    """Authenticate a user and hand out the two auth cookies.

    Authentication is switched off here for the same reason as on the
    registration view. The mixin keeps the documented 401 for bad
    credentials reachable without an authenticator.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Log the user in and attach both auth cookies."""
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return self._login_response(serializer.validated_data["user"])

    def _login_response(self, user):
        """Build the login body and attach both auth cookies."""
        refresh = RefreshToken.for_user(user)
        payload = {
            "detail": LOGIN_SUCCESS_MESSAGE,
            "user": UserSerializer(user).data,
        }
        response = Response(payload)
        set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


class LogoutView(APIView):
    """Log a user out and invalidate the refresh token.

    The delivered frontend sends no request body here, so nothing is
    read from it. The refresh token comes from its cookie, and both
    cookies are removed from the client afterwards.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Blacklist the refresh token and clear both cookies."""
        serializer = LogoutSerializer(data=_refresh_cookie_data(request))
        serializer.is_valid(raise_exception=True)
        response = Response({"detail": LOGOUT_SUCCESS_MESSAGE})
        delete_auth_cookies(response)
        return response


class TokenRefreshView(CookieChallengeMixin, APIView):
    """Rotate the token pair carried by the refresh cookie.

    Authentication is switched off: a client refreshes precisely
    because its access token is gone or expired, and the default
    authenticator would answer 401 before the refresh cookie is ever
    read. The refresh cookie is the credential of this endpoint.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Rotate the tokens and rewrite both auth cookies."""
        serializer = CookieTokenRefreshSerializer(
            data=_refresh_cookie_data(request)
        )
        serializer.is_valid(raise_exception=True)
        return self._refresh_response(serializer.validated_data)

    def _refresh_response(self, tokens):
        """Answer with the fixed message and both fresh cookies."""
        response = Response({"detail": TOKEN_REFRESH_SUCCESS_MESSAGE})
        set_auth_cookies(response, tokens["access"], tokens["refresh"])
        return response
