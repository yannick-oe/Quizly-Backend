"""Exceptions raised by the quiz_app service layer."""


class QuizGenerationError(Exception):
    """Base class for every failure of the generation pipeline."""


class InvalidVideoError(QuizGenerationError):
    """The URL does not lead to a video that can be processed."""


class VideoTooLongError(QuizGenerationError):
    """The video is longer than the configured maximum."""


class AudioConversionError(QuizGenerationError):
    """FFmpeg did not produce a usable audio track."""


class TranscriptionError(QuizGenerationError):
    """Whisper did not produce a usable transcript."""


class MissingApiKeyError(QuizGenerationError):
    """No Gemini API key is configured for this installation."""


class GeminiRequestError(QuizGenerationError):
    """The Gemini API did not answer with usable text."""


class QuizContentError(QuizGenerationError):
    """Gemini's answer stayed unusable after the repair attempt."""
