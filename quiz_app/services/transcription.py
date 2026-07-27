"""Speech to text for the quiz pipeline.

Loading a Whisper model costs seconds and megabytes, so the model is
kept in memory after its first use. Its size follows the WHISPER_MODEL
setting, and the cache is keyed by name so that a changed setting
loads the model it names instead of returning the old one.

load_transcription_model is also the seam the tests replace, which is
what keeps the suite from downloading model weights.
"""

import logging

import whisper
from django.conf import settings

from .exceptions import TranscriptionError

LOGGER = logging.getLogger(__name__)

TRANSCRIPT_KEY = "text"

TRANSCRIPTION_FAILED_MESSAGE = (
    "The audio track of the video could not be transcribed."
)

EMPTY_TRANSCRIPT_MESSAGE = (
    "The video carries no speech that could be transcribed."
)

_MODEL_CACHE = {}


def load_transcription_model():
    """Return the configured Whisper model, loaded once per process."""
    name = settings.WHISPER_MODEL
    if name not in _MODEL_CACHE:
        _MODEL_CACHE[name] = whisper.load_model(name)
    return _MODEL_CACHE[name]


def transcribe_audio(audio_path):
    """Return the spoken text of an audio file.

    Whisper and torch fail in many ways, from a missing binary to a
    failed allocation, and none of them is worth telling apart here.
    Every one of them becomes a failure of this single step.
    """
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
        raise TranscriptionError(EMPTY_TRANSCRIPT_MESSAGE)
    return stripped
