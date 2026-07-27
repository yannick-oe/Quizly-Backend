"""Tests for PATCH /api/quizzes/{id}/.

The delivered frontend sends title and description together on every
keystroke, so the ordinary case is a body that repeats a value which
did not change. It also never sends video_url or questions, but a
client could: both are declared read-only, which makes DRF drop them
instead of answering 400 for a field that cannot be written.
"""

from django.utils.dateparse import parse_datetime

from .helpers import (
    MISSING_QUIZ_ID,
    QUIZ_DESCRIPTION,
    QUIZ_TITLE,
    QuizEndpointTestCase,
    anonymous_client,
    quiz_detail_url,
)

NEW_TITLE = "A better title"

NEW_DESCRIPTION = "A better description"

OTHER_VIDEO_URL = "https://www.youtube.com/watch?v=someOtherId"

TITLE_KEY = "title"

DESCRIPTION_KEY = "description"

VIDEO_URL_KEY = "video_url"

UPDATED_AT_KEY = "updated_at"


class QuizUpdateTests(QuizEndpointTestCase):
    """Cover the partial update of a single quiz."""

    def patch(self, quiz_id, body, client=None):
        """Send a partial update for one quiz."""
        return (client or self.client).patch(
            quiz_detail_url(quiz_id),
            data=body,
            content_type="application/json",
        )

    def patch_own(self, body):
        """Send a partial update for the quiz of the test user."""
        return self.patch(self.quiz.pk, body)

    def full_update(self):
        """Send both fields the delivered frontend always sends."""
        return self.patch_own(
            {TITLE_KEY: NEW_TITLE, DESCRIPTION_KEY: NEW_DESCRIPTION}
        )

    def test_an_update_is_answered_with_200(self):
        """The documented success code of a partial update."""
        self.assertEqual(self.full_update().status_code, 200)

    def test_both_fields_are_answered_with_their_new_values(self):
        """The body of the answer shows the updated quiz."""
        body = self.full_update().json()
        self.assertEqual(body[TITLE_KEY], NEW_TITLE)
        self.assertEqual(body[DESCRIPTION_KEY], NEW_DESCRIPTION)

    def test_both_fields_are_stored(self):
        """What was answered is what the database holds."""
        self.full_update()
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, NEW_TITLE)
        self.assertEqual(self.quiz.description, NEW_DESCRIPTION)

    def test_a_single_field_can_be_updated_on_its_own(self):
        """A partial update leaves the field it does not name."""
        self.patch_own({TITLE_KEY: NEW_TITLE})
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.description, QUIZ_DESCRIPTION)

    def test_updated_at_moves_forward(self):
        """The timestamp the documentation shows is a fresh one."""
        before = self.quiz.updated_at
        answered = parse_datetime(self.full_update().json()[UPDATED_AT_KEY])
        self.assertGreater(answered, before)

    def test_a_read_only_video_url_is_ignored(self):
        """A field the contract does not write is dropped, not 400."""
        response = self.patch_own({VIDEO_URL_KEY: OTHER_VIDEO_URL})
        self.assertEqual(response.status_code, 200)
        self.quiz.refresh_from_db()
        self.assertNotEqual(self.quiz.video_url, OTHER_VIDEO_URL)

    def test_an_empty_title_answers_400(self):
        """A title is required, and blank is not a title."""
        self.assertEqual(self.patch_own({TITLE_KEY: ""}).status_code, 400)

    def test_a_foreign_quiz_answers_403(self):
        """Only the owner may edit a quiz."""
        response = self.patch(self.foreign_quiz.pk, {TITLE_KEY: NEW_TITLE})
        self.assertEqual(response.status_code, 403)

    def test_a_refused_update_changes_nothing(self):
        """A 403 leaves the quiz of the other user untouched."""
        self.patch(self.foreign_quiz.pk, {TITLE_KEY: NEW_TITLE})
        self.foreign_quiz.refresh_from_db()
        self.assertNotEqual(self.foreign_quiz.title, NEW_TITLE)

    def test_an_unknown_id_answers_404(self):
        """A quiz that does not exist cannot be updated."""
        response = self.patch(MISSING_QUIZ_ID, {TITLE_KEY: NEW_TITLE})
        self.assertEqual(response.status_code, 404)

    def test_an_unauthenticated_request_answers_401(self):
        """Without the access cookie nothing is updated."""
        response = self.patch(
            self.quiz.pk,
            {TITLE_KEY: NEW_TITLE},
            anonymous_client(),
        )
        self.assertEqual(response.status_code, 401)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, QUIZ_TITLE)
