"""System checks for the quiz_app app.

Quiz generation converts the downloaded audio with FFmpeg. A missing
binary would only surface as a failed request much later, so the
project reports it when it starts.
"""

import shutil

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
