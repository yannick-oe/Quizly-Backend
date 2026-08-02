"""The Gemini call of the quiz pipeline."""

import logging

from django.conf import settings
from google import genai
from google.genai import types

from ..constants import (
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRY_STATUS_CODES,
    GEMINI_TIMEOUT_MILLISECONDS,
)
from .exceptions import GeminiRequestError, MissingApiKeyError

LOGGER = logging.getLogger(__name__)

MISSING_API_KEY_MESSAGE = (
    "No Gemini API key is configured. Set GEMINI_API_KEY in .env."
)

REQUEST_FAILED_MESSAGE = "The quiz service did not answer."

EMPTY_RESPONSE_MESSAGE = "The quiz service answered with no content."

FAILURE_LOG_TEMPLATE = "Gemini request failed: %s"


def build_client():
    """Return a Gemini client for the configured API key."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise MissingApiKeyError(MISSING_API_KEY_MESSAGE)
    return genai.Client(api_key=api_key, http_options=_http_options())


def _http_options():
    """Return the timeout and retry policy of every Gemini request."""
    return types.HttpOptions(
        timeout=GEMINI_TIMEOUT_MILLISECONDS,
        retry_options=types.HttpRetryOptions(
            attempts=GEMINI_RETRY_ATTEMPTS,
            http_status_codes=list(GEMINI_RETRY_STATUS_CODES),
        ),
    )


def request_completion(prompt):
    """Return the text Gemini answers a prompt with."""
    client = build_client()
    try:
        response = _generate(client, prompt)
    except Exception as error:
        raise _request_error(error) from error
    return _response_text(response)


def _generate(client, prompt):
    """Send one prompt to Gemini and return its raw response."""
    return client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )


def _request_error(error):
    """Log a failed Gemini call and return the exception for it."""
    LOGGER.error(FAILURE_LOG_TEMPLATE, error)
    return GeminiRequestError(REQUEST_FAILED_MESSAGE)


def _response_text(response):
    """Return the stripped text a Gemini response carries."""
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise GeminiRequestError(EMPTY_RESPONSE_MESSAGE)
    return text
