"""Shared helpers for the quiz_app tests.

Every external call of the generation pipeline is replaced through the
targets named here. The suite starts no subprocess, opens no socket and
downloads no model weights.
"""

import subprocess
from pathlib import Path

VIDEO_ID = "dQw4w9WgXcQ"

VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"

YOUTUBE_DL_TARGET = "quiz_app.services.youtube.YoutubeDL"

SUBPROCESS_RUN_TARGET = "quiz_app.services.youtube.subprocess.run"

DOWNLOAD_AUDIO_TARGET = "quiz_app.services.youtube.download_audio"

LOAD_MODEL_TARGET = "quiz_app.services.transcription.whisper.load_model"

YOUTUBE_LOGGER = "quiz_app.services.youtube"

TRANSCRIPTION_LOGGER = "quiz_app.services.transcription"

SOURCE_FILE_NAME = "source.m4a"

SOURCE_BYTES = b"fake-audio"

WAV_BYTES = b"RIFF-fake-wav"

ACCEPTED_DURATION_SECONDS = 120.0


def downloader_of(youtube_dl):
    """Return the instance a patched YoutubeDL yields in a with."""
    return youtube_dl.return_value.__enter__.return_value


def video_metadata(**overrides):
    """Return yt_dlp metadata for a video of acceptable length."""
    values = {
        "duration": ACCEPTED_DURATION_SECONDS,
        "title": "A short video",
    }
    values.update(overrides)
    return values


def write_source_file(url, target_dir):
    """Stand in for a download by writing the file it would leave."""
    path = Path(target_dir) / SOURCE_FILE_NAME
    path.write_bytes(SOURCE_BYTES)
    return path


def write_wav_file(command, **kwargs):
    """Stand in for FFmpeg by writing the WAV it would produce."""
    Path(command[-1]).write_bytes(WAV_BYTES)
    return subprocess.CompletedProcess(command, 0)


class DirectoryRecorder:
    """A download replacement that remembers where it wrote."""

    def __init__(self):
        """Start out without a recorded directory."""
        self.directories = []

    def __call__(self, url, target_dir):
        """Record the directory and write the expected source file."""
        self.directories.append(Path(target_dir))
        return write_source_file(url, target_dir)
