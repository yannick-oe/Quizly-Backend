"""Tests for the transcription step of the quiz pipeline.

whisper.load_model is replaced in every test. Nothing here downloads
model weights, and the cache is emptied around each test so that the
model is loaded on demand rather than left over from a neighbour.
"""

from unittest import mock

from django.test import SimpleTestCase, override_settings

from quiz_app.services import transcription
from quiz_app.services.exceptions import (
    InvalidVideoError,
    TranscriptionError,
)

from .helpers import LOAD_MODEL_TARGET, TRANSCRIPTION_LOGGER

AUDIO_PATH = "/tmp/quizly/audio.wav"

SECOND_AUDIO_PATH = "/tmp/quizly/second.wav"

TRANSCRIPT = "The Roman Republic ended in a series of civil wars."

PADDED_TRANSCRIPT = f"  {TRANSCRIPT}\n"


def fake_model(**overrides):
    """Return a Whisper stand-in that answers with a transcript."""
    model = mock.MagicMock()
    model.transcribe.return_value = {"text": PADDED_TRANSCRIPT}
    model.configure_mock(**overrides)
    return model


class TranscriptionTestCase(SimpleTestCase):
    """Start and end every test with an empty model cache."""

    def setUp(self):
        """Empty the module level model cache."""
        transcription._MODEL_CACHE.clear()
        self.addCleanup(transcription._MODEL_CACHE.clear)


class LoadTranscriptionModelTests(TranscriptionTestCase):
    """Cover the cached loader that the pipeline goes through."""

    def test_the_configured_model_name_is_used(self):
        """The loader asks Whisper for the configured model."""
        with mock.patch(LOAD_MODEL_TARGET) as load_model:
            with override_settings(WHISPER_MODEL="tiny"):
                transcription.load_transcription_model()
        load_model.assert_called_once_with("tiny")

    def test_the_model_is_loaded_once_for_two_transcriptions(self):
        """Two transcriptions share a single loaded model."""
        model = fake_model()
        with mock.patch(LOAD_MODEL_TARGET, return_value=model) as load_model:
            first = transcription.transcribe_audio(AUDIO_PATH)
            second = transcription.transcribe_audio(SECOND_AUDIO_PATH)
        self.assertEqual(load_model.call_count, 1)
        self.assertEqual(model.transcribe.call_count, 2)
        self.assertEqual(first, TRANSCRIPT)
        self.assertEqual(second, TRANSCRIPT)

    def test_a_changed_model_name_loads_again(self):
        """The cache is keyed by name, not shared across sizes."""
        with mock.patch(LOAD_MODEL_TARGET) as load_model:
            with override_settings(WHISPER_MODEL="tiny"):
                transcription.load_transcription_model()
            with override_settings(WHISPER_MODEL="small"):
                transcription.load_transcription_model()
        self.assertEqual(load_model.call_count, 2)


class TranscribeAudioTests(TranscriptionTestCase):
    """Cover the transcription itself and its failure modes."""

    def test_the_transcript_is_stripped(self):
        """Surrounding whitespace never reaches the caller."""
        with mock.patch(LOAD_MODEL_TARGET, return_value=fake_model()):
            result = transcription.transcribe_audio(AUDIO_PATH)
        self.assertEqual(result, TRANSCRIPT)

    def test_the_path_is_handed_over_as_a_string(self):
        """Whisper receives a string, not a Path object."""
        model = fake_model()
        with mock.patch(LOAD_MODEL_TARGET, return_value=model):
            transcription.transcribe_audio(AUDIO_PATH)
        model.transcribe.assert_called_once_with(AUDIO_PATH)

    def test_a_library_failure_becomes_our_exception(self):
        """A crash inside Whisper leaves as a TranscriptionError."""
        model = fake_model()
        model.transcribe.side_effect = RuntimeError("out of memory")
        with (
            mock.patch(LOAD_MODEL_TARGET, return_value=model),
            self.assertLogs(TRANSCRIPTION_LOGGER, level="ERROR"),
            self.assertRaises(TranscriptionError),
        ):
            transcription.transcribe_audio(AUDIO_PATH)

    def test_an_empty_transcript_blames_the_video(self):
        """A silent video is the input's fault, not the tool chain's."""
        model = fake_model()
        model.transcribe.return_value = {"text": "   \n"}
        with mock.patch(LOAD_MODEL_TARGET, return_value=model):
            with self.assertRaises(InvalidVideoError):
                transcription.transcribe_audio(AUDIO_PATH)

    def test_an_empty_transcript_is_no_transcription_failure(self):
        """The silent case stays out of the 500 error class."""
        model = fake_model()
        model.transcribe.return_value = {"text": ""}
        with mock.patch(LOAD_MODEL_TARGET, return_value=model):
            with self.assertRaises(InvalidVideoError):
                transcription.transcribe_audio(AUDIO_PATH)
        self.assertFalse(issubclass(InvalidVideoError, TranscriptionError))

    def test_a_result_without_text_is_rejected(self):
        """A result that carries no text key is refused."""
        model = fake_model()
        model.transcribe.return_value = None
        with mock.patch(LOAD_MODEL_TARGET, return_value=model):
            with self.assertRaises(InvalidVideoError):
                transcription.transcribe_audio(AUDIO_PATH)
