"""Tests for the outward shape of the quiz endpoints."""

from quiz_app.api import urls as quiz_urls
from quiz_app.api.views import QuizViewSet

from .helpers import (
    QUESTION_FIELD_ORDER,
    QUIZ_FIELD_ORDER,
    QuizEndpointTestCase,
    quiz_detail_url,
    quiz_list_url,
)

QUESTIONS_KEY = "questions"

PUT_METHOD = "put"

ROUTER_REGISTRY = [("quizzes", QuizViewSet, "quiz")]

ROUTE_NAMES = {"api-root", "quiz-list", "quiz-detail"}


class FieldOrderTests(QuizEndpointTestCase):
    """Cover the documented order of the served fields."""

    def detail_body(self):
        """Return the parsed answer of the detail endpoint."""
        return self.client.get(quiz_detail_url(self.quiz.pk)).json()

    def test_a_quiz_carries_the_documented_fields_in_order(self):
        """The detail answer prints the fields as documented."""
        self.assertEqual(list(self.detail_body()), QUIZ_FIELD_ORDER)

    def test_a_listed_quiz_carries_the_same_order(self):
        """One serializer serves both routes, and it shows."""
        body = self.client.get(quiz_list_url()).json()
        self.assertEqual(list(body[0]), QUIZ_FIELD_ORDER)

    def test_a_question_carries_exactly_six_fields(self):
        """Both timestamps are served, and nothing beyond them."""
        question = self.detail_body()[QUESTIONS_KEY][0]
        self.assertEqual(list(question), QUESTION_FIELD_ORDER)


class RouteInventoryTests(QuizEndpointTestCase):
    """Cover the routes and methods the URLconf exposes."""

    def test_the_router_registers_exactly_the_quiz_viewset(self):
        """The router carries one registration and no second."""
        self.assertEqual(quiz_urls.router.registry, ROUTER_REGISTRY)

    def test_the_urlconf_names_only_the_documented_routes(self):
        """No route beyond the quiz pair and the root appears."""
        names = {pattern.name for pattern in quiz_urls.urlpatterns}
        self.assertEqual(names, ROUTE_NAMES)

    def test_put_on_the_detail_route_answers_405(self):
        """There is no PUT, and an authenticated one proves it."""
        response = self.client.put(
            quiz_detail_url(self.quiz.pk),
            data={"title": "Replaced"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

    def test_the_viewset_leaves_put_out_of_its_methods(self):
        """The viewset does not list PUT as an allowed method."""
        self.assertNotIn(PUT_METHOD, QuizViewSet.http_method_names)
