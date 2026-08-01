"""Tests for the outward shape of the quiz endpoints."""

from django.urls import get_resolver, resolve

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

API_PREFIX = "api/"

API_ROUTE_NAMES = [
    "login",
    "logout",
    "quiz-detail",
    "quiz-list",
    "register",
    "token_refresh",
]

COLLECTION_ACTIONS = {"get": "list", "post": "create"}

DETAIL_ACTIONS = {
    "get": "retrieve",
    "patch": "partial_update",
    "delete": "destroy",
}


def api_route_names():
    """Return the names of every route under the api/ prefix."""
    names = []
    for resolver in get_resolver().url_patterns:
        if str(resolver.pattern) == API_PREFIX:
            names.extend(pattern.name for pattern in resolver.url_patterns)
    return names


class FieldOrderTests(QuizEndpointTestCase):
    """Cover the order of the served fields."""

    def detail_body(self):
        """Return the parsed answer of the detail endpoint."""
        return self.client.get(quiz_detail_url(self.quiz.pk)).json()

    def test_a_quiz_carries_the_documented_fields_in_order(self):
        """The detail answer prints the fields in the fixed order."""
        self.assertEqual(list(self.detail_body()), QUIZ_FIELD_ORDER)

    def test_a_listed_quiz_carries_the_same_order(self):
        """The list answer prints the same field order."""
        body = self.client.get(quiz_list_url()).json()
        self.assertEqual(list(body[0]), QUIZ_FIELD_ORDER)

    def test_a_question_carries_exactly_six_fields(self):
        """Both timestamps are served, and nothing beyond them."""
        question = self.detail_body()[QUESTIONS_KEY][0]
        self.assertEqual(list(question), QUESTION_FIELD_ORDER)


class RouteInventoryTests(QuizEndpointTestCase):
    """Cover the routes and methods the URLconf exposes."""

    def assert_resolves_to_actions(self, url, expected):
        """Assert a URL reaches the viewset with the given actions."""
        match = resolve(url)
        self.assertIs(match.func.cls, QuizViewSet)
        for method, action in expected.items():
            with self.subTest(method=method):
                self.assertEqual(match.func.actions[method], action)

    def test_the_collection_route_resolves_to_the_viewset(self):
        """GET and POST on the collection reach list and create."""
        self.assert_resolves_to_actions(quiz_list_url(), COLLECTION_ACTIONS)

    def test_the_detail_route_resolves_to_the_viewset(self):
        """GET, PATCH and DELETE reach the detail actions."""
        self.assert_resolves_to_actions(
            quiz_detail_url(self.quiz.pk), DETAIL_ACTIONS
        )

    def test_the_urlconf_names_only_the_documented_routes(self):
        """The api/ prefix serves six routes and no seventh."""
        self.assertEqual(sorted(api_route_names()), API_ROUTE_NAMES)

    def test_put_on_the_detail_route_answers_405(self):
        """An authenticated PUT answers with 405."""
        response = self.client.put(
            quiz_detail_url(self.quiz.pk),
            data={"title": "Replaced"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

    def test_the_viewset_leaves_put_out_of_its_methods(self):
        """The viewset does not list PUT as an allowed method."""
        self.assertNotIn(PUT_METHOD, QuizViewSet.http_method_names)
