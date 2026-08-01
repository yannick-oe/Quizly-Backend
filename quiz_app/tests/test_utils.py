"""Tests for the stateless helpers of the quiz_app app."""

from django.test import SimpleTestCase

from quiz_app.utils import (
    extract_youtube_video_id,
    normalize_youtube_url,
    parse_json_response,
    strip_code_fences,
)

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

PAYLOAD = {"title": "A quiz", "questions": [{"answer": "A"}]}

PAYLOAD_JSON = '{"title": "A quiz", "questions": [{"answer": "A"}]}'

WRAPPED_PAYLOADS = (
    ("no fence at all", PAYLOAD_JSON),
    ("a json fence", f"```json\n{PAYLOAD_JSON}\n```"),
    ("a bare fence", f"```\n{PAYLOAD_JSON}\n```"),
    ("an uppercase language tag", f"```JSON\n{PAYLOAD_JSON}\n```"),
    ("surrounding whitespace", f"\n\n  {PAYLOAD_JSON}  \n"),
    ("a padded fence", f"  ```json\n{PAYLOAD_JSON}\n```  \n"),
    ("carriage returns", f"```json\r\n{PAYLOAD_JSON}\r\n```"),
    ("a fence on one line", f"```json {PAYLOAD_JSON}```"),
    ("a bare fence without newlines", f"```{PAYLOAD_JSON}```"),
)

BROKEN_PAYLOADS = (
    ("an explanation instead of JSON", "Sorry, I cannot do that."),
    ("a fenced explanation", "```json\nSorry, no quiz.\n```"),
    ("a truncated object", '```json\n{"title": "A quiz",\n```'),
    ("single quotes", "```json\n{'title': 'A quiz'}\n```"),
    ("an empty answer", ""),
    ("an empty fence", "```json\n\n```"),
    ("nothing at all", None),
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
        """A watch URL with a short id survives unchanged."""
        url = "https://www.youtube.com/watch?v=example"
        self.assertEqual(normalize_youtube_url(url), url)

    def test_the_extracted_id_carries_no_decoration(self):
        """The id helper answers with the bare video id."""
        short_link = f"https://youtu.be/{VIDEO_ID}"
        self.assertEqual(extract_youtube_video_id(short_link), VIDEO_ID)

    def test_an_unusable_url_has_no_video_id(self):
        """The id helper answers None where the URL is not a video."""
        self.assertIsNone(extract_youtube_video_id("https://example.test"))


class ParseJsonResponseTests(SimpleTestCase):
    """Cover the shapes a model answer arrives in."""

    def test_wrapped_and_bare_forms_unpack_alike(self):
        """Every fenced form yields the same data as the bare one."""
        for label, text in WRAPPED_PAYLOADS:
            with self.subTest(form=label):
                self.assertEqual(parse_json_response(text), PAYLOAD)

    def test_a_list_at_the_top_level_survives(self):
        """The helper does not insist on an object."""
        self.assertEqual(parse_json_response("```json\n[1]\n```"), [1])

    def test_broken_json_raises_a_value_error(self):
        """Unusable content leaves as ValueError, not as a crash."""
        for label, text in BROKEN_PAYLOADS:
            with self.subTest(form=label):
                with self.assertRaises(ValueError):
                    parse_json_response(text)

    def test_text_without_a_fence_is_only_stripped(self):
        """A bare answer keeps its content and loses its padding."""
        self.assertEqual(strip_code_fences("  hello  "), "hello")

    def test_an_empty_answer_stays_empty(self):
        """Nothing at all is answered with an empty string."""
        self.assertEqual(strip_code_fences(""), "")

    def test_an_unclosed_fence_is_left_alone(self):
        """A fence without an end is not silently repaired."""
        text = '```json\n{"a": 1}'
        self.assertEqual(strip_code_fences(text), text)
