"""Tests for POST /api/quizzes/.

generate_quiz is replaced where the view imports it, so no test here
downloads, transcribes or asks Gemini anything. The stand-in stores a
real quiz for the user and the URL it is handed, which is what lets
these tests check that the owner comes from the request and not from
the body.

The failure tests are the point of the module. The endpoint
documentation names 400 and 500 for this route, the service layer
raises seven different exceptions, and which of them lands in which
class is a decision that has to stay visible.
"""

from unittest import mock

from quiz_app.constants import QUESTIONS_PER_QUIZ
from quiz_app.models import Quiz
from quiz_app.services.exceptions import (
    AudioConversionError,
    GeminiRequestError,
    InvalidVideoError,
    MissingApiKeyError,
    QuizContentError,
    TranscriptionError,
    VideoTooLongError,
)

from .helpers import (
    GENERATE_QUIZ_TARGET,
    VIDEO_ID,
    VIDEO_URL,
    VIEWS_LOGGER,
    QuizEndpointTestCase,
    anonymous_client,
    create_quiz,
    quiz_list_url,
)

SHORT_LINK = f"https://youtu.be/{VIDEO_ID}"

FOREIGN_LINK = "https://vimeo.com/76979871"

TOO_LONG_MESSAGE = "The video is longer than the supported maximum."

SILENT_MESSAGE = "No speech was found in the video."

API_KEY_MESSAGE = "Set GEMINI_API_KEY in .env."

OWNER_FIELD = "owner"

DETAIL_KEY = "detail"

QUESTIONS_KEY = "questions"

URL_FIELD = "url"


def stored_quiz(user, url):
    """Stand in for the pipeline by storing a quiz right away."""
    return create_quiz(user, video_url=url)


class QuizCreateTestCase(QuizEndpointTestCase):
    """Replace the generation pipeline for every test."""

    def setUp(self):
        """Authenticate and put a stand-in in place of the pipeline."""
        super().setUp()
        self.generate = self.enterContext(mock.patch(GENERATE_QUIZ_TARGET))
        self.generate.side_effect = stored_quiz

    def post(self, body):
        """Send a request body to the quiz collection."""
        return self.client.post(
            quiz_list_url(),
            data=body,
            content_type="application/json",
        )


class HappyPathTests(QuizCreateTestCase):
    """Cover the run that answers with a finished quiz."""

    def test_a_generated_quiz_is_answered_with_201(self):
        """The documented success code is 201, not 200."""
        response = self.post({URL_FIELD: VIDEO_URL})
        self.assertEqual(response.status_code, 201)

    def test_the_answer_carries_the_whole_quiz(self):
        """The documentation shows the finished quiz in the body."""
        body = self.post({URL_FIELD: VIDEO_URL}).json()
        self.assertEqual(body["video_url"], VIDEO_URL)
        self.assertEqual(len(body[QUESTIONS_KEY]), QUESTIONS_PER_QUIZ)

    def test_the_quiz_is_generated_for_the_requesting_user(self):
        """The owner comes from the cookie, never from the body."""
        self.post({URL_FIELD: VIDEO_URL})
        self.generate.assert_called_once_with(self.user, VIDEO_URL)

    def test_the_stored_quiz_belongs_to_the_requesting_user(self):
        """What is stored carries the owner the request named."""
        quiz_id = self.post({URL_FIELD: VIDEO_URL}).json()["id"]
        self.assertEqual(Quiz.objects.get(pk=quiz_id).owner, self.user)

    def test_the_answer_names_no_owner(self):
        """The documented quiz object has no user reference."""
        self.assertNotIn(OWNER_FIELD, self.post({URL_FIELD: VIDEO_URL}).json())

    def test_a_short_link_reaches_the_service_in_watch_form(self):
        """The frontend needs the v= form to embed the video."""
        self.post({URL_FIELD: SHORT_LINK})
        self.generate.assert_called_once_with(self.user, VIDEO_URL)


class RequestRejectionTests(QuizCreateTestCase):
    """Cover the bodies that never reach the pipeline."""

    def test_a_link_that_is_not_youtube_answers_400(self):
        """An unusable URL is refused before anything is fetched."""
        response = self.post({URL_FIELD: FOREIGN_LINK})
        self.assertEqual(response.status_code, 400)
        self.generate.assert_not_called()

    def test_the_refusal_names_the_url_field(self):
        """The error belongs to the field the client filled in."""
        self.assertIn(URL_FIELD, self.post({URL_FIELD: FOREIGN_LINK}).json())

    def test_a_missing_url_answers_400(self):
        """A body without a URL is not a request for a quiz."""
        self.assertEqual(self.post({}).status_code, 400)

    def test_an_empty_url_answers_400(self):
        """An empty string is not a link either."""
        self.assertEqual(self.post({URL_FIELD: ""}).status_code, 400)

    def test_an_unauthenticated_request_answers_401(self):
        """The route needs the access cookie, not a 403."""
        response = anonymous_client().post(
            quiz_list_url(),
            data={URL_FIELD: VIDEO_URL},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)


class ClientFailureTests(QuizCreateTestCase):
    """Cover the pipeline failures that are the client's problem."""

    def assert_answers_400(self, error):
        """Assert a failure becomes a 400 that carries its reason."""
        self.generate.side_effect = error
        with self.assertLogs(VIEWS_LOGGER, level="WARNING"):
            response = self.post({URL_FIELD: VIDEO_URL})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()[DETAIL_KEY], str(error))

    def test_a_video_that_cannot_be_read_answers_400(self):
        """A private or removed video is a fault of the URL."""
        self.assert_answers_400(InvalidVideoError(SILENT_MESSAGE))

    def test_a_video_that_is_too_long_answers_400(self):
        """The duration limit answers with the documented 400."""
        self.assert_answers_400(VideoTooLongError(TOO_LONG_MESSAGE))

    def test_a_refused_video_stores_nothing(self):
        """A refused request leaves the quiz table as it was."""
        self.generate.side_effect = VideoTooLongError(TOO_LONG_MESSAGE)
        before = Quiz.objects.count()
        with self.assertLogs(VIEWS_LOGGER, level="WARNING"):
            self.post({URL_FIELD: VIDEO_URL})
        self.assertEqual(Quiz.objects.count(), before)


class ServerFailureTests(QuizCreateTestCase):
    """Cover the pipeline failures that are ours."""

    def assert_answers_500(self, error):
        """Assert a failure becomes a logged 500 with a fixed text."""
        self.generate.side_effect = error
        with self.assertLogs(VIEWS_LOGGER, level="ERROR") as logs:
            response = self.post({URL_FIELD: VIDEO_URL})
        self.assertEqual(response.status_code, 500)
        self.assertIn(str(error), logs.output[0])
        return response.json()[DETAIL_KEY]

    def test_a_broken_conversion_answers_500(self):
        """A failing FFmpeg is a broken tool chain, not a bad URL."""
        self.assert_answers_500(AudioConversionError("ffmpeg is gone"))

    def test_a_broken_transcription_answers_500(self):
        """Whisper failing is ours to fix, not the client's."""
        self.assert_answers_500(TranscriptionError("whisper died"))

    def test_a_failed_gemini_request_answers_500(self):
        """A quiz service that does not answer is a server fault."""
        self.assert_answers_500(GeminiRequestError("no answer"))

    def test_unusable_gemini_output_answers_500(self):
        """Two unusable answers end the request with a 500."""
        self.assert_answers_500(QuizContentError("still unusable"))

    def test_a_missing_api_key_answers_500(self):
        """An unconfigured installation is not the client's fault."""
        self.assert_answers_500(MissingApiKeyError(API_KEY_MESSAGE))

    def test_a_500_keeps_the_internal_message_to_itself(self):
        """The body says nothing about keys, models or binaries."""
        detail = self.assert_answers_500(MissingApiKeyError(API_KEY_MESSAGE))
        self.assertNotIn(API_KEY_MESSAGE, detail)

    def test_a_failed_generation_stores_nothing(self):
        """A 500 leaves no half-written quiz behind."""
        self.generate.side_effect = TranscriptionError("whisper died")
        before = Quiz.objects.count()
        with self.assertLogs(VIEWS_LOGGER, level="ERROR"):
            self.post({URL_FIELD: VIDEO_URL})
        self.assertEqual(Quiz.objects.count(), before)
