"""Tests for the system checks of the quiz_app app.

Both checks report a warning rather than an error, and both tests
below insist on that level. An error would abort manage.py test on a
machine without FFmpeg or without an API key, which is exactly the
machine the suite has to run on.
"""

from unittest import mock

from django.core import checks
from django.test import SimpleTestCase, override_settings

from quiz_app.checks import (
    API_KEY_MISSING_ID,
    FFMPEG_MISSING_ID,
    check_ffmpeg_available,
    check_gemini_api_key,
)

WHICH_TARGET = "quiz_app.checks.shutil.which"

FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"

API_KEY = "test-key-not-a-real-one"


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


class GeminiApiKeyCheckTests(SimpleTestCase):
    """Cover both outcomes of the Gemini API key check."""

    @override_settings(GEMINI_API_KEY="")
    def test_an_empty_key_reports_a_warning(self):
        """An unconfigured key is reported, and only as a warning."""
        messages = check_gemini_api_key(None)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, API_KEY_MISSING_ID)
        self.assertEqual(messages[0].level, checks.WARNING)
        self.assertIn("GEMINI_API_KEY", messages[0].msg)

    @override_settings(GEMINI_API_KEY=API_KEY)
    def test_a_configured_key_reports_nothing(self):
        """A filled in key produces no message at all."""
        self.assertEqual(check_gemini_api_key(None), [])

    @override_settings(GEMINI_API_KEY="")
    def test_the_hint_says_where_to_put_the_key(self):
        """The hint names the file the key belongs in."""
        self.assertIn(".env", check_gemini_api_key(None)[0].hint)

    def test_the_check_is_registered_with_django(self):
        """The check runs as part of manage.py check."""
        registered = checks.registry.registry.get_checks()
        self.assertIn(check_gemini_api_key, registered)
