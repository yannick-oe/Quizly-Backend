"""The instructions Gemini is given for a quiz."""

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
    """Return the prompts to try, in order, for one transcript."""
    return (
        build_prompt(QUIZ_PROMPT, transcript),
        build_prompt(REPAIR_PROMPT, transcript),
    )
