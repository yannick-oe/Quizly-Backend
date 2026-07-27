"""Tests for the chain from a YouTube URL to a stored quiz.

Three seams are replaced in every test: prepared_audio for the
download and the FFmpeg call, transcribe_audio for Whisper, and
request_completion for Gemini. Nothing here starts a subprocess, opens
a socket or loads a model.

The retry tests count calls rather than only checking the outcome. One
repair attempt is the contract, so both "it gave up too early" and "it
kept asking" have to fail here rather than in production.
"""

from contextlib import contextmanager
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from quiz_app.models import Question, Quiz
from quiz_app.services import generation
from quiz_app.services.exceptions import (
    GeminiRequestError,
    InvalidVideoError,
    QuizContentError,
    TranscriptionError,
)

from .helpers import (
    BUILD_QUESTION_TARGET,
    GENERATION_LOGGER,
    PREPARED_AUDIO_TARGET,
    QUIZ_DESCRIPTION,
    QUIZ_TITLE,
    REQUEST_COMPLETION_TARGET,
    TRANSCRIBE_AUDIO_TARGET,
    TRANSCRIPT,
    VIDEO_ID,
    VIDEO_URL,
    as_fenced_json,
    as_json,
    payload_with_first_question,
    question_options,
    quiz_payload,
)

SHORT_LINK = f"https://youtu.be/{VIDEO_ID}"

AUDIO_PATH = "/tmp/quizly/audio.wav"

BROKEN_JSON = "I am afraid I cannot do that."

UNUSABLE_QUIZ = as_json(quiz_payload(questions=[]))


@contextmanager
def fake_audio(url):
    """Stand in for the download, the conversion and the cleanup."""
    yield AUDIO_PATH


class GenerationTestCase(TestCase):
    """Replace every external step of the pipeline."""

    @classmethod
    def setUpTestData(cls):
        """Create the user the generated quizzes belong to."""
        cls.user = User.objects.create_user(
            username="quizmaster",
            password="correct-horse-battery",
        )

    def setUp(self):
        """Patch the audio, the transcription and Gemini."""
        self.enterContext(
            mock.patch(PREPARED_AUDIO_TARGET, side_effect=fake_audio)
        )
        self.transcribe = self.enterContext(
            mock.patch(TRANSCRIBE_AUDIO_TARGET, return_value=TRANSCRIPT)
        )
        self.completion = self.enterContext(
            mock.patch(REQUEST_COMPLETION_TARGET)
        )
        self.completion.return_value = as_json(quiz_payload())

    def generate(self, url=VIDEO_URL):
        """Run the pipeline for a URL."""
        return generation.generate_quiz(self.user, url)

    def assert_nothing_was_stored(self):
        """Assert neither a quiz nor a question survived."""
        self.assertEqual(Quiz.objects.count(), 0)
        self.assertEqual(Question.objects.count(), 0)


class HappyPathTests(GenerationTestCase):
    """Cover the run that produces a quiz."""

    def test_a_quiz_is_stored_with_its_questions(self):
        """One run leaves one quiz with the full set of questions."""
        quiz = self.generate()
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertEqual(quiz.title, QUIZ_TITLE)
        self.assertEqual(quiz.description, QUIZ_DESCRIPTION)
        self.assertEqual(
            quiz.questions.count(), len(quiz_payload()["questions"])
        )

    def test_the_quiz_belongs_to_the_user_that_asked(self):
        """The owner comes from the caller, not from the payload."""
        self.assertEqual(self.generate().owner, self.user)

    def test_a_short_link_is_stored_in_the_watch_form(self):
        """The frontend needs the v= form to embed the video."""
        self.assertEqual(self.generate(SHORT_LINK).video_url, VIDEO_URL)

    def test_the_questions_carry_options_and_answer(self):
        """A stored question holds what the frontend renders."""
        first = self.generate().questions.first()
        self.assertEqual(first.question_options, question_options(1))
        self.assertEqual(first.answer, question_options(1)[0])

    def test_the_transcript_is_asked_for_before_gemini(self):
        """Whisper runs on the prepared audio, Gemini on its text."""
        self.generate()
        self.transcribe.assert_called_once_with(AUDIO_PATH)
        self.assertIn(TRANSCRIPT, self.completion.call_args.args[0])

    def test_a_fenced_answer_is_accepted(self):
        """Gemini wrapping its JSON does not cost the run."""
        self.completion.return_value = as_fenced_json(
            quiz_payload(), language="json"
        )
        self.assertEqual(self.generate().title, QUIZ_TITLE)

    def test_padded_values_are_stored_stripped(self):
        """No stored answer carries padding the frontend would see."""
        options = question_options(1)
        self.completion.return_value = as_json(
            payload_with_first_question(answer=f"  {options[0]}  ")
        )
        first = self.generate().questions.first()
        self.assertEqual(first.answer, options[0])


class UrlRejectionTests(GenerationTestCase):
    """Cover the URL check that runs before anything is fetched."""

    def test_a_foreign_url_is_refused(self):
        """A link that is not a YouTube video never starts a run."""
        with self.assertRaises(InvalidVideoError):
            self.generate("https://vimeo.com/76979871")
        self.transcribe.assert_not_called()
        self.completion.assert_not_called()

    def test_a_refused_url_stores_nothing(self):
        """The database is untouched after a refused URL."""
        with self.assertRaises(InvalidVideoError):
            self.generate("not a url at all")
        self.assert_nothing_was_stored()


class RetryTests(GenerationTestCase):
    """Cover the one repair attempt and its hard stop."""

    def test_an_unusable_answer_is_retried_once(self):
        """A second, stricter prompt rescues a failed first try."""
        self.completion.side_effect = [
            BROKEN_JSON,
            as_json(quiz_payload()),
        ]
        with self.assertLogs(GENERATION_LOGGER, level="WARNING"):
            quiz = self.generate()
        self.assertEqual(self.completion.call_count, 2)
        self.assertEqual(quiz.title, QUIZ_TITLE)

    def test_the_retry_uses_a_different_prompt(self):
        """The repair attempt does not repeat the same words."""
        self.completion.side_effect = [
            BROKEN_JSON,
            as_json(quiz_payload()),
        ]
        with self.assertLogs(GENERATION_LOGGER, level="WARNING"):
            self.generate()
        first, second = self.completion.call_args_list
        self.assertNotEqual(first.args[0], second.args[0])

    def test_a_refused_quiz_is_retried_as_well(self):
        """Valid JSON that breaks a rule counts as unusable."""
        self.completion.side_effect = [
            UNUSABLE_QUIZ,
            as_json(quiz_payload()),
        ]
        with self.assertLogs(GENERATION_LOGGER, level="WARNING"):
            self.generate()
        self.assertEqual(self.completion.call_count, 2)

    def test_two_unusable_answers_give_up(self):
        """The pipeline stops after the repair attempt."""
        self.completion.side_effect = [BROKEN_JSON, UNUSABLE_QUIZ]
        with (
            self.assertLogs(GENERATION_LOGGER, level="WARNING"),
            self.assertRaises(QuizContentError),
        ):
            self.generate()
        self.assertEqual(self.completion.call_count, 2)

    def test_giving_up_stores_nothing(self):
        """Two failed attempts leave the database as it was."""
        self.completion.side_effect = [BROKEN_JSON, BROKEN_JSON]
        with (
            self.assertLogs(GENERATION_LOGGER, level="WARNING"),
            self.assertRaises(QuizContentError),
        ):
            self.generate()
        self.assert_nothing_was_stored()


class FailurePropagationTests(GenerationTestCase):
    """Cover the failures that are not worth a second attempt."""

    def test_a_failed_request_is_not_retried(self):
        """A broken API answers the same way on the second call."""
        self.completion.side_effect = GeminiRequestError("no answer")
        with self.assertRaises(GeminiRequestError):
            self.generate()
        self.assertEqual(self.completion.call_count, 1)

    def test_a_failed_request_stores_nothing(self):
        """A failure at the Gemini step leaves no rows behind."""
        self.completion.side_effect = GeminiRequestError("no answer")
        with self.assertRaises(GeminiRequestError):
            self.generate()
        self.assert_nothing_was_stored()

    def test_a_silent_video_never_reaches_gemini(self):
        """A video without speech stops at the transcription."""
        self.transcribe.side_effect = InvalidVideoError("no speech")
        with self.assertRaises(InvalidVideoError):
            self.generate()
        self.completion.assert_not_called()
        self.assert_nothing_was_stored()

    def test_a_broken_tool_chain_leaves_as_it_is(self):
        """A transcription failure keeps its own exception class."""
        self.transcribe.side_effect = TranscriptionError("whisper died")
        with self.assertRaises(TranscriptionError):
            self.generate()
        self.assert_nothing_was_stored()


class AtomicWriteTests(GenerationTestCase):
    """Cover the rollback that keeps half a quiz out of the tables."""

    def test_a_failure_between_the_writes_rolls_back(self):
        """A quiz without its questions is never left behind."""
        failure = mock.patch(
            BUILD_QUESTION_TARGET, side_effect=ValueError("boom")
        )
        with failure, self.assertRaises(ValueError):
            self.generate()
        self.assert_nothing_was_stored()
