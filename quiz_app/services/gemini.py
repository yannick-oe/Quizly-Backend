"""The Gemini call of the quiz pipeline."""

import logging
import time
from http import HTTPStatus

from django.conf import settings
from google import genai
from google.genai import errors, types

from ..constants import (
    GEMINI_RETRY_DELAY_SECONDS,
    GEMINI_TIMEOUT_MILLISECONDS,
)
from .exceptions import GeminiRequestError, MissingApiKeyError

LOGGER = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.SERVICE_UNAVAILABLE,
    }
)

MISSING_API_KEY_MESSAGE = (
    "No Gemini API key is configured. Set GEMINI_API_KEY in .env."
)

REQUEST_FAILED_MESSAGE = "The quiz service did not answer."

EMPTY_RESPONSE_MESSAGE = "The quiz service answered with no content."

RETRY_LOG_TEMPLATE = "Gemini is busy, asking once more: %s"

FAILURE_LOG_TEMPLATE = "Gemini request failed: %s"


def build_client():
    """Return a Gemini client for the configured API key."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise MissingApiKeyError(MISSING_API_KEY_MESSAGE)
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MILLISECONDS),
    )


def request_completion(prompt):
    """Return the text Gemini answers a prompt with."""
    client = build_client()
    try:
        response = _generate(client, prompt)
    except Exception as error:
        response = _generate_again(client, prompt, error)
    return _response_text(response)


def _generate(client, prompt):
    """Send one prompt to Gemini and return its raw response."""
    return client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )


def _generate_again(client, prompt, error):
    """Retry a prompt once after a transient failure."""
    if not _is_transient(error):
        raise _request_error(error) from error
    LOGGER.warning(RETRY_LOG_TEMPLATE, error)
    time.sleep(GEMINI_RETRY_DELAY_SECONDS)
    try:
        return _generate(client, prompt)
    except Exception as retry_error:
        raise _request_error(retry_error) from retry_error


def _is_transient(error):
    """Return whether a failure is worth a second attempt."""
    return (
        isinstance(error, errors.APIError)
        and error.code in TRANSIENT_STATUS_CODES
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
