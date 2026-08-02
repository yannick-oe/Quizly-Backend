"""Serializers for the authentication endpoints."""

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenBlacklistSerializer,
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

EMAIL_TAKEN_MESSAGE = "A user with that email already exists."

PASSWORD_MISMATCH_MESSAGE = "The two password fields did not match."

INVALID_CREDENTIALS_MESSAGE = "Invalid username or password."

REFRESH_TOKEN_FIELD = "refresh"


class UserSerializer(serializers.ModelSerializer):
    """Expose the user fields that the login response carries."""

    class Meta:
        """Bind the serializer to Django's user model."""

        model = User
        fields = ("id", "username", "email")


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate a registration request and create the account."""

    confirmed_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        """Bind the serializer to Django's user model."""

        model = User
        fields = ("username", "password", "confirmed_password", "email")
        extra_kwargs = {
            "email": {
                "required": True,
                "allow_blank": False,
                "validators": [
                    UniqueValidator(
                        queryset=User.objects.all(),
                        message=EMAIL_TAKEN_MESSAGE,
                        lookup="iexact",
                    )
                ],
            },
            "password": {"write_only": True, "trim_whitespace": False},
        }

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


class LoginSerializer(TokenObtainPairSerializer):
    """Validate credentials into token data that carries the user."""

    default_error_messages = {
        "no_active_account": INVALID_CREDENTIALS_MESSAGE,
    }

    def validate(self, attrs):
        """Return the token pair with the serialized user added."""
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(TokenBlacklistSerializer):
    """Blacklist the refresh token that arrived in the cookie."""

    refresh = None

    def validate(self, attrs):
        """Blacklist the token and tolerate an unusable one."""
        attrs[REFRESH_TOKEN_FIELD] = self.context["request"].COOKIES.get(
            settings.REFRESH_TOKEN_COOKIE_NAME, ""
        )
        if not attrs[REFRESH_TOKEN_FIELD]:
            return {}
        try:
            return super().validate(attrs)
        except TokenError:
            return {}


class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """Rotate the token pair that arrives in the refresh cookie."""

    refresh = None

    def validate(self, attrs):
        """Rotate the pair after reading the token from the cookie."""
        attrs[REFRESH_TOKEN_FIELD] = self.context["request"].COOKIES.get(
            settings.REFRESH_TOKEN_COOKIE_NAME, ""
        )
        return super().validate(attrs)
