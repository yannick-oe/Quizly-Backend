"""Writing of the cookies that carry the JWT tokens.

No token ever appears in a response body, so these cookies are the
only channel through which a client receives one.
"""

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
