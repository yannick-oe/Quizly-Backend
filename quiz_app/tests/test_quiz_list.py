"""Tests for GET /api/quizzes/.

Two things are checked here that no status code would catch. The
answer is a bare JSON array and not an object with a results key, so
the type is asserted rather than only its content. And the list holds
the quizzes of the requesting user only, which is the one place where
the queryset is narrowed to the owner.
"""

from quiz_app.constants import QUESTIONS_PER_QUIZ

from .helpers import (
    FOREIGN_TITLE,
    QUIZ_TITLE,
    QuizEndpointTestCase,
    anonymous_client,
    create_quiz,
    create_user,
    authenticate,
    quiz_list_url,
)

SECOND_TITLE = "A second quiz of the same user"

THIRD_USERNAME = "newcomer"

QUESTIONS_KEY = "questions"

TITLE_KEY = "title"


class QuizListTests(QuizEndpointTestCase):
    """Cover the collection endpoint of the current user."""

    def get_list(self, client=None):
        """Return the parsed body of the quiz collection."""
        return (client or self.client).get(quiz_list_url())

    def test_the_list_is_answered_with_200(self):
        """The documented success code of the collection."""
        self.assertEqual(self.get_list().status_code, 200)

    def test_the_answer_is_a_bare_array(self):
        """No pagination envelope, no results key, just a list."""
        self.assertIsInstance(self.get_list().json(), list)

    def test_only_the_own_quizzes_are_listed(self):
        """A quiz of another user never appears in this list."""
        titles = [quiz[TITLE_KEY] for quiz in self.get_list().json()]
        self.assertEqual(titles, [QUIZ_TITLE])
        self.assertNotIn(FOREIGN_TITLE, titles)

    def test_a_listed_quiz_carries_its_questions(self):
        """The documentation shows the list with questions in it."""
        first = self.get_list().json()[0]
        self.assertEqual(len(first[QUESTIONS_KEY]), QUESTIONS_PER_QUIZ)

    def test_the_newest_quiz_comes_first(self):
        """The model orders newest first, and the list keeps that."""
        create_quiz(self.user, title=SECOND_TITLE)
        titles = [quiz[TITLE_KEY] for quiz in self.get_list().json()]
        self.assertEqual(titles, [SECOND_TITLE, QUIZ_TITLE])

    def test_a_user_without_quizzes_gets_an_empty_array(self):
        """An empty list is still a list, and still a 200."""
        client = anonymous_client()
        authenticate(client, create_user(THIRD_USERNAME))
        response = self.get_list(client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_an_unauthenticated_request_answers_401(self):
        """Without the access cookie there is no list to show."""
        self.assertEqual(self.get_list(anonymous_client()).status_code, 401)
