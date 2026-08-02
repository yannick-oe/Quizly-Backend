# Quizly Backend

Django REST API for Quizly. It takes a YouTube URL, downloads the audio with
yt-dlp, converts it to WAV with FFmpeg, transcribes it with Whisper and asks
Gemini for a quiz of ten questions with four options each; quizzes are stored
per user. This repository contains the backend only — the frontend is
delivered separately as a static site.

## Requirements

- **Python 3.12**
- **FFmpeg**, available on `PATH`

Install FFmpeg:

| Platform | Command |
|---|---|
| macOS (Homebrew) | `brew install ffmpeg` |
| Debian / Ubuntu | `sudo apt update && sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Windows (winget) | `winget install Gyan.FFmpeg` |
| Windows (Chocolatey) | `choco install ffmpeg` |

Verify the installation:

```bash
ffmpeg -version
```

The first quiz generation downloads the Whisper model weights, which needs a
working internet connection and some disk space.

## Setup

```bash
git clone <repository-url>
cd Quizly-Backend

python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# put the printed key into .env as SECRET_KEY

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

A missing or empty `SECRET_KEY` aborts the start with `ImproperlyConfigured`.

## Environment variables

All of them are read from `.env`; see `.env.example` for a copy with
placeholders. `.env` itself is ignored by git and must never be committed.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | yes | none | Django signing key. The start fails without it. |
| `DEBUG` | no | `False` | Django debug mode. `True` for local development only. |
| `ALLOWED_HOSTS` | no | `127.0.0.1,localhost` | Comma-separated hosts Django will serve. |
| `GEMINI_API_KEY` | for quiz generation | none | Google AI Studio key for Gemini Flash. |
| `GEMINI_MODEL` | no | `gemini-3.5-flash-lite` | Gemini model asked for the quiz. The 2.x names are retired and answer `404`. |
| `COOKIE_SECURE` | no | `False` | `Secure` flag on both auth cookies. `True` only behind HTTPS. |
| `CORS_ALLOWED_ORIGINS` | no | `http://127.0.0.1:5500` | Comma-separated origins allowed to send credentials. No wildcard. |
| `WHISPER_MODEL` | no | `base` | Whisper model size: `tiny`, `base`, `small`, `medium` or `large`. |

Boolean variables accept `1`, `true`, `yes` or `on`, case-insensitive.
Anything else counts as false.

## API

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

`GET /api/quizzes/` returns a bare array — the list is not paginated — and
there is no `PUT`.

### Authentication

JWT, carried exclusively in HttpOnly cookies — no token in any response body,
no `Authorization` header.

- Cookies: `access_token` and `refresh_token`
- Flags: `HttpOnly` always, `SameSite=Lax`, `Secure` controlled by
  `COOKIE_SECURE`
- Refresh tokens rotate on use, and the previous one is blacklisted
- Logout invalidates the refresh token server-side

The API has no CSRF protection; `SameSite=Lax` on both auth cookies and the
explicit `CORS_ALLOWED_ORIGINS` list are the countermeasures. The Django
admin keeps its own CSRF protection.

Every deliberate deviation from the endpoint documentation is recorded in
[DEVIATIONS.md](DEVIATIONS.md), one dated entry each.

## Admin

The admin at `http://127.0.0.1:8000/admin/` needs a superuser, created with
`python manage.py createsuperuser`. Quizzes and questions are both editable:
a quiz's questions sit inline on its page, and questions are also registered
on their own.

Two rules are enforced at generation time only, and the admin does not check
them:

- `question_options` holds exactly four distinct entries; the frontend has no
  label for a fifth.
- `answer` is character-for-character one of those four options; a stray
  leading space silently marks every answer to that question wrong.

## Development

```bash
black .
flake8 .
python manage.py test
coverage run manage.py test && coverage report
```

The tooling is configured in [pyproject.toml](pyproject.toml) and
[.flake8](.flake8), with migrations excluded. The test suite mocks yt-dlp,
Whisper and Gemini and runs without network access, an API key or a model
download.

### Logging

The project logs to the console only; no log file is written. Every record
carries a timestamp, its level, the logger name and the message. The cause of
a `500` from `POST /api/quizzes/` — the pipeline step that failed — appears
here and nowhere else.

### Postman

A collection covering every endpoint lives at
[postman/Quizly.postman_collection.json](postman/Quizly.postman_collection.json).
Import it and run it from top to bottom. `Create quiz` needs FFmpeg and a
`GEMINI_API_KEY`; the other requests need neither. The collection variable
`video_url` points at a specific YouTube video; if that video is gone,
replace the value with any short spoken-word `watch?v=` URL.

## Performance

Measured on an Apple Silicon development machine with `WHISPER_MODEL=base`,
on a 345 second video, with the model already in memory:

| Step | Time |
|---|---|
| Download (yt-dlp) | 1.2 s |
| Conversion (FFmpeg) | 0.5 s |
| Whisper model load (cached) | 0.3 s |
| Transcription | 8.5 s |
| **Total** | **10.5 s** |

Quiz generation is synchronous — the client waits for the whole pipeline
inside `POST /api/quizzes/`. Videos longer than `MAX_VIDEO_DURATION_SECONDS`
(1800 seconds) are rejected with `400`.

## Known limitations

- **Open the frontend at `http://127.0.0.1:5500`, not at
  `http://localhost:5500`.** Served from `localhost`, every API request is
  cross-site, the browser drops the `SameSite=Lax` cookies, and each request
  after the login answers `401`.
- **`COOKIE_SECURE=True` over plain HTTP fails the same way.** The browser
  discards a `Secure` cookie on an insecure connection; keep the flag `False`
  for local development.
- **A `403` logs the user out of the delivered frontend.** The frontend
  treats `401` and `403` identically, and a quiz that belongs to somebody
  else answers `403` as the endpoint documentation requires.
- **Quiz generation is synchronous.** `POST /api/quizzes/` downloads,
  transcribes and generates inside the request; the duration grows with the
  video length and the Whisper model size.
- **A `503` comes from Gemini, not from this backend.** The default
  `GEMINI_MODEL` is `gemini-3.5-flash-lite`; set the variable in `.env` to
  ask for a different model.
- **A busy Gemini is asked once more, then the request fails.** A `429` or
  `503` is retried once after a short pause; a second failure answers `500`,
  after download, conversion and transcription have already run.
- **A video without speech answers `400`.** Whisper returns an empty
  transcript for a silent or music-only video, which counts as a property of
  the input, not as a server fault.
- **Logout works without a usable refresh cookie.** `POST /api/logout/`
  needs a valid access token, but it answers `200` and clears both cookies
  even when the refresh cookie is missing, damaged or already blacklisted.
- **The Whisper model stays resident.** The first transcription loads the
  model named by `WHISPER_MODEL` and keeps it in memory for the lifetime of
  the process; restarting the server releases it.
- **Game progress is not stored.** The backend keeps quizzes and questions;
  how far a user got through a quiz lives in the frontend only.
- **Registration does not check password strength.** `POST /api/register/`
  accepts any non-empty password; Django's configured validators still apply
  where Django itself runs them, in `createsuperuser` and the admin.
- **A registration error renders as `undefined` in the delivered frontend.**
  That frontend reads only `data.username` from a `400`; the real message
  sits under the `email` or `confirmed_password` key.
