"""URL routes for the quiz endpoints."""

from rest_framework.routers import DefaultRouter

from .views import QuizViewSet

router = DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")

urlpatterns = router.urls
