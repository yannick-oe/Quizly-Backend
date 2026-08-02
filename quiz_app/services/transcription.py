"""Speech to text for the quiz pipeline."""

import functools
import logging

import whisper
from django.conf import settings

from .exceptions import InvalidVideoError, TranscriptionError

LOGGER = logging.getLogger(__name__)

TRANSCRIPT_KEY = "text"

TRANSCRIPTION_FAILED_MESSAGE = (
    "The audio track of the video could not be transcribed."
)

EMPTY_TRANSCRIPT_MESSAGE = (
    "No speech was found in the video. Pick a video that is spoken, "
    "not one that is silent or music only."
)


@functools.cache
def _load_model(name):
    """Load one Whisper model by name."""
    return whisper.load_model(name)


def load_transcription_model():
    """Return the configured Whisper model, loaded once per process."""
    return _load_model(settings.WHISPER_MODEL)


def transcribe_audio(audio_path):
    """Return the spoken text of an audio file."""
    model = load_transcription_model()
    try:
        result = model.transcribe(str(audio_path))
    except Exception as error:
        LOGGER.error("Whisper transcription failed: %s", error)
        raise TranscriptionError(TRANSCRIPTION_FAILED_MESSAGE) from error
    return _transcript_text(result)


def _transcript_text(result):
    """Return the stripped transcript a Whisper result carries."""
    text = (result or {}).get(TRANSCRIPT_KEY) or ""
    stripped = text.strip()
    if not stripped:
        raise InvalidVideoError(EMPTY_TRANSCRIPT_MESSAGE)
    return stripped
