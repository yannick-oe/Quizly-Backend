"""Serializers for the quiz endpoints."""

from rest_framework import serializers

from ..constants import (
    INVALID_URL_MESSAGE,
    OPTIONS_PER_QUESTION,
    QUESTIONS_PER_QUIZ,
)
from ..models import Question, Quiz
from ..utils import normalize_youtube_url

TITLE_MAX_LENGTH = Quiz._meta.get_field("title").max_length

DUPLICATE_OPTIONS_MESSAGE = (
    "The options of a question have to differ from one another."
)

UNKNOWN_ANSWER_MESSAGE = (
    "The answer has to be one of the options of its own question."
)


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for one stored question."""

    class Meta:
        """Name the model and the field order."""

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
    """Serializer for a stored quiz and its questions."""

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
    """The request body of POST /api/quizzes/."""

    url = serializers.CharField()

    def validate_url(self, value):
        """Return the canonical form of an accepted YouTube link."""
        video_url = normalize_youtube_url(value)
        if video_url is None:
            raise serializers.ValidationError(INVALID_URL_MESSAGE)
        return video_url


class GeneratedQuestionSerializer(serializers.Serializer):
    """One question of the model output, checked field by field."""

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
    questions = GeneratedQuestionSerializer(
        many=True,
        min_length=QUESTIONS_PER_QUIZ,
        max_length=QUESTIONS_PER_QUIZ,
    )
