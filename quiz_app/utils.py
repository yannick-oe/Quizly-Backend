"""Stateless helpers for the quiz_app app."""

import json
import re
from urllib.parse import parse_qs, urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

WATCH_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }
)

SHORT_LINK_HOSTS = frozenset({"youtu.be", "www.youtu.be"})

WATCH_PATH_SEGMENT = "watch"

PATH_ID_SEGMENTS = frozenset({"shorts", "embed", "live", "v"})

VIDEO_ID_QUERY_KEY = "v"

VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")

WATCH_URL_TEMPLATE = "https://www.youtube.com/watch?v={video_id}"

CODE_FENCE_PATTERN = re.compile(
    r"\A```[ \t]*[A-Za-z0-9_+-]*[ \t]*\r?\n?"
    r"(?P<body>.*?)"
    r"\r?\n?[ \t]*```\Z",
    re.DOTALL,
)

FENCE_BODY_GROUP = "body"


def strip_code_fences(text):
    """Return a model answer without its Markdown code fence."""
    stripped = (text or "").strip()
    match = CODE_FENCE_PATTERN.match(stripped)
    if match is None:
        return stripped
    return match.group(FENCE_BODY_GROUP).strip()


def parse_json_response(text):
    """Return the data a fenced or bare JSON answer carries."""
    return json.loads(strip_code_fences(text))


def normalize_youtube_url(url):
    """Return the canonical watch URL of a YouTube link, or None."""
    video_id = extract_youtube_video_id(url)
    if video_id is None:
        return None
    return WATCH_URL_TEMPLATE.format(video_id=video_id)


def extract_youtube_video_id(url):
    """Return the video id a YouTube link carries, else None."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ALLOWED_SCHEMES:
        return None
    host = parts.hostname or ""
    if host in SHORT_LINK_HOSTS:
        return _checked_video_id(_first_path_segment(parts.path))
    if host in WATCH_HOSTS:
        return _checked_video_id(_watch_video_id(parts))
    return None


def _watch_video_id(parts):
    """Return the id a watch, shorts, embed or live URL carries."""
    segments = _path_segments(parts.path)
    if not segments:
        return None
    if segments[0] == WATCH_PATH_SEGMENT:
        return _first_query_value(parts.query, VIDEO_ID_QUERY_KEY)
    if segments[0] in PATH_ID_SEGMENTS and len(segments) > 1:
        return segments[1]
    return None


def _path_segments(path):
    """Return the non-empty segments of a URL path."""
    return [segment for segment in path.split("/") if segment]


def _first_path_segment(path):
    """Return the first non-empty segment of a path, else None."""
    segments = _path_segments(path)
    if not segments:
        return None
    return segments[0]


def _first_query_value(query, key):
    """Return the first value a query string holds for a key."""
    values = parse_qs(query).get(key, [])
    if not values:
        return None
    return values[0]


def _checked_video_id(candidate):
    """Return a candidate id when it looks like one, else None."""
    if not candidate or not VIDEO_ID_PATTERN.match(candidate):
        return None
    return candidate
