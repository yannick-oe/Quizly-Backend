"""Serializers for the authentication endpoints."""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import (
    TokenBlacklistSerializer,
    TokenRefreshSerializer,
)

EMAIL_TAKEN_MESSAGE = "A user with that email already exists."

PASSWORD_MISMATCH_MESSAGE = "The two password fields did not match."

INVALID_CREDENTIALS_MESSAGE = "Invalid username or password."

MISSING_REFRESH_TOKEN_MESSAGE = "No refresh token cookie was sent."


class UserSerializer(serializers.ModelSerializer):
    """Expose the user fields that the login response carries."""

    class Meta:
        """Bind the serializer to Django's user model."""

        model = User
        fields = ("id", "username", "email")


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate a registration request and create the account.

    Passwords keep their surrounding whitespace, the way Django's own
    authentication form does, so that a password survives the trip
    from registration to login unchanged.
    """

    confirmed_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        """Bind the serializer to Django's user model."""

        model = User
        fields = ("username", "password", "confirmed_password", "email")
        extra_kwargs = {
            "email": {"required": True, "allow_blank": False},
            "password": {"write_only": True, "trim_whitespace": False},
        }

    def validate_email(self, value):
        """Reject an email address that is already registered."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(EMAIL_TAKEN_MESSAGE)
        return value

    def validate(self, attrs):
        """Reject a request whose two passwords differ."""
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"confirmed_password": PASSWORD_MISMATCH_MESSAGE}
            )
        return attrs

    def create(self, validated_data):
        """Create the user with a hashed password."""
        validated_data.pop("confirmed_password")
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Turn a username and a password into an authenticated user.

    Both fields are optional at field level on purpose. A missing
    value has to reach validate() so that it fails the same way a
    wrong one does, with the 401 the documentation lists, instead of
    the 400 it does not list for this endpoint.
    """

    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        write_only=True,
    )

    def validate(self, attrs):
        """Authenticate the credentials or fail with 401."""
        user = authenticate(
            request=self.context.get("request"),
            username=attrs.get("username"),
            password=attrs.get("password"),
        )
        if user is None:
            raise AuthenticationFailed(INVALID_CREDENTIALS_MESSAGE)
        attrs["user"] = user
        return attrs


class LogoutSerializer(TokenBlacklistSerializer):
    """Blacklist the refresh token that arrived in the cookie.

    The delivered frontend sends Content-Type: application/json with
    no body at all, so the view feeds the cookie value in as field
    data. A token that is missing or already unusable does not fail
    the logout: the documentation lists 401 for "not authenticated",
    which the access token answers, and the response clears both
    cookies either way.
    """

    refresh = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )

    def validate(self, attrs):
        """Blacklist the token and tolerate an unusable one."""
        if not attrs.get("refresh"):
            return {}
        try:
            return super().validate(attrs)
        except TokenError:
            return {}


class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """Rotate the token pair that arrived in the refresh cookie.

    The delivered frontend sends neither a body nor a Content-Type on
    this request, so the view feeds the cookie value in as field data.
    The field stays optional and a missing value fails the same way an
    invalid one does: the documentation lists 401 for "refresh token
    invalid or missing" and no 400 at all for this endpoint.
    """

    refresh = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """Rotate the pair or refuse the token with 401."""
        if not attrs.get("refresh"):
            raise InvalidToken(MISSING_REFRESH_TOKEN_MESSAGE)
        try:
            return super().validate(attrs)
        except TokenError as error:
            raise InvalidToken(error.args[0]) from error
