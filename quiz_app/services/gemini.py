"""The Gemini call of the quiz pipeline.

This module knows nothing about Quiz, Question or the shape of a quiz.
It sends a prompt and answers with text; judging that text is the job
of the serializer, and chaining the steps is the job of generation.py.
That split is what makes the API replaceable and the tests cheap.

The client is built per call rather than kept in a module variable.
Building it costs nothing measurable, and a cached client would freeze
the API key and the model name of the first request for the lifetime of
the process, which override_settings could then no longer reach.

A prompt is sent twice at most, and the second time only after a
failure that says "not now": 429 when the quota is exhausted for the
moment, 503 when the model is under load. Anything else is final. A
refused key does not become valid on the second ask, and a rejected
request is rejected the same way twice, so a retry there would only
add latency to a request the client is already waiting on.

That decision is made on the status code the SDK carries in its own
APIError and never on the wording of the message, which is free text
of the service and can change without notice.

This retry is not the one in generation.py. That one asks again because
the answer was unusable; this one asks again because there was no
answer at all.
"""

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
    """Return a Gemini client for the configured API key.

    The key is checked here and not at startup. The test suite has to
    run without one, so a missing key is a warning of the system check
    in quiz_app/checks.py and an exception at this point.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise MissingApiKeyError(MISSING_API_KEY_MESSAGE)
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MILLISECONDS),
    )


def request_completion(prompt):
    """Return the text Gemini answers a prompt with.

    The SDK fails in as many ways as the network below it, from a
    refused key to a dropped connection. Only a busy service earns a
    second attempt; every other failure becomes a failed request.
    """
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
    """Ask a second time after a failure that may pass.

    A failure that is not transient leaves as ours right here, so the
    second call only ever happens for a service that was busy.
    """
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
