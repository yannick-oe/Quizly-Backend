"""Shared helpers for the quiz_app tests.

Every external call of the generation pipeline is replaced through the
targets named here. The suite starts no subprocess, opens no socket and
downloads no model weights.

quiz_payload() builds a model answer that passes validation unchanged.
Every test that wants a rejected one starts from it and breaks exactly
one rule, so what a test is about is the one line that differs.

The endpoint tests share QuizEndpointTestCase. It creates two users
with one quiz each, so "my quiz" and "somebody else's quiz" are both
in the database of every test, and authenticates the client by setting
the access cookie directly. Going through POST /api/login/ would make
every quiz test depend on the login endpoint as well.
"""

import json
import string
import subprocess
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from quiz_app.constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ
from quiz_app.models import Question, Quiz

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

GENERATE_QUIZ_TARGET = "quiz_app.api.views.generate_quiz"

VIEWS_LOGGER = "quiz_app.api.views"

QUIZ_LIST_ROUTE = "quiz-list"

QUIZ_DETAIL_ROUTE = "quiz-detail"

USERNAME = "quizmaster"

OTHER_USERNAME = "someone-else"

PASSWORD = "correct-horse-battery"

FOREIGN_TITLE = "A quiz of somebody else"

MISSING_QUIZ_ID = 999_999

QUIZ_FIELD_ORDER = [
    "id",
    "title",
    "description",
    "created_at",
    "updated_at",
    "video_url",
    "questions",
]

QUESTION_FIELD_ORDER = [
    "id",
    "question_title",
    "question_options",
    "answer",
    "created_at",
    "updated_at",
]


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


def quiz_list_url():
    """Return the URL of the quiz collection."""
    return reverse(QUIZ_LIST_ROUTE)


def quiz_detail_url(quiz_id):
    """Return the URL of a single quiz."""
    return reverse(QUIZ_DETAIL_ROUTE, args=[quiz_id])


def create_user(username=USERNAME):
    """Create an account the quiz endpoints can be called as."""
    return User.objects.create_user(username=username, password=PASSWORD)


def authenticate(client, user):
    """Give a client the access cookie of a user."""
    access_token = RefreshToken.for_user(user).access_token
    client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = str(access_token)


def anonymous_client():
    """Return a client that carries no cookie at all."""
    return Client()


def create_quiz(owner, **overrides):
    """Store a quiz with a full set of questions for a user."""
    fields = {
        "title": QUIZ_TITLE,
        "description": QUIZ_DESCRIPTION,
        "video_url": VIDEO_URL,
    }
    fields.update(overrides)
    quiz = Quiz.objects.create(owner=owner, **fields)
    Question.objects.bulk_create(
        [
            Question(quiz=quiz, **question_payload(index))
            for index in range(1, QUESTIONS_PER_QUIZ + 1)
        ]
    )
    return quiz


class QuizEndpointTestCase(TestCase):
    """Two users, one quiz each, and a client logged in as the first."""

    @classmethod
    def setUpTestData(cls):
        """Create both accounts and a quiz for each of them."""
        cls.user = create_user()
        cls.other_user = create_user(OTHER_USERNAME)
        cls.quiz = create_quiz(cls.user)
        cls.foreign_quiz = create_quiz(cls.other_user, title=FOREIGN_TITLE)

    def setUp(self):
        """Authenticate the shared client as the first user."""
        authenticate(self.client, self.user)
