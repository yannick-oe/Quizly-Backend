# Quizly Backend

Django REST API for Quizly. It takes a YouTube URL, downloads the audio with
yt-dlp, extracts a WAV track with FFmpeg, transcribes it with Whisper and asks
Gemini Flash for a quiz of ten questions with four options each. The quiz is
stored per user and served over a small REST API.

This repository contains the backend only. The frontend is delivered
separately and is served as a static site.

## Project status

In place: environment-driven settings, DRF wired to cookie-based JWT
authentication, SimpleJWT with token blacklisting, CORS, the `Quiz` and
`Question` models with their migration, the Django admin, and the first two
endpoints — `POST /api/register/` and `POST /api/login/`.

**Not implemented yet:** `POST /api/logout/`, `POST /api/token/refresh/` and
the five quiz endpoints. Their rows in the endpoint table below describe the
contract this backend is being built against, not what it answers today.

## Requirements

- **Python 3.12** (developed against 3.12.13)
- **FFmpeg**, available on `PATH`. Whisper shells out to it, and without it
  quiz generation fails at the audio step with a 500.

Install FFmpeg:

| Platform | Command |
|---|---|
| macOS (Homebrew) | `brew install ffmpeg` |
| Debian / Ubuntu | `sudo apt update && sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Windows (winget) | `winget install Gyan.FFmpeg` |
| Windows (Chocolatey) | `choco install ffmpeg` |

Verify the installation before starting the server:

```bash
ffmpeg -version
```

The first quiz generation additionally downloads the Whisper model weights,
which needs a working internet connection and some disk space. The size
depends on `WHISPER_MODEL`.

## Setup

```bash
git clone <repository-url>
cd Quizly-Backend

python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
```

Generate a `SECRET_KEY` and put it into `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

A missing or empty `SECRET_KEY` aborts the start with
`ImproperlyConfigured: Environment variable SECRET_KEY is missing or empty.`
That is deliberate — there is no insecure fallback key.

Then migrate and run:

```bash
python manage.py migrate
python manage.py createsuperuser    # required for the admin, see below
python manage.py runserver
```

The server listens on `http://127.0.0.1:8000/`, the admin lives at
`http://127.0.0.1:8000/admin/`.

## Environment variables

All of them are read from `.env`; see `.env.example` for a copy with
placeholders. `.env` itself is ignored by git and must never be committed.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | yes | none | Django signing key. The start fails without it. |
| `DEBUG` | no | `False` | Django debug mode. `True` for local development only. |
| `ALLOWED_HOSTS` | no | `127.0.0.1,localhost` | Comma-separated hosts Django will serve. |
| `GEMINI_API_KEY` | for quiz generation | none | Google AI Studio key for Gemini Flash. |
| `COOKIE_SECURE` | no | `False` | `Secure` flag on both auth cookies. `True` only behind HTTPS. |
| `CORS_ALLOWED_ORIGINS` | no | `http://127.0.0.1:5500` | Comma-separated origins allowed to send credentials. No wildcard. |
| `WHISPER_MODEL` | no | `base` | Whisper model size: `tiny`, `base`, `small`, `medium` or `large`. Larger is slower and needs more memory. |

Boolean variables accept `1`, `true`, `yes` or `on`, case-insensitive.
Anything else counts as false.

## API

Base URL: `http://127.0.0.1:8000/api/`

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/register/` | Create an account |
| `POST` | `/api/login/` | Log in, sets both auth cookies |
| `POST` | `/api/logout/` | Log out, blacklists the refresh token |
| `POST` | `/api/token/refresh/` | Issue a new access token from the refresh cookie |
| `POST` | `/api/quizzes/` | Generate a quiz from a YouTube URL |
| `GET` | `/api/quizzes/` | List the quizzes of the current user |
| `GET` | `/api/quizzes/{id}/` | Retrieve one quiz |
| `PATCH` | `/api/quizzes/{id}/` | Update title and description |
| `DELETE` | `/api/quizzes/{id}/` | Delete a quiz |

There is no `PUT`, and `GET /api/quizzes/` returns a bare array — the list is
not paginated.

### Authentication

JWT, carried **exclusively in HttpOnly cookies**. There is no token in any
response body and no `Authorization` header anywhere. Clients only need to
send their requests with credentials included; the browser attaches the
cookies.

- Cookies: `access_token` and `refresh_token`
- Flags: `HttpOnly` always, `SameSite=Lax`, `Secure` controlled by
  `COOKIE_SECURE`
- Refresh tokens rotate on use, and the previous one is blacklisted
- Logout invalidates the refresh token server-side

The API has no CSRF protection. That is a deliberate decision, not an
oversight; `SameSite=Lax` and an explicit `CORS_ALLOWED_ORIGINS` list are the
countermeasures. The reasoning and the way back are recorded in
[DEVIATIONS.md](DEVIATIONS.md). The Django admin keeps its CSRF protection.

## Admin

The Django admin is part of the deliverable, not an afterthought. It lives at
`http://127.0.0.1:8000/admin/` and needs a superuser, so
`python manage.py createsuperuser` is a required setup step rather than an
optional one:

```bash
python manage.py createsuperuser
```

What is editable there:

| Entry | What you can edit |
|---|---|
| **Quizzes** | Title, description, video URL and owner. The quiz's questions are edited inline on the same page. |
| **Questions** | Registered separately as well, so a single question can be found and edited without opening its quiz. |

Both lists are searchable and filterable; `created_at` and `updated_at` are
read-only on both.

Two rules the admin does not enforce, because they are enforced when a quiz is
generated rather than on the model:

- `question_options` holds exactly **four distinct** entries. The frontend
  labels them A to D and has no label for a fifth.
- `answer` is **character-for-character** one of those four options. The
  frontend compares the option text it read back from the page against
  `answer` with a strict equality check, so a stray leading space marks every
  answer to that question wrong, silently and without an error.

## Development

```bash
black .                                    # format, line length 79
flake8 .                                   # lint
python manage.py test                      # test suite
coverage run manage.py test && coverage report
```

`black` and `flake8` are configured in [pyproject.toml](pyproject.toml) and
[.flake8](.flake8). Both run before every commit. Generated migrations are
excluded from formatting and from the length and docstring checks.

The test suite mocks yt-dlp, Whisper and Gemini. It runs without network
access, without an API key and without downloading model weights.

## Known limitations

**Open the frontend at `http://127.0.0.1:5500`, not at
`http://localhost:5500`.** `localhost` and `127.0.0.1` are different hosts to
the browser. Served from `localhost`, every API request counts as cross-site,
the browser drops the `SameSite=Lax` auth cookies, and login reports success
while every request after it comes back as `401`. It looks like a backend bug
and is not one. If the frontend runs on a different port, add that exact
origin to `CORS_ALLOWED_ORIGINS`.

**`COOKIE_SECURE=True` over plain HTTP has the same effect.** The browser
discards a `Secure` cookie on an insecure connection without any warning.
Keep it `False` for local development.

**A `403` logs the user out of the delivered frontend.** The frontend treats
`401` and `403` identically: try a refresh, otherwise redirect to the login
page. Requesting a quiz that belongs to somebody else answers `403` as the
endpoint documentation requires, so the frontend logs the user out instead of
showing a message. The reasoning is in [DEVIATIONS.md](DEVIATIONS.md).

**Quiz generation is synchronous.** `POST /api/quizzes/` downloads,
transcribes and generates within the request, because the documented response
is the finished quiz. Expect the request to take a while, roughly in
proportion to the video length and the Whisper model size. Videos above a
configured maximum length are rejected with `400` rather than left to run into
a timeout.

**Game progress is not stored.** The backend keeps quizzes and questions.
How far a user got through a quiz lives in the frontend only, and is gone on
reload.
