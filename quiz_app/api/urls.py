"""URL routes for the quiz endpoints.

The viewset is wired through explicit path entries and not through a
router. A router builds its detail route from a ModelViewSet with PUT
included, which would be a tenth endpoint the documentation does not
list and the delivered frontend never calls. Naming the methods here
means the URLconf holds exactly the documented five.
"""

from django.urls import path

from .views import QuizViewSet

LIST_ACTIONS = {
    "get": "list",
    "post": "create",
}

DETAIL_ACTIONS = {
    "get": "retrieve",
    "patch": "partial_update",
    "delete": "destroy",
}

urlpatterns = [
    path(
        "quizzes/",
        QuizViewSet.as_view(LIST_ACTIONS),
        name="quiz-list",
    ),
    path(
        "quizzes/<int:pk>/",
        QuizViewSet.as_view(DETAIL_ACTIONS),
        name="quiz-detail",
    ),
]
