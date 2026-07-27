"""The instructions Gemini is given for a quiz.

A prompt is code, not a string that belongs in a view. It lives here so
that it can be read, reviewed and changed in one place.

Every number in the text is interpolated, never typed out: the counts
come from quiz_app.constants and the title limit from the model field
that stores it. The prompt and the serializer that judges the answer
would otherwise drift apart, and a drift there costs a whole run.

Two prompts, not one. The first asks for a quiz. The second repeats the
request after an unusable answer and spells out the rules the first
attempt broke, because repeating the same words rarely produces a
different result.

The transcript is put in with str.replace and not with str.format. The
prompt shows Gemini a JSON skeleton, so it is full of braces that
format() would read as fields of its own.
"""

from ..constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ
from ..models import Quiz

TRANSCRIPT_PLACEHOLDER = "<<TRANSCRIPT>>"

TITLE_MAX_LENGTH = Quiz._meta.get_field("title").max_length

SHAPE = """Answer with a single JSON object of this shape:
{"title": "...", "description": "...", "questions": [
  {"question_title": "...", "question_options": ["...", "..."],
   "answer": "..."}]}"""

RULES = f"""Rules, all of them mandatory:
- Write the quiz in the language of the transcript.
- "questions" holds exactly {QUESTIONS_PER_QUIZ} objects.
- Every "question_options" holds exactly {OPTIONS_PER_QUESTION} strings.
- The options of a question differ from one another. No repeated \
option, no rephrasing of the same answer.
- "answer" repeats one of that question's own options character for \
character. Not a letter, not an index, not a shortened form.
- No field is empty, and "title" stays under {TITLE_MAX_LENGTH} chars.
- Ask only about what the transcript actually says.
- Answer with raw JSON: no Markdown code fence, no language tag, no \
sentence before or after the JSON."""

QUIZ_PROMPT = f"""You turn the transcript of a video into a \
multiple-choice quiz.

{SHAPE}

{RULES}

Transcript:
{TRANSCRIPT_PLACEHOLDER}"""

REPAIR_PROMPT = f"""Your previous answer could not be used: it was not \
valid JSON, or it broke one of the rules below. Build the quiz again \
and check every rule before you answer.

{SHAPE}

{RULES}

Count before you answer: exactly {QUESTIONS_PER_QUIZ} questions, and \
exactly {OPTIONS_PER_QUESTION} distinct options for each of them. Copy \
every "answer" character for character out of that question's own \
options.

Transcript:
{TRANSCRIPT_PLACEHOLDER}"""


def build_prompt(template, transcript):
    """Return a prompt template with the transcript put in."""
    return template.replace(TRANSCRIPT_PLACEHOLDER, transcript)


def build_prompt_sequence(transcript):
    """Return the prompts to try, in order, for one transcript.

    Its length is the number of Gemini calls one generation can ever
    cost: a first attempt and a repair, then the caller gives up.
    """
    return (
        build_prompt(QUIZ_PROMPT, transcript),
        build_prompt(REPAIR_PROMPT, transcript),
    )
