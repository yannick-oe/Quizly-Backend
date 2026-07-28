"""Fixed values of the quiz domain.

The services, the serializers and the tests all read these values from
here. This module is the only place they are defined.

The two time limits come from a measurement rather than a guess. On the
reference machine a 345 second video costs 10.5 seconds end to end,
which is about 33 times realtime, so half an hour of video needs about
55 seconds of processing before Gemini is even asked. Chrome gives a
fetch without its own timeout roughly 300 seconds, and quiz generation
answers inside the request, so that budget has to cover everything.

The two Gemini numbers spend the rest of that budget. A model that
answers "not now" is asked a second time after a short pause, so one
generation can cost two request timeouts and the pause between them.

The one message here is not a quantity. The same sentence refuses a
link that is not a YouTube video twice: once in the create serializer,
before anything is downloaded, and once at the head of the pipeline,
which is callable on its own. The pipeline imports the serializer, so
the serializer cannot import the pipeline; this module imports neither
and is the only place both can read it from.
"""

MAX_VIDEO_DURATION_SECONDS = 1800

FFMPEG_TIMEOUT_SECONDS = 120

GEMINI_TIMEOUT_MILLISECONDS = 120_000

GEMINI_RETRY_DELAY_SECONDS = 2

QUESTIONS_PER_QUIZ = 10

OPTIONS_PER_QUESTION = 4

INVALID_URL_MESSAGE = (
    "This is not a YouTube video URL. Use a link of the form "
    "https://www.youtube.com/watch?v=<id>."
)
