"""Tests for the download and conversion steps of the audio service."""

import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase
from yt_dlp.utils import DownloadError

from quiz_app.services import youtube
from quiz_app.services.exceptions import (
    AudioConversionError,
    InvalidVideoError,
)

from .helpers import (
    DOWNLOAD_AUDIO_TARGET,
    SOURCE_FILE_NAME,
    SUBPROCESS_RUN_TARGET,
    VIDEO_URL,
    WAV_BYTES,
    YOUTUBE_DL_TARGET,
    YOUTUBE_LOGGER,
    DirectoryRecorder,
    downloader_of,
    video_metadata,
    write_source_file,
    write_wav_file,
)


class WorkingDirectoryTestCase(SimpleTestCase):
    """Give every test a temporary directory of its own."""

    def setUp(self):
        """Create the directory the service may write into."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work_dir = directory.name


class DownloadAudioTests(WorkingDirectoryTestCase):
    """Cover the download step and its failure modes."""

    def test_the_downloaded_file_is_returned(self):
        """The path yt_dlp left in the directory is handed back."""
        write_source_file(VIDEO_URL, self.work_dir)
        with mock.patch(YOUTUBE_DL_TARGET) as youtube_dl:
            path = youtube.download_audio(VIDEO_URL, self.work_dir)
            downloader = downloader_of(youtube_dl)
        self.assertEqual(path, Path(self.work_dir) / SOURCE_FILE_NAME)
        downloader.download.assert_called_once_with([VIDEO_URL])

    def test_the_options_write_into_the_given_directory(self):
        """The output template stays inside the temporary directory."""
        options = youtube.build_download_options(self.work_dir)
        self.assertTrue(options["outtmpl"].startswith(self.work_dir))
        self.assertEqual(options["format"], youtube.AUDIO_FORMAT)
        self.assertNotIn("skip_download", options)

    def test_a_yt_dlp_error_becomes_an_invalid_video(self):
        """A failed download leaves as our own exception."""
        failure = DownloadError("Requested format is not available")
        with mock.patch(YOUTUBE_DL_TARGET) as youtube_dl:
            downloader_of(youtube_dl).download.side_effect = failure
            with (
                self.assertLogs(YOUTUBE_LOGGER, level="INFO") as logs,
                self.assertRaises(InvalidVideoError),
            ):
                youtube.download_audio(VIDEO_URL, self.work_dir)
        record = logs.records[0]
        self.assertEqual(record.levelname, "INFO")
        self.assertEqual(record.name, YOUTUBE_LOGGER)
        self.assertIn(VIDEO_URL, record.getMessage())

    def test_a_download_without_a_file_is_rejected(self):
        """A silent download that wrote nothing is refused."""
        with mock.patch(YOUTUBE_DL_TARGET):
            with self.assertRaises(InvalidVideoError):
                youtube.download_audio(VIDEO_URL, self.work_dir)


class ConvertToWavTests(WorkingDirectoryTestCase):
    """Cover the FFmpeg call and the rules it has to follow."""

    def test_ffmpeg_is_called_as_a_list_with_a_timeout(self):
        """The call carries a list, a timeout, and no shell."""
        with mock.patch(SUBPROCESS_RUN_TARGET) as run:
            youtube.convert_to_wav(SOURCE_FILE_NAME, self.work_dir)
        command = run.call_args.args[0]
        keywords = run.call_args.kwargs
        self.assertIsInstance(command, list)
        self.assertEqual(command[0], youtube.FFMPEG_BINARY)
        self.assertEqual(keywords["timeout"], youtube.FFMPEG_TIMEOUT_SECONDS)
        self.assertTrue(keywords["check"])
        self.assertIs(keywords.get("shell", False), False)

    def test_every_argument_of_the_call_is_a_string(self):
        """No Path object is handed to the subprocess."""
        command = youtube.build_ffmpeg_command(
            Path("/audio/source.m4a"), Path("/audio/audio.wav")
        )
        self.assertTrue(all(isinstance(part, str) for part in command))
        self.assertEqual(command[-1], "/audio/audio.wav")

    def test_the_written_wav_path_is_returned(self):
        """The conversion answers with the file it wrote."""
        with mock.patch(SUBPROCESS_RUN_TARGET, side_effect=write_wav_file):
            path = youtube.convert_to_wav(SOURCE_FILE_NAME, self.work_dir)
        self.assertEqual(path.name, youtube.WAV_FILE_NAME)
        self.assertEqual(path.read_bytes(), WAV_BYTES)

    def test_a_failing_ffmpeg_becomes_our_exception(self):
        """A non-zero exit is reported as a conversion failure."""
        failure = subprocess.CalledProcessError(1, [youtube.FFMPEG_BINARY])
        with (
            mock.patch(SUBPROCESS_RUN_TARGET, side_effect=failure),
            self.assertLogs(YOUTUBE_LOGGER, level="ERROR"),
            self.assertRaises(AudioConversionError),
        ):
            youtube.convert_to_wav(SOURCE_FILE_NAME, self.work_dir)

    def test_a_missing_ffmpeg_becomes_our_exception(self):
        """A binary that is not on PATH is reported the same way."""
        with (
            mock.patch(SUBPROCESS_RUN_TARGET, side_effect=OSError),
            self.assertLogs(YOUTUBE_LOGGER, level="ERROR"),
            self.assertRaises(AudioConversionError),
        ):
            youtube.convert_to_wav(SOURCE_FILE_NAME, self.work_dir)

    def test_a_timeout_becomes_our_exception(self):
        """A conversion that runs too long is reported the same way."""
        failure = subprocess.TimeoutExpired([youtube.FFMPEG_BINARY], 1)
        with (
            mock.patch(SUBPROCESS_RUN_TARGET, side_effect=failure),
            self.assertLogs(YOUTUBE_LOGGER, level="ERROR"),
            self.assertRaises(AudioConversionError),
        ):
            youtube.convert_to_wav(SOURCE_FILE_NAME, self.work_dir)


class PreparedAudioTests(SimpleTestCase):
    """Cover the whole audio chain on the successful path."""

    def setUp(self):
        """Replace yt_dlp, the download step and FFmpeg."""
        youtube_dl = self.enterContext(mock.patch(YOUTUBE_DL_TARGET))
        extract_info = downloader_of(youtube_dl).extract_info
        extract_info.return_value = video_metadata()
        self.enterContext(
            mock.patch(DOWNLOAD_AUDIO_TARGET, side_effect=write_source_file)
        )
        self.enterContext(
            mock.patch(SUBPROCESS_RUN_TARGET, side_effect=write_wav_file)
        )

    def test_the_wav_is_readable_inside_the_block(self):
        """The yielded path points at the converted WAV file."""
        with youtube.prepared_audio(VIDEO_URL) as wav_path:
            self.assertEqual(wav_path.name, youtube.WAV_FILE_NAME)
            self.assertEqual(wav_path.read_bytes(), WAV_BYTES)

    def test_the_directory_is_gone_after_the_block(self):
        """Leaving the block removes the temporary directory."""
        with youtube.prepared_audio(VIDEO_URL) as wav_path:
            directory = wav_path.parent
        self.assertFalse(directory.exists())


class PreparedAudioCleanupTests(SimpleTestCase):
    """Prove the temporary directory survives no failure."""

    def setUp(self):
        """Let the metadata pass, record the directory, fail FFmpeg."""
        youtube_dl = self.enterContext(mock.patch(YOUTUBE_DL_TARGET))
        extract_info = downloader_of(youtube_dl).extract_info
        extract_info.return_value = video_metadata()
        self.recorder = DirectoryRecorder()
        self.enterContext(
            mock.patch(DOWNLOAD_AUDIO_TARGET, side_effect=self.recorder)
        )
        self.enterContext(
            mock.patch(SUBPROCESS_RUN_TARGET, side_effect=OSError)
        )

    def test_a_failed_conversion_still_removes_the_directory(self):
        """A failing conversion leaves no directory behind."""
        with (
            self.assertLogs(YOUTUBE_LOGGER, level="ERROR"),
            self.assertRaises(AudioConversionError),
            youtube.prepared_audio(VIDEO_URL),
        ):
            pass
        self.assertEqual(len(self.recorder.directories), 1)
        self.assertFalse(self.recorder.directories[0].exists())
