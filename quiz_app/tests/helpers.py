"""Shared helpers for the quiz_app tests.

Every external call of the generation pipeline is replaced through the
targets named here. The suite starts no subprocess, opens no socket and
downloads no model weights.

quiz_payload() builds a model answer that passes validation unchanged.
Every test that wants a rejected one starts from it and breaks exactly
one rule, so what a test is about is the one line that differs.
"""

import json
import string
import subprocess
from pathlib import Path
from types import SimpleNamespace

from quiz_app.constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ

VIDEO_ID = "dQw4w9WgXcQ"

VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"

YOUTUBE_DL_TARGET = "quiz_app.services.youtube.YoutubeDL"

SUBPROCESS_RUN_TARGET = "quiz_app.services.youtube.subprocess.run"

DOWNLOAD_AUDIO_TARGET = "quiz_app.services.youtube.download_audio"

LOAD_MODEL_TARGET = "quiz_app.services.transcription.whisper.load_model"

GEMINI_CLIENT_TARGET = "quiz_app.services.gemini.genai.Client"

REQUEST_COMPLETION_TARGET = "quiz_app.services.generation.request_completion"

PREPARED_AUDIO_TARGET = "quiz_app.services.generation.prepared_audio"

TRANSCRIBE_AUDIO_TARGET = "quiz_app.services.generation.transcribe_audio"

BUILD_QUESTION_TARGET = "quiz_app.services.generation.build_question"

YOUTUBE_LOGGER = "quiz_app.services.youtube"

TRANSCRIPTION_LOGGER = "quiz_app.services.transcription"

GEMINI_LOGGER = "quiz_app.services.gemini"

GENERATION_LOGGER = "quiz_app.services.generation"

TRANSCRIPT = "The Roman Republic ended in a series of civil wars."

QUIZ_TITLE = "The fall of the Roman Republic"

QUIZ_DESCRIPTION = "Ten questions about the last years of the Republic."

OPTION_LABELS = string.ascii_uppercase[:OPTIONS_PER_QUESTION]

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


def question_options(index):
    """Return the options of one well-formed question."""
    return [f"Option {index}{label}" for label in OPTION_LABELS]


def question_payload(index, **overrides):
    """Return one well-formed question of a model answer."""
    options = question_options(index)
    payload = {
        "question_title": f"Question {index} about the Republic?",
        "question_options": options,
        "answer": options[0],
    }
    payload.update(overrides)
    return payload


def quiz_payload(**overrides):
    """Return a model answer that passes validation unchanged."""
    payload = {
        "title": QUIZ_TITLE,
        "description": QUIZ_DESCRIPTION,
        "questions": [
            question_payload(index)
            for index in range(1, QUESTIONS_PER_QUIZ + 1)
        ],
    }
    payload.update(overrides)
    return payload


def payload_with_first_question(**overrides):
    """Return a quiz whose first question breaks one rule."""
    questions = quiz_payload()["questions"]
    questions[0] = question_payload(1, **overrides)
    return quiz_payload(questions=questions)


def as_json(payload):
    """Return a payload as the raw JSON text that was asked for."""
    return json.dumps(payload)


def as_fenced_json(payload, language=""):
    """Return a payload wrapped in a Markdown code fence."""
    return f"```{language}\n{as_json(payload)}\n```"


def gemini_response(text):
    """Return a stand-in for a Gemini response object."""
    return SimpleNamespace(text=text)
