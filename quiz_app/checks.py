"""System checks for the quiz_app app.

Quiz generation needs FFmpeg on PATH and a Gemini API key. Neither
would surface before the first request without these checks, and both
are reported when the project starts.

Both are warnings, not errors, and both are on purpose. The coding
standards ask for a hard failure on missing configuration, but the
project rules also require the test suite to run without an API key
and on a machine without FFmpeg. An error would abort manage.py test
on exactly that machine. The strictness is moved to the point of use
instead: a named exception when the missing piece is actually needed.
"""

import shutil

from django.conf import settings
from django.core.checks import Warning as CheckWarning

FFMPEG_BINARY = "ffmpeg"

FFMPEG_MISSING_ID = "quiz_app.W001"

FFMPEG_MISSING_MESSAGE = (
    "FFmpeg was not found on PATH. Quiz generation will fail at the "
    "audio conversion step."
)

FFMPEG_MISSING_HINT = (
    "Install it and keep it on PATH: brew install ffmpeg on macOS, "
    "sudo apt install ffmpeg on Debian and Ubuntu, "
    "winget install Gyan.FFmpeg on Windows."
)


API_KEY_MISSING_ID = "quiz_app.W002"

API_KEY_MISSING_MESSAGE = (
    "GEMINI_API_KEY is empty or unset. Quiz generation will fail at "
    "the question generation step."
)

API_KEY_MISSING_HINT = (
    "Create a key at https://aistudio.google.com/apikey and put it "
    "into .env as GEMINI_API_KEY. See .env.example."
)


def check_ffmpeg_available(app_configs, **kwargs):
    """Report a warning when the FFmpeg binary is missing.

    A warning and not an error on purpose. An error would abort
    manage.py test on a machine without FFmpeg, and the test suite
    mocks every call to it anyway.
    """
    if shutil.which(FFMPEG_BINARY) is not None:
        return []
    return [
        CheckWarning(
            FFMPEG_MISSING_MESSAGE,
            hint=FFMPEG_MISSING_HINT,
            id=FFMPEG_MISSING_ID,
        )
    ]


def check_gemini_api_key(app_configs, **kwargs):
    """Report a warning when no Gemini API key is configured.

    A warning for the same reason as the one above: the suite mocks
    every Gemini call and must run without a key. The hard stop sits
    in quiz_app/services/gemini.py, where the key is needed.
    """
    if settings.GEMINI_API_KEY:
        return []
    return [
        CheckWarning(
            API_KEY_MISSING_MESSAGE,
            hint=API_KEY_MISSING_HINT,
            id=API_KEY_MISSING_ID,
        )
    ]
