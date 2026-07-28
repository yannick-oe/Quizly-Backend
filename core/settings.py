"""Django settings for the core project.

Environment-specific values are read from the environment, with .env
loaded on start; see .env.example for the variables this project uses.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

ENV_TRUE_VALUES = ("1", "true", "yes", "on")


def get_required_env(name):
    """Return a required environment variable or fail loudly."""
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(
            f"Environment variable {name} is missing or empty. "
            "Copy .env.example to .env and fill in a value."
        )
    return value


def get_bool_env(name, default):
    """Return an environment variable parsed as a boolean."""
    return os.getenv(name, default).strip().lower() in ENV_TRUE_VALUES


def get_list_env(name, default):
    """Return an environment variable split on commas."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_env(name, default):
    """Return an environment variable, or a default when it is empty."""
    return os.getenv(name, "").strip() or default


SECRET_KEY = get_required_env("SECRET_KEY")

DEBUG = get_bool_env("DEBUG", "False")

ALLOWED_HOSTS = get_list_env("ALLOWED_HOSTS", "127.0.0.1,localhost")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "auth_app.apps.AuthAppConfig",
    "quiz_app.apps.QuizAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation" ".MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".NumericPasswordValidator"
        ),
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"


# Cross-origin requests

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = get_list_env(
    "CORS_ALLOWED_ORIGINS", "http://127.0.0.1:5500"
)


# Django REST Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "auth_app.api.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


# JSON Web Tokens

ACCESS_TOKEN_LIFETIME_MINUTES = 60

REFRESH_TOKEN_LIFETIME_DAYS = 1

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

ACCESS_TOKEN_COOKIE_NAME = "access_token"

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"

COOKIE_HTTPONLY = True

COOKIE_SAMESITE = "Lax"

COOKIE_SECURE = get_bool_env("COOKIE_SECURE", "False")


# Audio transcription

DEFAULT_WHISPER_MODEL = "base"

WHISPER_MODEL = get_env("WHISPER_MODEL", DEFAULT_WHISPER_MODEL)


# Quiz generation

GEMINI_API_KEY = get_env("GEMINI_API_KEY", "")

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

GEMINI_MODEL = get_env("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
