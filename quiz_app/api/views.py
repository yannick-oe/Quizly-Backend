"""Views for the quiz endpoints.

One viewset serves all five routes. urls.py wires it through explicit
path entries instead of a router, so the method set is exactly the
documented one and no PUT appears behind our back.

get_queryset() filters on the owner for the list action only. The
detail actions work on the full queryset and the ownership check runs
as an object permission, because DRF looks the object up before it
checks object permissions: a filtered detail queryset would answer 404
where the documentation asks for 403. See DEVIATIONS.md.

POST runs the whole pipeline inside the request. Its failures arrive
as the service layer's own exceptions and are translated here through
one mapping rather than a chain of checks: what the client sent is a
400, what broke on our side is a 500. Both are logged with their real
cause first. The delivered frontend shows nothing but "Error
generating quiz", so the log is the only diagnosis there is, and a 500
answers with a fixed sentence rather than an internal message.
"""

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
    """Return a one-field JSON body with a status code.

    Never an empty body: the delivered frontend parses every answer
    except the one of DELETE as JSON, whatever its status.
    """
    return Response({DETAIL_KEY: message}, status=code)


def _failure_response(error, video_url):
    """Log a failed generation and answer it with its status.

    A 500 answers with a fixed sentence. The message of the exception
    can name a missing API key or a broken tool chain, and neither is
    the client's business.
    """
    code = FAILURE_STATUS_CODES.get(type(error), SERVER_FAILURE_CODE)
    if code == SERVER_FAILURE_CODE:
        LOGGER.error(FAILURE_LOG_TEMPLATE, video_url, error)
        return _detail_response(GENERATION_FAILED_MESSAGE, code)
    LOGGER.warning(FAILURE_LOG_TEMPLATE, video_url, error)
    return _detail_response(str(error), code)


class QuizViewSet(viewsets.ModelViewSet):
    """The five documented quiz endpoints, and no sixth.

    queryset declares the base every action starts from and carries
    the prefetch; get_queryset() is what narrows it, so the two
    cannot drift apart. http_method_names leaves out PUT a second
    time. urls.py already maps only the documented methods, so this
    is the guard that holds if somebody ever puts this viewset on a
    router.
    """

    queryset = Quiz.objects.prefetch_related(QUESTIONS_RELATION)
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated & IsQuizOwner]
    http_method_names = ALLOWED_METHODS

    def get_queryset(self):
        """Return the quizzes the running action may reach.

        Only the list is narrowed to the owner. The detail actions
        stay on the full queryset so that a foreign quiz can answer
        403 instead of 404; the object permission decides there.

        The declared queryset is re-evaluated rather than reused, as
        DRF does it: a class attribute is built once per process.
        """
        queryset = self.queryset.all()
        if self.action == LIST_ACTION:
            return queryset.filter(owner=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        """Generate a quiz from a URL and answer with the quiz."""
        video_url = self._accepted_url(request)
        try:
            quiz = generate_quiz(request.user, video_url)
        except QuizGenerationError as error:
            return _failure_response(error, video_url)
        return Response(
            self.get_serializer(quiz).data,
            status=status.HTTP_201_CREATED,
        )

    def _accepted_url(self, request):
        """Return the canonical URL the request body carries."""
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data[URL_FIELD]
