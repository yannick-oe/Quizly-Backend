"""Tests for the gate the Gemini output has to pass."""

from django.test import SimpleTestCase

from quiz_app.api.serializers import (
    TITLE_MAX_LENGTH,
    GeneratedQuizSerializer,
)
from quiz_app.constants import OPTIONS_PER_QUESTION, QUESTIONS_PER_QUIZ

from .helpers import (
    QUIZ_DESCRIPTION,
    QUIZ_TITLE,
    payload_with_first_question,
    question_options,
    question_payload,
    quiz_payload,
)


def questions_numbering(count):
    """Return a list of well-formed questions of a given length."""
    return [question_payload(index) for index in range(1, count + 1)]


class SerializerTestCase(SimpleTestCase):
    """Give every test the two assertions it actually makes."""

    def assert_accepted(self, payload):
        """Assert a payload validates and return its clean data."""
        serializer = GeneratedQuizSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return serializer.validated_data

    def assert_refused(self, payload):
        """Assert a payload does not validate."""
        serializer = GeneratedQuizSerializer(data=payload)
        self.assertFalse(serializer.is_valid())


class AcceptedQuizTests(SerializerTestCase):
    """Cover the answer the prompt asks Gemini for."""

    def test_a_well_formed_payload_is_accepted(self):
        """The shape the prompt describes passes untouched."""
        data = self.assert_accepted(quiz_payload())
        self.assertEqual(data["title"], QUIZ_TITLE)
        self.assertEqual(data["description"], QUIZ_DESCRIPTION)
        self.assertEqual(len(data["questions"]), QUESTIONS_PER_QUIZ)

    def test_every_question_keeps_its_options_and_answer(self):
        """The clean data carries the fields the model layer needs."""
        data = self.assert_accepted(quiz_payload())
        first = data["questions"][0]
        self.assertEqual(first["question_options"], question_options(1))
        self.assertEqual(first["answer"], question_options(1)[0])

    def test_a_title_of_the_maximum_length_is_accepted(self):
        """The limit itself is still inside the limit."""
        title = "T" * TITLE_MAX_LENGTH
        data = self.assert_accepted(quiz_payload(title=title))
        self.assertEqual(data["title"], title)


class StrippedValuesTests(SerializerTestCase):
    """Cover the stripping of every accepted string."""

    def test_padding_is_removed_from_every_string(self):
        """No value reaches the database with its padding."""
        options = question_options(1)
        padded = [f"  {option}\n" for option in options]
        payload = payload_with_first_question(
            question_title="  Padded?  ",
            question_options=padded,
            answer=f"\t{options[0]} ",
        )
        first = self.assert_accepted(payload)["questions"][0]
        self.assertEqual(first["question_title"], "Padded?")
        self.assertEqual(first["question_options"], options)
        self.assertEqual(first["answer"], options[0])

    def test_an_answer_matching_only_after_stripping_is_accepted(self):
        """Padding around the answer is not treated as a mismatch."""
        options = question_options(1)
        payload = payload_with_first_question(answer=f" {options[2]} ")
        first = self.assert_accepted(payload)["questions"][0]
        self.assertEqual(first["answer"], options[2])

    def test_the_title_is_stripped_as_well(self):
        """A padded title is trimmed, not rejected."""
        data = self.assert_accepted(quiz_payload(title=f" {QUIZ_TITLE} "))
        self.assertEqual(data["title"], QUIZ_TITLE)


class QuestionCountTests(SerializerTestCase):
    """Cover the required number of questions."""

    def test_one_question_too_few_is_refused(self):
        """Nine questions are not a quiz."""
        questions = questions_numbering(QUESTIONS_PER_QUIZ - 1)
        self.assert_refused(quiz_payload(questions=questions))

    def test_one_question_too_many_is_refused(self):
        """Eleven questions are not a quiz either."""
        questions = questions_numbering(QUESTIONS_PER_QUIZ + 1)
        self.assert_refused(quiz_payload(questions=questions))

    def test_no_questions_at_all_are_refused(self):
        """An empty list does not pass as a set of questions."""
        self.assert_refused(quiz_payload(questions=[]))

    def test_a_missing_questions_key_is_refused(self):
        """A quiz without questions is not a quiz."""
        payload = quiz_payload()
        del payload["questions"]
        self.assert_refused(payload)


class OptionCountTests(SerializerTestCase):
    """Cover the required number of options."""

    def test_one_option_too_few_is_refused(self):
        """Three options are refused."""
        options = question_options(1)[: OPTIONS_PER_QUESTION - 1]
        self.assert_refused(
            payload_with_first_question(
                question_options=options, answer=options[0]
            )
        )

    def test_one_option_too_many_is_refused(self):
        """Five options are refused."""
        options = question_options(1) + ["Option 1E"]
        self.assert_refused(
            payload_with_first_question(
                question_options=options, answer=options[0]
            )
        )

    def test_a_repeated_option_is_refused(self):
        """Two identical options are refused."""
        options = question_options(1)
        options[2] = options[0]
        self.assert_refused(
            payload_with_first_question(
                question_options=options, answer=options[0]
            )
        )

    def test_options_that_repeat_after_stripping_are_refused(self):
        """Padding does not turn a duplicate into a distinct option."""
        options = question_options(1)
        options[2] = f"  {options[0]}  "
        self.assert_refused(
            payload_with_first_question(
                question_options=options, answer=options[0]
            )
        )

    def test_an_empty_option_is_refused(self):
        """A blank option is no option."""
        options = question_options(1)
        options[3] = "   "
        self.assert_refused(
            payload_with_first_question(
                question_options=options, answer=options[0]
            )
        )


class AnswerTests(SerializerTestCase):
    """Cover the rule that the answer is one of the options."""

    def test_an_answer_outside_the_options_is_refused(self):
        """An answer nobody can pick is refused."""
        self.assert_refused(
            payload_with_first_question(answer="Something else")
        )

    def test_a_letter_instead_of_the_text_is_refused(self):
        """The model answering "A" does not pass as an option."""
        self.assert_refused(payload_with_first_question(answer="A"))

    def test_an_answer_differing_in_case_is_refused(self):
        """The answer comparison is case sensitive."""
        self.assert_refused(
            payload_with_first_question(answer=question_options(1)[0].upper())
        )

    def test_an_empty_answer_is_refused(self):
        """An empty answer is refused."""
        self.assert_refused(payload_with_first_question(answer=""))

    def test_an_empty_question_title_is_refused(self):
        """A blank question title is refused."""
        self.assert_refused(payload_with_first_question(question_title="   "))


class QuizFieldTests(SerializerTestCase):
    """Cover the two fields of the quiz itself."""

    def test_an_empty_title_is_refused(self):
        """A quiz needs a title."""
        self.assert_refused(quiz_payload(title=""))

    def test_a_whitespace_title_is_refused(self):
        """Padding alone does not count as a title."""
        self.assert_refused(quiz_payload(title="   "))

    def test_one_character_over_the_title_limit_is_refused(self):
        """A title over the limit is refused."""
        self.assert_refused(quiz_payload(title="T" * (TITLE_MAX_LENGTH + 1)))

    def test_an_empty_description_is_refused(self):
        """A quiz needs a description."""
        self.assert_refused(quiz_payload(description=""))

    def test_a_list_instead_of_an_object_is_refused(self):
        """A wrong top-level type is refused."""
        self.assert_refused([quiz_payload()])
