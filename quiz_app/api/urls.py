"""URL routes for the quiz endpoints."""

from rest_framework.routers import SimpleRouter

from .views import QuizViewSet

router = SimpleRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")

urlpatterns = router.urls
