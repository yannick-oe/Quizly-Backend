"""Fixed values of the quiz domain."""

MAX_VIDEO_DURATION_SECONDS = 1800

FFMPEG_TIMEOUT_SECONDS = 120

GEMINI_TIMEOUT_MILLISECONDS = 60_000

GEMINI_RETRY_DELAY_SECONDS = 2

QUESTIONS_PER_QUIZ = 10

OPTIONS_PER_QUESTION = 4

INVALID_URL_MESSAGE = (
    "This is not a YouTube video URL. Use a link of the form "
    "https://www.youtube.com/watch?v=<id>."
)
