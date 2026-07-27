"""Tests for the Gemini call of the quiz pipeline.

google.genai.Client is replaced in every test through
quiz_app.services.gemini.genai.Client. No test builds a real client,
so nothing here opens a socket or needs an API key, and the key the
tests do configure is a string that never leaves the process.
"""

from unittest import mock

from django.test import SimpleTestCase, override_settings

from quiz_app.services import gemini
from quiz_app.services.exceptions import (
    GeminiRequestError,
    MissingApiKeyError,
)

from .helpers import GEMINI_CLIENT_TARGET, GEMINI_LOGGER, gemini_response

API_KEY = "test-key-not-a-real-one"

MODEL = "gemini-3.5-flash"

PROMPT = "Turn this transcript into a quiz."

ANSWER = '{"title": "A quiz"}'

PADDED_ANSWER = f"\n  {ANSWER}  \n"


@override_settings(GEMINI_API_KEY=API_KEY, GEMINI_MODEL=MODEL)
class GeminiTestCase(SimpleTestCase):
    """Replace the SDK client for every test in this module."""

    def setUp(self):
        """Patch the client class and hand back a stock answer."""
        self.client_class = self.enterContext(mock.patch(GEMINI_CLIENT_TARGET))
        self.generate = self.client_class.return_value.models.generate_content
        self.generate.return_value = gemini_response(ANSWER)


class BuildClientTests(GeminiTestCase):
    """Cover how the client is configured before it is used."""

    def test_the_configured_key_is_handed_to_the_sdk(self):
        """The client is built with the key from the settings."""
        gemini.build_client()
        self.assertEqual(
            self.client_class.call_args.kwargs["api_key"], API_KEY
        )

    def test_the_request_carries_a_timeout(self):
        """No Gemini call is allowed to hang without a limit."""
        gemini.build_client()
        options = self.client_class.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, gemini.GEMINI_TIMEOUT_MILLISECONDS)

    @override_settings(GEMINI_API_KEY="")
    def test_a_missing_key_raises_before_the_client_is_built(self):
        """An unconfigured installation fails with a named error."""
        with self.assertRaises(MissingApiKeyError):
            gemini.build_client()
        self.client_class.assert_not_called()

    @override_settings(GEMINI_API_KEY="")
    def test_the_missing_key_message_names_the_variable(self):
        """The message says which variable has to be filled in."""
        self.assertIn("GEMINI_API_KEY", gemini.MISSING_API_KEY_MESSAGE)


class RequestCompletionTests(GeminiTestCase):
    """Cover the request itself and the answer it produces."""

    def test_the_prompt_and_the_model_reach_the_sdk(self):
        """The call names the configured model and the prompt."""
        gemini.request_completion(PROMPT)
        self.generate.assert_called_once_with(model=MODEL, contents=PROMPT)

    def test_the_answer_is_returned_stripped(self):
        """Padding around the answer never reaches the caller."""
        self.generate.return_value = gemini_response(PADDED_ANSWER)
        self.assertEqual(gemini.request_completion(PROMPT), ANSWER)

    def test_an_sdk_failure_becomes_our_exception(self):
        """No SDK exception escapes the service layer."""
        self.generate.side_effect = RuntimeError("connection reset")
        with (
            self.assertLogs(GEMINI_LOGGER, level="ERROR"),
            self.assertRaises(GeminiRequestError),
        ):
            gemini.request_completion(PROMPT)

    @override_settings(GEMINI_API_KEY="")
    def test_a_missing_key_stops_the_request(self):
        """Without a key nothing is sent at all."""
        with self.assertRaises(MissingApiKeyError):
            gemini.request_completion(PROMPT)
        self.generate.assert_not_called()

    def test_an_empty_answer_is_refused(self):
        """An answer of whitespace is not an answer."""
        self.generate.return_value = gemini_response("   \n")
        with self.assertRaises(GeminiRequestError):
            gemini.request_completion(PROMPT)

    def test_an_answer_without_text_is_refused(self):
        """A response that carries no text at all is refused."""
        self.generate.return_value = gemini_response(None)
        with self.assertRaises(GeminiRequestError):
            gemini.request_completion(PROMPT)

    def test_a_response_object_without_a_text_field_is_refused(self):
        """A shape the SDK never promised does not crash the call."""
        self.generate.return_value = object()
        with self.assertRaises(GeminiRequestError):
            gemini.request_completion(PROMPT)
