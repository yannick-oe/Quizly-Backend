"""Database models for the quiz_app app."""

from django.conf import settings
from django.db import models
from django.utils.text import Truncator

QUESTION_TITLE_PREVIEW_LENGTH = 60


class Quiz(models.Model):
    """A quiz generated from a single video, owned by one user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    video_url = models.URLField(max_length=500)

    class Meta:
        """Order quizzes newest first and fix the plural spelling."""

        ordering = ["-created_at"]
        verbose_name = "quiz"
        verbose_name_plural = "quizzes"

    def __str__(self):
        """Return the quiz title."""
        return self.title


class Question(models.Model):
    """One multiple-choice question belonging to a quiz."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_title = models.TextField()
    question_options = models.JSONField(default=list)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Keep the question order stable and reproducible."""

        ordering = ["id"]

    def __str__(self):
        """Return a shortened form of the question title."""
        return Truncator(self.question_title).chars(
            QUESTION_TITLE_PREVIEW_LENGTH
        )
