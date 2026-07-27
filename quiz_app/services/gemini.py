"""The Gemini call of the quiz pipeline.

This module knows nothing about Quiz, Question or the shape of a quiz.
It sends a prompt and answers with text; judging that text is the job
of the serializer, and chaining the steps is the job of generation.py.
That split is what makes the API replaceable and the tests cheap.

The client is built per call rather than kept in a module variable.
Building it costs nothing measurable, and a cached client would freeze
the API key and the model name of the first request for the lifetime of
the process, which override_settings could then no longer reach.
"""

import logging

from django.conf import settings
from google import genai
from google.genai import types

from .exceptions import GeminiRequestError, MissingApiKeyError

LOGGER = logging.getLogger(__name__)

GEMINI_TIMEOUT_MILLISECONDS = 120_000

MISSING_API_KEY_MESSAGE = (
    "No Gemini API key is configured. Set GEMINI_API_KEY in .env."
)

REQUEST_FAILED_MESSAGE = "The quiz service did not answer."

EMPTY_RESPONSE_MESSAGE = "The quiz service answered with no content."


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
    refused key to a dropped connection, and none of them is worth
    telling apart here. Every one becomes a failed request.
    """
    client = build_client()
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
    except Exception as error:
        LOGGER.error("Gemini request failed: %s", error)
        raise GeminiRequestError(REQUEST_FAILED_MESSAGE) from error
    return _response_text(response)


def _response_text(response):
    """Return the stripped text a Gemini response carries."""
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise GeminiRequestError(EMPTY_RESPONSE_MESSAGE)
    return text
