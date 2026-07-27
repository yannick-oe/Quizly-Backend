"""Tests for the outward shape of the quiz endpoints.

Two things are pinned here that a status code cannot express.

The first is the field order. The endpoint documentation prints the
quiz object and the question object in a fixed order, and a
ModelSerializer serves whatever order Meta.fields happens to hold. A
reordered Meta would pass every other test in this suite.

The second is the route inventory. Nine endpoints are documented and
there is no PUT. A router on this viewset would add one silently, so
the action maps of the URLconf are compared against the documented set
instead of only asserting that a PUT fails today.

HEAD is part of that expected set. DRF mirrors every GET onto HEAD
while it builds the view, which is what HTTP asks for and not a tenth
endpoint; the same goes for the OPTIONS every DRF view answers. What
would be a tenth endpoint is PUT, and that is what is pinned.
"""

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

DOCUMENTED_ROUTES = {
    "quizzes/": {
        "get": "list",
        "post": "create",
        "head": "list",
    },
    "quizzes/<int:pk>/": {
        "get": "retrieve",
        "patch": "partial_update",
        "delete": "destroy",
        "head": "retrieve",
    },
}


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
    """Cover the method set the URLconf exposes."""

    def test_the_urlconf_maps_exactly_the_documented_methods(self):
        """A tenth route cannot appear without failing here."""
        routes = {
            str(pattern.pattern): pattern.callback.actions
            for pattern in quiz_urls.urlpatterns
        }
        self.assertEqual(routes, DOCUMENTED_ROUTES)

    def test_put_on_the_detail_route_answers_405(self):
        """There is no PUT, and an authenticated one proves it."""
        response = self.client.put(
            quiz_detail_url(self.quiz.pk),
            data={"title": "Replaced"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

    def test_the_viewset_refuses_put_on_a_router_as_well(self):
        """The second guard, for the day somebody adds a router."""
        self.assertNotIn(PUT_METHOD, QuizViewSet.http_method_names)
