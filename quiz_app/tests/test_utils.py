"""Tests for the stateless helpers of the quiz_app app.

The URL forms below are the ones a user can paste into the delivered
frontend. All of them have to end up as the same watch URL, because
that frontend extracts the video id with a regular expression on "v=".
"""

from django.test import SimpleTestCase

from quiz_app.utils import extract_youtube_video_id, normalize_youtube_url

from .helpers import VIDEO_ID

CANONICAL_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"

ACCEPTED_URLS = (
    ("the watch form", f"https://www.youtube.com/watch?v={VIDEO_ID}"),
    (
        "extra query parameters",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42s&list=PLabc",
    ),
    ("a youtu.be short link", f"https://youtu.be/{VIDEO_ID}"),
    ("a short link with a query", f"https://youtu.be/{VIDEO_ID}?t=42"),
    ("the m. subdomain", f"https://m.youtube.com/watch?v={VIDEO_ID}"),
    ("a shorts link", f"https://www.youtube.com/shorts/{VIDEO_ID}"),
    ("an embed link", f"https://www.youtube.com/embed/{VIDEO_ID}"),
    ("a live link", f"https://www.youtube.com/live/{VIDEO_ID}"),
    ("a host without www", f"https://youtube.com/watch?v={VIDEO_ID}"),
    ("an uppercase host", f"HTTPS://WWW.YOUTUBE.COM/watch?v={VIDEO_ID}"),
    ("plain http", f"http://www.youtube.com/watch?v={VIDEO_ID}"),
    ("surrounding whitespace", f"  https://youtu.be/{VIDEO_ID}  "),
)

REJECTED_URLS = (
    ("a different site", "https://vimeo.com/76979871"),
    (
        "a lookalike host",
        f"https://youtube.com.example.test/watch?v={VIDEO_ID}",
    ),
    ("no URL at all", "just some text"),
    ("an empty string", ""),
    ("a channel page", "https://www.youtube.com/@developerakademie"),
    ("a playlist", "https://www.youtube.com/playlist?list=PLabc"),
    ("a watch URL without an id", "https://www.youtube.com/watch"),
    ("a bare short link", "https://youtu.be/"),
    ("a shorts path without an id", "https://www.youtube.com/shorts/"),
    ("an id outside any path", f"https://www.youtube.com/?v={VIDEO_ID}"),
    ("an unsupported scheme", f"ftp://youtube.com/watch?v={VIDEO_ID}"),
    ("a punctuated id", "https://www.youtube.com/watch?v=not+an+id"),
)


class NormalizeYoutubeUrlTests(SimpleTestCase):
    """Cover the URL forms the pipeline has to accept and refuse."""

    def test_accepted_forms_become_the_canonical_watch_url(self):
        """Every supported YouTube form yields the same watch URL."""
        for label, url in ACCEPTED_URLS:
            with self.subTest(form=label):
                self.assertEqual(normalize_youtube_url(url), CANONICAL_URL)

    def test_rejected_forms_answer_none(self):
        """Anything that is not a single video answers None."""
        for label, url in REJECTED_URLS:
            with self.subTest(form=label):
                self.assertIsNone(normalize_youtube_url(url))

    def test_the_documented_example_url_survives(self):
        """The example URL of the endpoint documentation is kept."""
        url = "https://www.youtube.com/watch?v=example"
        self.assertEqual(normalize_youtube_url(url), url)

    def test_the_extracted_id_carries_no_decoration(self):
        """The id helper answers with the bare video id."""
        short_link = f"https://youtu.be/{VIDEO_ID}"
        self.assertEqual(extract_youtube_video_id(short_link), VIDEO_ID)

    def test_an_unusable_url_has_no_video_id(self):
        """The id helper answers None where the URL is not a video."""
        self.assertIsNone(extract_youtube_video_id("https://example.test"))
