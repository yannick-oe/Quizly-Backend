"""Serializers for the quiz endpoints.

Two jobs live here, and they face in opposite directions.

QuizSerializer and QuestionSerializer are the outward shape: the quiz
object as the endpoint documentation prints it, field for field and in
the documented order. The owner is not one of those fields. The model
needs it, the contract has no place for it, so it never leaves the API.
Only title and description are writable; everything else is declared
read-only, which makes DRF drop it from a PATCH instead of answering
400 for a field a client sent back unchanged.

QuizCreateSerializer is the request body of POST /api/quizzes/. It
carries the URL and nothing else, and it hands that URL to the same
helper the pipeline uses, so a link that is not a YouTube video is a
400 before anything is downloaded.

GeneratedQuizSerializer faces the other way. It is the gate the Gemini
output has to pass before a single row is written, and a plain
Serializer rather than a ModelSerializer on purpose: what it validates
is an answer from a language model, not a request body, and none of
the rules below is a property of the model.

Every string that survives is stripped, and the stripped value is what
gets stored. The delivered frontend reads an option back off the page
with textContent and compares it against answer with ===. textContent
keeps whitespace, so one leading space would mark every answer to that
question wrong, silently and with no error anywhere.
"""

from rest_framework import serializers

from ..constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ
from ..models import Question, Quiz
from ..utils import normalize_youtube_url

TITLE_MAX_LENGTH = Quiz._meta.get_field("title").max_length

QUESTION_COUNT_MESSAGE = (
    f"A quiz needs exactly {QUESTIONS_PER_QUIZ} questions."
)

DUPLICATE_OPTIONS_MESSAGE = (
    "The options of a question have to differ from one another."
)

UNKNOWN_ANSWER_MESSAGE = (
    "The answer has to be one of the options of its own question."
)

INVALID_URL_MESSAGE = (
    "This is not a YouTube video URL. Use a link of the form "
    "https://www.youtube.com/watch?v=<id>."
)


class QuestionSerializer(serializers.ModelSerializer):
    """One stored question, in the shape the contract prints.

    Both timestamps are always served. The documentation shows them
    for POST and omits them for the other three answers; the superset
    satisfies the fuller example and costs the frontend nothing,
    because it reads neither. See DEVIATIONS.md.
    """

    class Meta:
        """Name the model and the documented field order."""

        model = Question
        fields = (
            "id",
            "question_title",
            "question_options",
            "answer",
            "created_at",
            "updated_at",
        )


class QuizSerializer(serializers.ModelSerializer):
    """A stored quiz with its questions, in the documented order.

    The questions are read-only here. They are written once, by the
    generation pipeline, and no documented endpoint changes them.
    """

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        """Name the model, the field order and what may be written."""

        model = Quiz
        fields = (
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "video_url",
        )


class QuizCreateSerializer(serializers.Serializer):
    """The request body of POST /api/quizzes/.

    A Serializer and not a ModelSerializer: the body carries a URL,
    not a quiz, and the quiz it leads to does not exist yet.
    """

    url = serializers.CharField()

    def validate_url(self, value):
        """Return the canonical form of an accepted YouTube link.

        The same helper decides here and in the pipeline what counts
        as a YouTube video, so a link the pipeline could not use is
        refused before anything is downloaded.
        """
        video_url = normalize_youtube_url(value)
        if video_url is None:
            raise serializers.ValidationError(INVALID_URL_MESSAGE)
        return video_url


class GeneratedQuestionSerializer(serializers.Serializer):
    """One question of the model output, checked field by field.

    CharField strips its input, so the duplicate check and the answer
    comparison below both run on the stripped values, and those are
    also the values the caller gets back.
    """

    question_title = serializers.CharField()
    question_options = serializers.ListField(
        child=serializers.CharField(),
        min_length=OPTIONS_PER_QUESTION,
        max_length=OPTIONS_PER_QUESTION,
    )
    answer = serializers.CharField()

    def validate_question_options(self, value):
        """Refuse options that repeat one another."""
        if len(set(value)) != len(value):
            raise serializers.ValidationError(DUPLICATE_OPTIONS_MESSAGE)
        return value

    def validate(self, attrs):
        """Refuse an answer that is not one of the options."""
        if attrs["answer"] not in attrs["question_options"]:
            raise serializers.ValidationError(UNKNOWN_ANSWER_MESSAGE)
        return attrs


class GeneratedQuizSerializer(serializers.Serializer):
    """The Gemini output, validated before anything is stored."""

    title = serializers.CharField(max_length=TITLE_MAX_LENGTH)
    description = serializers.CharField()
    questions = GeneratedQuestionSerializer(many=True)

    def validate_questions(self, value):
        """Insist on exactly the number of questions asked for."""
        if len(value) != QUESTIONS_PER_QUIZ:
            raise serializers.ValidationError(QUESTION_COUNT_MESSAGE)
        return value
