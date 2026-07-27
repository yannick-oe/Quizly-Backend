"""Shared helpers for the auth_app endpoint tests."""

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

USERNAME = "quizmaster"

PASSWORD = "correct-horse-battery"

EMAIL = "quizmaster@example.com"

ACCESS_COOKIE = settings.ACCESS_TOKEN_COOKIE_NAME

REFRESH_COOKIE = settings.REFRESH_TOKEN_COOKIE_NAME


def create_user(**overrides):
    """Create the account that the tests authenticate with."""
    fields = {
        "username": USERNAME,
        "password": PASSWORD,
        "email": EMAIL,
    }
    fields.update(overrides)
    return User.objects.create_user(**fields)


def log_in(client):
    """Log a client in so that it holds both auth cookies."""
    return client.post(
        reverse("login"),
        data={"username": USERNAME, "password": PASSWORD},
        content_type="application/json",
    )
