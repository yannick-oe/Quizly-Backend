"""Views for the quiz endpoints."""

import logging

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Quiz
from ..services.exceptions import (
    AudioConversionError,
    GeminiRequestError,
    InvalidVideoError,
    MissingApiKeyError,
    QuizContentError,
    QuizGenerationError,
    TranscriptionError,
    VideoTooLongError,
)
from ..services.generation import generate_quiz
from .permissions import IsQuizOwner
from .serializers import QuizCreateSerializer, QuizSerializer

LOGGER = logging.getLogger(__name__)

ALLOWED_METHODS = ("get", "post", "patch", "delete", "head", "options")

LIST_ACTION = "list"

CREATE_ACTION = "create"

QUESTIONS_RELATION = "questions"

URL_FIELD = "url"

DETAIL_KEY = "detail"

FAILURE_STATUS_CODES = {
    InvalidVideoError: status.HTTP_400_BAD_REQUEST,
    VideoTooLongError: status.HTTP_400_BAD_REQUEST,
    AudioConversionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    TranscriptionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    MissingApiKeyError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    GeminiRequestError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    QuizContentError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

SERVER_FAILURE_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR

GENERATION_FAILED_MESSAGE = (
    "The quiz could not be generated. Please try again later."
)

FAILURE_LOG_TEMPLATE = "Quiz generation failed for %s: %s"


def _detail_response(message, code):
    """Return a one-field JSON body with a status code."""
    return Response({DETAIL_KEY: message}, status=code)


def _failure_response(error, video_url):
    """Log a failed generation and answer it with its status."""
    code = FAILURE_STATUS_CODES.get(type(error), SERVER_FAILURE_CODE)
    if code == SERVER_FAILURE_CODE:
        LOGGER.error(FAILURE_LOG_TEMPLATE, video_url, error)
        return _detail_response(GENERATION_FAILED_MESSAGE, code)
    LOGGER.warning(FAILURE_LOG_TEMPLATE, video_url, error)
    return _detail_response(str(error), code)


class QuizViewSet(viewsets.ModelViewSet):
    """Serve the five documented quiz endpoints."""

    queryset = Quiz.objects.prefetch_related(QUESTIONS_RELATION)
    permission_classes = [IsAuthenticated & IsQuizOwner]
    http_method_names = ALLOWED_METHODS

    def get_queryset(self):
        """Return the quizzes the running action may reach."""
        queryset = self.queryset.all()
        if self.action == LIST_ACTION:
            return queryset.filter(owner=self.request.user)
        return queryset

    def get_serializer_class(self):
        """Return the serializer class of the running action."""
        if self.action == CREATE_ACTION:
            return QuizCreateSerializer
        return QuizSerializer

    def create(self, request, *args, **kwargs):
        """Generate a quiz from a URL and answer with the quiz."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video_url = serializer.validated_data[URL_FIELD]
        try:
            quiz = generate_quiz(request.user, video_url)
        except QuizGenerationError as error:
            return _failure_response(error, video_url)
        return Response(
            QuizSerializer(quiz).data,
            status=status.HTTP_201_CREATED,
        )
