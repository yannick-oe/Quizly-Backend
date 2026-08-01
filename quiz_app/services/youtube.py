"""Audio acquisition for the quiz pipeline."""

import logging
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import YoutubeDLError

from ..constants import (
    FFMPEG_TIMEOUT_SECONDS,
    MAX_VIDEO_DURATION_SECONDS,
)
from .exceptions import (
    AudioConversionError,
    InvalidVideoError,
    VideoTooLongError,
)

LOGGER = logging.getLogger(__name__)

DURATION_KEY = "duration"

COMMON_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}

METADATA_OPTIONS = {**COMMON_OPTIONS, "skip_download": True}

AUDIO_FORMAT = "bestaudio/best"

DOWNLOAD_TEMPLATE = "source.%(ext)s"

WAV_FILE_NAME = "audio.wav"

FFMPEG_BINARY = "ffmpeg"

WAV_SAMPLE_RATE = "16000"

WAV_CHANNELS = "1"

FFMPEG_QUIET_ARGUMENTS = ("-nostdin", "-loglevel", "error", "-y")

FFMPEG_INPUT_FLAG = "-i"

FFMPEG_WAV_ARGUMENTS = (
    "-vn",
    "-ar",
    WAV_SAMPLE_RATE,
    "-ac",
    WAV_CHANNELS,
)

VIDEO_UNAVAILABLE_MESSAGE = (
    "The video could not be read. It may be private, removed, region "
    "locked or not a video at all."
)

UNKNOWN_DURATION_MESSAGE = (
    "The video has no fixed length. A live stream cannot be turned "
    "into a quiz."
)

VIDEO_TOO_LONG_MESSAGE = (
    "The video is longer than the supported maximum of "
    f"{MAX_VIDEO_DURATION_SECONDS} seconds."
)

DOWNLOAD_FAILED_MESSAGE = (
    "The audio track of the video could not be downloaded."
)

CONVERSION_FAILED_MESSAGE = (
    "The downloaded audio could not be converted for transcription."
)


def fetch_video_metadata(url):
    """Return the metadata of a video without downloading it."""
    try:
        with YoutubeDL(METADATA_OPTIONS) as downloader:
            metadata = downloader.extract_info(url, download=False)
    except YoutubeDLError as error:
        LOGGER.info("Metadata lookup failed for %s: %s", url, error)
        raise InvalidVideoError(VIDEO_UNAVAILABLE_MESSAGE) from error
    if not metadata:
        raise InvalidVideoError(VIDEO_UNAVAILABLE_MESSAGE)
    return metadata


def check_video_duration(metadata):
    """Reject a video without a length or above the limit."""
    duration = metadata.get(DURATION_KEY)
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise InvalidVideoError(UNKNOWN_DURATION_MESSAGE)
    if duration > MAX_VIDEO_DURATION_SECONDS:
        raise VideoTooLongError(VIDEO_TOO_LONG_MESSAGE)


def build_download_options(target_dir):
    """Return the yt_dlp options for an audio-only download."""
    return {
        **COMMON_OPTIONS,
        "format": AUDIO_FORMAT,
        "outtmpl": str(Path(target_dir) / DOWNLOAD_TEMPLATE),
    }


def download_audio(url, target_dir):
    """Download the audio stream of a video into a directory."""
    try:
        with YoutubeDL(build_download_options(target_dir)) as downloader:
            downloader.download([url])
    except YoutubeDLError as error:
        LOGGER.info("Audio download failed for %s: %s", url, error)
        raise InvalidVideoError(DOWNLOAD_FAILED_MESSAGE) from error
    return _downloaded_file(target_dir)


def _downloaded_file(target_dir):
    """Return the file yt_dlp wrote into an empty directory."""
    files = sorted(Path(target_dir).iterdir())
    if not files:
        raise InvalidVideoError(DOWNLOAD_FAILED_MESSAGE)
    return files[0]


def build_ffmpeg_command(source_path, target_path):
    """Return the argument list that writes a mono WAV track."""
    return [
        FFMPEG_BINARY,
        *FFMPEG_QUIET_ARGUMENTS,
        FFMPEG_INPUT_FLAG,
        str(source_path),
        *FFMPEG_WAV_ARGUMENTS,
        str(target_path),
    ]


def convert_to_wav(source_path, target_dir):
    """Convert a downloaded audio file into a mono WAV track."""
    target_path = Path(target_dir) / WAV_FILE_NAME
    try:
        subprocess.run(
            build_ffmpeg_command(source_path, target_path),
            capture_output=True,
            check=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        LOGGER.error("FFmpeg conversion failed: %s", error)
        raise AudioConversionError(CONVERSION_FAILED_MESSAGE) from error
    return target_path


@contextmanager
def prepared_audio(url):
    """Yield a WAV track for a video and remove it afterwards."""
    check_video_duration(fetch_video_metadata(url))
    with tempfile.TemporaryDirectory() as target_dir:
        source_path = download_audio(url, target_dir)
        yield convert_to_wav(source_path, target_dir)
