"""Tests for the Gemini call of the quiz pipeline."""

from unittest import mock

from django.test import SimpleTestCase, override_settings
from google.genai import errors

from quiz_app.constants import GEMINI_RETRY_DELAY_SECONDS
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

SECOND_ANSWER = '{"title": "A quiz on the second ask"}'

SLEEP_TARGET = "quiz_app.services.gemini.time.sleep"

BUSY_STATUS_CODE = 503

QUOTA_STATUS_CODE = 429

REJECTED_STATUS_CODE = 400


def api_error(code, name):
    """Return the error the SDK raises for one HTTP status."""
    details = {"error": {"code": code, "status": name, "message": name}}
    return errors.APIError(code, details)


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
        """An answer of only whitespace is refused."""
        self.generate.return_value = gemini_response("   \n")
        with self.assertRaises(GeminiRequestError):
            gemini.request_completion(PROMPT)

    def test_an_answer_without_text_is_refused(self):
        """A response that carries no text at all is refused."""
        self.generate.return_value = gemini_response(None)
        with self.assertRaises(GeminiRequestError):
            gemini.request_completion(PROMPT)

    def test_a_response_object_without_a_text_field_is_refused(self):
        """A response without a text attribute is refused."""
        self.generate.return_value = object()
        with self.assertRaises(GeminiRequestError):
            gemini.request_completion(PROMPT)


class TransientRetryTests(GeminiTestCase):
    """Cover the single extra attempt for a busy service."""

    def setUp(self):
        """Patch the client and keep the pause out of the suite."""
        super().setUp()
        self.sleep = self.enterContext(mock.patch(SLEEP_TARGET))

    def busy_then_answer(self, code):
        """Fail the first call with a status, answer the second."""
        self.generate.side_effect = [
            api_error(code, "UNAVAILABLE"),
            gemini_response(SECOND_ANSWER),
        ]

    def test_a_busy_model_is_asked_a_second_time(self):
        """A 503 answer is asked a second time."""
        self.busy_then_answer(BUSY_STATUS_CODE)
        with self.assertLogs(GEMINI_LOGGER, level="WARNING"):
            answer = gemini.request_completion(PROMPT)
        self.assertEqual(answer, SECOND_ANSWER)
        self.assertEqual(self.generate.call_count, 2)

    def test_an_exhausted_quota_is_asked_a_second_time(self):
        """A 429 answer is asked a second time."""
        self.busy_then_answer(QUOTA_STATUS_CODE)
        with self.assertLogs(GEMINI_LOGGER, level="WARNING"):
            gemini.request_completion(PROMPT)
        self.assertEqual(self.generate.call_count, 2)

    def test_the_second_attempt_waits_first(self):
        """The retry sleeps before it asks again."""
        self.busy_then_answer(BUSY_STATUS_CODE)
        with self.assertLogs(GEMINI_LOGGER, level="WARNING"):
            gemini.request_completion(PROMPT)
        self.sleep.assert_called_once_with(GEMINI_RETRY_DELAY_SECONDS)

    def test_the_second_attempt_repeats_the_same_request(self):
        """The retry repeats the identical request."""
        self.busy_then_answer(BUSY_STATUS_CODE)
        with self.assertLogs(GEMINI_LOGGER, level="WARNING"):
            gemini.request_completion(PROMPT)
        first, second = self.generate.call_args_list
        self.assertEqual(first, second)

    def test_two_busy_answers_give_up(self):
        """Two transient failures end the request."""
        self.generate.side_effect = api_error(BUSY_STATUS_CODE, "UNAVAILABLE")
        with (
            self.assertLogs(GEMINI_LOGGER, level="WARNING"),
            self.assertRaises(GeminiRequestError),
        ):
            gemini.request_completion(PROMPT)
        self.assertEqual(self.generate.call_count, 2)

    def test_a_rejected_request_is_not_retried(self):
        """A 400 answer fails without a second attempt."""
        self.generate.side_effect = api_error(
            REJECTED_STATUS_CODE, "INVALID_ARGUMENT"
        )
        with (
            self.assertLogs(GEMINI_LOGGER, level="ERROR"),
            self.assertRaises(GeminiRequestError),
        ):
            gemini.request_completion(PROMPT)
        self.assertEqual(self.generate.call_count, 1)
        self.sleep.assert_not_called()

    def test_a_dropped_connection_is_not_retried(self):
        """A failure without a status code stays a failed request."""
        self.generate.side_effect = RuntimeError("connection reset")
        with (
            self.assertLogs(GEMINI_LOGGER, level="ERROR"),
            self.assertRaises(GeminiRequestError),
        ):
            gemini.request_completion(PROMPT)
        self.assertEqual(self.generate.call_count, 1)

    def test_an_answered_request_never_waits(self):
        """A request answered at once never sleeps."""
        gemini.request_completion(PROMPT)
        self.sleep.assert_not_called()
