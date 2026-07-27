"""Exceptions raised by the quiz_app service layer.

Each class marks one failure of the generation pipeline. The service
layer raises them instead of DRF exceptions so that it stays free of
HTTP; translating them into status codes is the job of the API layer.

The split follows the error classes the endpoint documentation names:
an unusable video is the client's problem and becomes a 400, a broken
tool chain is ours and becomes a 500.
"""


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
    """No Gemini API key is configured for this installation.

    Raised where the key is needed rather than at startup. The test
    suite has to run without a key, so the start only warns; see the
    system check in quiz_app/checks.py.
    """


class GeminiRequestError(QuizGenerationError):
    """The Gemini API did not answer with usable text."""


class QuizContentError(QuizGenerationError):
    """Gemini's answer stayed unusable after the repair attempt."""
