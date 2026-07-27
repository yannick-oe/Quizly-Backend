"""Serializers for the quiz endpoints.

GeneratedQuizSerializer is the gate the Gemini output has to pass
before a single row is written. It is a plain Serializer and not a
ModelSerializer on purpose: what it validates is an answer from a
language model, not a request body, and none of the rules below is a
property of the model.

Every string that survives is stripped, and the stripped value is what
gets stored. The delivered frontend reads an option back off the page
with textContent and compares it against answer with ===. textContent
keeps whitespace, so one leading space would mark every answer to that
question wrong, silently and with no error anywhere.
"""

from rest_framework import serializers

from ..constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ
from ..models import Quiz

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
