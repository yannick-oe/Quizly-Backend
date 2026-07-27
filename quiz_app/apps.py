"""Application configuration for the quiz_app app."""

from django.apps import AppConfig
from django.core.checks import register

from .checks import check_ffmpeg_available


class QuizAppConfig(AppConfig):
    """Configure the quiz app."""

    name = "quiz_app"

    def ready(self):
        """Register the system checks of this app."""
        register(check_ffmpeg_available)
