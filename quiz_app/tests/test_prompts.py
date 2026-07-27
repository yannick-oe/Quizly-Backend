"""Tests for the instructions Gemini is given.

Nothing external is involved: the prompts are strings, and these tests
only read them. Their point is that the prompt and the serializer stay
in agreement. A prompt that asks for a different number than the
serializer accepts fails every generation run, and it fails it after
the download and the transcription have already been paid for.
"""

from django.test import SimpleTestCase

from quiz_app.api.serializers import TITLE_MAX_LENGTH
from quiz_app.constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ
from quiz_app.services import prompts

TRANSCRIPT = "Caesar crossed the Rubicon in January 49 BC."

EXPECTED_ATTEMPTS = 2


class PromptSequenceTests(SimpleTestCase):
    """Cover the prompts one generation run may send."""

    def setUp(self):
        """Build the sequence once for every test."""
        self.prompts = prompts.build_prompt_sequence(TRANSCRIPT)

    def test_a_run_holds_one_attempt_and_one_repair(self):
        """The sequence length is the call budget of a run."""
        self.assertEqual(len(self.prompts), EXPECTED_ATTEMPTS)

    def test_every_prompt_carries_the_transcript(self):
        """Neither prompt asks about a video it did not see."""
        for prompt in self.prompts:
            with self.subTest(prompt=prompt[:40]):
                self.assertIn(TRANSCRIPT, prompt)

    def test_no_placeholder_survives(self):
        """The transcript marker is replaced, not sent along."""
        for prompt in self.prompts:
            with self.subTest(prompt=prompt[:40]):
                self.assertNotIn(prompts.TRANSCRIPT_PLACEHOLDER, prompt)

    def test_the_repair_prompt_differs_from_the_first(self):
        """The second attempt says more than the first one did."""
        first, repair = self.prompts
        self.assertNotEqual(first, repair)
        self.assertGreater(len(repair), len(first))


class PromptContentTests(SimpleTestCase):
    """Cover the numbers the prompt and the serializer share."""

    def test_both_prompts_name_the_question_count(self):
        """Gemini is told how many questions are expected."""
        for prompt in prompts.build_prompt_sequence(TRANSCRIPT):
            with self.subTest(prompt=prompt[:40]):
                self.assertIn(str(QUESTIONS_PER_QUIZ), prompt)

    def test_both_prompts_name_the_option_count(self):
        """Gemini is told how many options a question needs."""
        for prompt in prompts.build_prompt_sequence(TRANSCRIPT):
            with self.subTest(prompt=prompt[:40]):
                self.assertIn(str(OPTIONS_PER_QUESTION), prompt)

    def test_the_title_limit_matches_the_serializer(self):
        """The prompt quotes the limit the serializer enforces."""
        self.assertEqual(prompts.TITLE_MAX_LENGTH, TITLE_MAX_LENGTH)
        self.assertIn(str(TITLE_MAX_LENGTH), prompts.RULES)

    def test_the_answer_rule_is_stated(self):
        """The rule the frontend depends on is spelled out."""
        self.assertIn("character for character", prompts.RULES)

    def test_raw_json_is_asked_for(self):
        """The fence is discouraged even though it is stripped."""
        self.assertIn("raw JSON", prompts.RULES)
