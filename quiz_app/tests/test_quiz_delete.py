"""Tests for DELETE /api/quizzes/{id}/."""

from quiz_app.models import Question, Quiz

from .helpers import (
    MISSING_QUIZ_ID,
    QuizEndpointTestCase,
    anonymous_client,
    quiz_detail_url,
)


class QuizDeleteTests(QuizEndpointTestCase):
    """Cover the deletion of a single quiz."""

    def delete(self, quiz_id, client=None):
        """Ask for one quiz to be deleted."""
        return (client or self.client).delete(quiz_detail_url(quiz_id))

    def test_an_own_quiz_is_answered_with_204(self):
        """A deleted own quiz answers with 204."""
        self.assertEqual(self.delete(self.quiz.pk).status_code, 204)

    def test_the_answer_has_an_empty_body(self):
        """The 204 answer carries no body."""
        self.assertEqual(self.delete(self.quiz.pk).content, b"")

    def test_the_quiz_is_gone(self):
        """A deleted quiz is deleted, not hidden."""
        self.delete(self.quiz.pk)
        self.assertFalse(Quiz.objects.filter(pk=self.quiz.pk).exists())

    def test_the_questions_are_gone_as_well(self):
        """The cascade takes the questions of the quiz with it."""
        self.delete(self.quiz.pk)
        self.assertFalse(
            Question.objects.filter(quiz_id=self.quiz.pk).exists()
        )

    def test_a_foreign_quiz_answers_403(self):
        """Only the owner may delete a quiz."""
        response = self.delete(self.foreign_quiz.pk)
        self.assertEqual(response.status_code, 403)

    def test_a_refused_deletion_keeps_the_quiz(self):
        """A 403 leaves the quiz of the other user in place."""
        self.delete(self.foreign_quiz.pk)
        self.assertTrue(Quiz.objects.filter(pk=self.foreign_quiz.pk).exists())

    def test_an_unknown_id_answers_404(self):
        """A quiz that does not exist cannot be deleted."""
        self.assertEqual(self.delete(MISSING_QUIZ_ID).status_code, 404)

    def test_an_unauthenticated_request_answers_401(self):
        """Without the access cookie nothing is deleted."""
        response = self.delete(self.quiz.pk, anonymous_client())
        self.assertEqual(response.status_code, 401)
        self.assertTrue(Quiz.objects.filter(pk=self.quiz.pk).exists())
