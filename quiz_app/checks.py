"""System checks for the quiz_app app."""

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
    """Report a warning when the FFmpeg binary is missing."""
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
    """Report a warning when no Gemini API key is configured."""
    if settings.GEMINI_API_KEY:
        return []
    return [
        CheckWarning(
            API_KEY_MISSING_MESSAGE,
            hint=API_KEY_MISSING_HINT,
            id=API_KEY_MISSING_ID,
        )
    ]
