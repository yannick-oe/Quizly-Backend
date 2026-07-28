"""The whole chain from a YouTube URL to a stored quiz.

Order: normalise, fetch metadata, check the length, download, convert,
transcribe, ask Gemini, validate, store. Nothing is written before the
last step, so every failure before it leaves the database untouched by
construction rather than by rollback.

Gemini gets a second chance and no more. An unusable answer is retried
once with a stricter prompt; if that one is unusable too, the run ends
with QuizContentError. A loop over a model that keeps answering the
same way would hold the request open until the client gives up.

An unusable answer is logged before it is dropped. The delivered
frontend shows nothing but "Error generating quiz", so the log is the
only place where the reason survives.
"""

import logging

from django.db import transaction

from ..api.serializers import GeneratedQuizSerializer
from ..constants import INVALID_URL_MESSAGE
from ..models import Question, Quiz
from ..utils import normalize_youtube_url, parse_json_response
from .exceptions import InvalidVideoError, QuizContentError
from .gemini import request_completion
from .prompts import build_prompt_sequence
from .transcription import transcribe_audio
from .youtube import prepared_audio

LOGGER = logging.getLogger(__name__)

UNUSABLE_OUTPUT_MESSAGE = (
    "The quiz service did not return a usable quiz for this video."
)


def generate_quiz(user, url):
    """Create and store a quiz for a user from a YouTube URL."""
    video_url = normalize_youtube_url(url)
    if video_url is None:
        raise InvalidVideoError(INVALID_URL_MESSAGE)
    transcript = transcribe_video(video_url)
    payload = generate_quiz_payload(transcript)
    return store_quiz(user, video_url, payload)


def transcribe_video(video_url):
    """Return the spoken text of the video behind a URL.

    The audio only exists inside the with block; its temporary
    directory is gone by the time the transcript is returned.
    """
    with prepared_audio(video_url) as audio_path:
        return transcribe_audio(audio_path)


def generate_quiz_payload(transcript):
    """Return validated quiz data for a transcript."""
    for prompt in build_prompt_sequence(transcript):
        payload = validated_payload(prompt)
        if payload is not None:
            return payload
    raise QuizContentError(UNUSABLE_OUTPUT_MESSAGE)


def validated_payload(prompt):
    """Return validated quiz data, or None when it is unusable.

    Only an unusable answer becomes None. A failing request raises,
    because retrying it with a different prompt would not help.
    """
    text = request_completion(prompt)
    try:
        data = parse_json_response(text)
    except ValueError as error:
        LOGGER.warning("Gemini answered with no usable JSON: %s", error)
        return None
    serializer = GeneratedQuizSerializer(data=data)
    if not serializer.is_valid():
        LOGGER.warning("Gemini output refused: %s", serializer.errors)
        return None
    return serializer.validated_data


@transaction.atomic
def store_quiz(user, video_url, payload):
    """Persist a validated quiz with all of its questions."""
    quiz = Quiz.objects.create(
        owner=user,
        title=payload["title"],
        description=payload["description"],
        video_url=video_url,
    )
    Question.objects.bulk_create(
        [build_question(quiz, item) for item in payload["questions"]]
    )
    return quiz


def build_question(quiz, item):
    """Return an unsaved question for one validated payload item."""
    return Question(
        quiz=quiz,
        question_title=item["question_title"],
        question_options=list(item["question_options"]),
        answer=item["answer"],
    )
