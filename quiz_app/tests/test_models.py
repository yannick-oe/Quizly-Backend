"""Tests for the string representation of the quiz models."""

from django.contrib.auth.models import User
from django.test import TestCase

from quiz_app.models import QUESTION_TITLE_PREVIEW_LENGTH, Question, Quiz

from .helpers import VIDEO_URL

QUIZ_TITLE = "The Fall of the Roman Republic"

LONG_QUESTION_TITLE = "Which of these events came first in the sequence? " * 3

ELLIPSIS = "…"


class QuizStringTests(TestCase):
    """Cover the display names of a quiz and of its questions."""

    def setUp(self):
        """Create one quiz to hang the questions off."""
        owner = User.objects.create_user(
            username="quizmaster",
            password="correct-horse-battery",
        )
        self.quiz = Quiz.objects.create(
            owner=owner,
            title=QUIZ_TITLE,
            description="Generated from a lecture recording.",
            video_url=VIDEO_URL,
        )

    def make_question(self, question_title):
        """Create a question belonging to the quiz."""
        return Question.objects.create(
            quiz=self.quiz,
            question_title=question_title,
            question_options=["Caesar", "Sulla", "Marius", "Pompey"],
            answer="Sulla",
        )

    def test_a_quiz_is_named_after_its_title(self):
        """A quiz shows its title unchanged."""
        self.assertEqual(str(self.quiz), QUIZ_TITLE)

    def test_a_short_question_title_is_shown_unchanged(self):
        """A question that fits is not truncated."""
        question = self.make_question("Who marched on Rome first?")
        self.assertEqual(str(question), "Who marched on Rome first?")

    def test_a_long_question_title_is_shortened(self):
        """A long question title is cut to the preview length."""
        question = self.make_question(LONG_QUESTION_TITLE)
        preview = str(question)
        self.assertLessEqual(len(preview), QUESTION_TITLE_PREVIEW_LENGTH)
        self.assertTrue(preview.endswith(ELLIPSIS))
