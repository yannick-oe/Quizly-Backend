"""Tests for the system checks of the quiz_app app."""

from unittest import mock

from django.core import checks
from django.test import SimpleTestCase

from quiz_app.checks import FFMPEG_MISSING_ID, check_ffmpeg_available

WHICH_TARGET = "quiz_app.checks.shutil.which"

FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"


class FfmpegCheckTests(SimpleTestCase):
    """Cover both outcomes of the FFmpeg availability check."""

    def test_a_missing_binary_reports_a_warning(self):
        """A missing FFmpeg is reported, and only as a warning."""
        with mock.patch(WHICH_TARGET, return_value=None):
            messages = check_ffmpeg_available(None)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, FFMPEG_MISSING_ID)
        self.assertEqual(messages[0].level, checks.WARNING)
        self.assertIn("install", messages[0].hint.lower())

    def test_a_present_binary_reports_nothing(self):
        """A resolvable FFmpeg produces no message at all."""
        with mock.patch(WHICH_TARGET, return_value=FFMPEG_PATH):
            self.assertEqual(check_ffmpeg_available(None), [])

    def test_the_check_is_registered_with_django(self):
        """The check runs as part of manage.py check."""
        registered = checks.registry.registry.get_checks()
        self.assertIn(check_ffmpeg_available, registered)
