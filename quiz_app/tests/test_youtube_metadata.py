"""Tests for the metadata step of the YouTube audio service.

The duration guard is the reason this step exists at all, so the tests
below not only check that an unusable video raises, but also that no
download was started when it does.
"""

from unittest import mock

from django.test import SimpleTestCase
from yt_dlp.utils import DownloadError

from quiz_app.constants import MAX_VIDEO_DURATION_SECONDS
from quiz_app.services import youtube
from quiz_app.services.exceptions import InvalidVideoError, VideoTooLongError

from .helpers import (
    DOWNLOAD_AUDIO_TARGET,
    VIDEO_URL,
    YOUTUBE_DL_TARGET,
    downloader_of,
    video_metadata,
)


class FetchVideoMetadataTests(SimpleTestCase):
    """Cover the lookup that runs before anything is fetched."""

    def test_the_lookup_asks_for_information_only(self):
        """The metadata call passes download=False to yt_dlp."""
        expected = video_metadata()
        with mock.patch(YOUTUBE_DL_TARGET) as youtube_dl:
            downloader = downloader_of(youtube_dl)
            downloader.extract_info.return_value = expected
            result = youtube.fetch_video_metadata(VIDEO_URL)
        self.assertEqual(result, expected)
        downloader.extract_info.assert_called_once_with(
            VIDEO_URL, download=False
        )

    def test_the_options_switch_the_download_off(self):
        """The options of the lookup carry skip_download."""
        self.assertTrue(youtube.METADATA_OPTIONS["skip_download"])

    def test_a_yt_dlp_error_becomes_an_invalid_video(self):
        """A yt_dlp exception never escapes the service layer."""
        failure = DownloadError("Video unavailable")
        with mock.patch(YOUTUBE_DL_TARGET) as youtube_dl:
            downloader_of(youtube_dl).extract_info.side_effect = failure
            with self.assertRaises(InvalidVideoError):
                youtube.fetch_video_metadata(VIDEO_URL)

    def test_metadata_without_content_is_rejected(self):
        """An empty answer from yt_dlp is refused, not passed on."""
        with mock.patch(YOUTUBE_DL_TARGET) as youtube_dl:
            downloader_of(youtube_dl).extract_info.return_value = None
            with self.assertRaises(InvalidVideoError):
                youtube.fetch_video_metadata(VIDEO_URL)


class CheckVideoDurationTests(SimpleTestCase):
    """Cover the duration guard on its own."""

    def test_a_video_within_the_limit_passes(self):
        """A short video is not rejected."""
        metadata = video_metadata(duration=1.0)
        self.assertIsNone(youtube.check_video_duration(metadata))

    def test_the_limit_itself_is_still_accepted(self):
        """The configured maximum is inclusive."""
        metadata = video_metadata(duration=MAX_VIDEO_DURATION_SECONDS)
        self.assertIsNone(youtube.check_video_duration(metadata))

    def test_a_video_above_the_limit_is_rejected(self):
        """One second above the maximum is already too long."""
        metadata = video_metadata(duration=MAX_VIDEO_DURATION_SECONDS + 1)
        with self.assertRaises(VideoTooLongError):
            youtube.check_video_duration(metadata)

    def test_the_message_names_the_limit(self):
        """The rejection message states the supported maximum."""
        self.assertIn(
            str(MAX_VIDEO_DURATION_SECONDS),
            youtube.VIDEO_TOO_LONG_MESSAGE,
        )

    def test_a_missing_duration_is_rejected(self):
        """A live stream reports no duration and is refused."""
        metadata = video_metadata(duration=None)
        with self.assertRaises(InvalidVideoError):
            youtube.check_video_duration(metadata)

    def test_a_zero_duration_is_rejected(self):
        """A video of no length has nothing to transcribe."""
        metadata = video_metadata(duration=0)
        with self.assertRaises(InvalidVideoError):
            youtube.check_video_duration(metadata)


class DurationGuardBlocksTheDownloadTests(SimpleTestCase):
    """Prove that a refused video is never downloaded."""

    def setUp(self):
        """Replace yt_dlp and the download step of the pipeline."""
        youtube_dl = self.enterContext(mock.patch(YOUTUBE_DL_TARGET))
        self.extract_info = downloader_of(youtube_dl).extract_info
        self.download = self.enterContext(mock.patch(DOWNLOAD_AUDIO_TARGET))

    def assert_refused_before_the_download(self, duration, expected):
        """Assert a duration raises and starts no download."""
        self.extract_info.return_value = video_metadata(duration=duration)
        with self.assertRaises(expected):
            with youtube.prepared_audio(VIDEO_URL):
                pass
        self.download.assert_not_called()

    def test_an_overlong_video_is_not_downloaded(self):
        """A video above the limit stops at the metadata step."""
        self.assert_refused_before_the_download(
            MAX_VIDEO_DURATION_SECONDS + 1, VideoTooLongError
        )

    def test_a_video_without_a_duration_is_not_downloaded(self):
        """A live stream stops at the metadata step."""
        self.assert_refused_before_the_download(None, InvalidVideoError)
