"""Views for the authentication endpoints."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import CookieJWTAuthentication
from .cookies import set_auth_cookies
from .serializers import (
    LoginSerializer,
    RegistrationSerializer,
    UserSerializer,
)

REGISTRATION_SUCCESS_MESSAGE = "User created successfully!"

LOGIN_SUCCESS_MESSAGE = "Login successfully!"


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


class LoginView(APIView):
    """Authenticate a user and hand out the two auth cookies.

    Authentication is switched off here for the same reason as on the
    registration view.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        """Return the challenge that keeps a 401 from becoming 403.

        DRF coerces 401 into 403 whenever a view has no authenticator
        to build a WWW-Authenticate header from, and this view has
        none by design. Answering with the challenge the rest of the
        API sends keeps the documented 401 for bad credentials.
        """
        return CookieJWTAuthentication().authenticate_header(request)

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
