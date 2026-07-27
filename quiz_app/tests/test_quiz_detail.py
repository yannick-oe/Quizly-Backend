"""Tests for GET /api/quizzes/{id}/.

The three refusals are asserted separately and on purpose. The
endpoint documentation lists 401, 403 and 404 as three different
cases, and the 403 is the one that only survives because the detail
queryset is not filtered on the owner. A refactor that filters it
would turn the 403 into a 404 without breaking anything else, so that
distinction is checked here rather than assumed.
"""

from quiz_app.constants import QUESTIONS_PER_QUIZ

from .helpers import (
    MISSING_QUIZ_ID,
    QUIZ_TITLE,
    QuizEndpointTestCase,
    anonymous_client,
    quiz_detail_url,
)

OWNER_FIELD = "owner"

QUESTIONS_KEY = "questions"


class QuizDetailTests(QuizEndpointTestCase):
    """Cover reading a single quiz."""

    def get_detail(self, quiz_id, client=None):
        """Request one quiz by its id."""
        return (client or self.client).get(quiz_detail_url(quiz_id))

    def test_an_own_quiz_is_answered_with_200(self):
        """The owner may read their own quiz."""
        self.assertEqual(self.get_detail(self.quiz.pk).status_code, 200)

    def test_the_answer_carries_the_quiz_and_its_questions(self):
        """The documented body holds the details and the questions."""
        body = self.get_detail(self.quiz.pk).json()
        self.assertEqual(body["title"], QUIZ_TITLE)
        self.assertEqual(len(body[QUESTIONS_KEY]), QUESTIONS_PER_QUIZ)

    def test_the_answer_names_no_owner(self):
        """The documented quiz object has no user reference."""
        self.assertNotIn(OWNER_FIELD, self.get_detail(self.quiz.pk).json())

    def test_a_foreign_quiz_answers_403_and_not_404(self):
        """A quiz of another user is refused, not hidden."""
        response = self.get_detail(self.foreign_quiz.pk)
        self.assertEqual(response.status_code, 403)

    def test_a_foreign_quiz_is_not_disclosed(self):
        """A refused request answers with no quiz data at all."""
        body = self.get_detail(self.foreign_quiz.pk).json()
        self.assertNotIn("title", body)

    def test_an_unknown_id_answers_404(self):
        """A quiz that does not exist is the other documented case."""
        self.assertEqual(self.get_detail(MISSING_QUIZ_ID).status_code, 404)

    def test_an_unauthenticated_request_answers_401(self):
        """Without the access cookie the answer is 401, not 403."""
        response = self.get_detail(self.quiz.pk, anonymous_client())
        self.assertEqual(response.status_code, 401)
