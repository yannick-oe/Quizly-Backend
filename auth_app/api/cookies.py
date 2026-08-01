"""Writing and removal of the cookies that carry the JWT tokens."""

from django.conf import settings

ACCESS_TOKEN_LIFETIME_SETTING = "ACCESS_TOKEN_LIFETIME"

REFRESH_TOKEN_LIFETIME_SETTING = "REFRESH_TOKEN_LIFETIME"

COOKIE_PATH = "/"


def _set_token_cookie(response, name, token, lifetime_setting):
    """Write one auth cookie that expires with its own token."""
    lifetime = settings.SIMPLE_JWT[lifetime_setting]
    response.set_cookie(
        key=name,
        value=token,
        max_age=int(lifetime.total_seconds()),
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path=COOKIE_PATH,
    )


def set_auth_cookies(response, access, refresh):
    """Attach the access and refresh cookies to a response."""
    _set_token_cookie(
        response,
        settings.ACCESS_TOKEN_COOKIE_NAME,
        access,
        ACCESS_TOKEN_LIFETIME_SETTING,
    )
    _set_token_cookie(
        response,
        settings.REFRESH_TOKEN_COOKIE_NAME,
        refresh,
        REFRESH_TOKEN_LIFETIME_SETTING,
    )


def _delete_token_cookie(response, name):
    """Expire one auth cookie the way it was written."""
    response.delete_cookie(
        key=name,
        path=COOKIE_PATH,
        samesite=settings.COOKIE_SAMESITE,
    )


def delete_auth_cookies(response):
    """Remove the access and refresh cookies from a response."""
    _delete_token_cookie(response, settings.ACCESS_TOKEN_COOKIE_NAME)
    _delete_token_cookie(response, settings.REFRESH_TOKEN_COOKIE_NAME)
