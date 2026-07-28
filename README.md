# Quizly Backend

Django REST API for Quizly. It takes a YouTube URL, downloads the audio with
yt-dlp, extracts a WAV track with FFmpeg, transcribes it with Whisper and asks
Gemini Flash for a quiz of ten questions with four options each. The quiz is
stored per user and served over a small REST API.

This repository contains the backend only. The frontend is delivered
separately and is served as a static site.

## Project status

**All nine documented endpoints are implemented** — the four authentication
routes and the five quiz routes, including the whole generation pipeline from
a YouTube URL to a stored quiz.

In place besides them: environment-driven settings, DRF wired to cookie-based
JWT authentication, SimpleJWT with token blacklisting, CORS, the `Quiz` and
`Question` models with their migration, the Django admin with both models
editable, startup checks that warn about a missing FFmpeg or a missing Gemini
key, a [Postman collection](postman/Quizly.postman_collection.json) for every
endpoint, and a test suite that covers all of it without touching the network.

There is no tenth route. `PUT /api/quizzes/{id}/` answers `405`.

Every deliberate departure from the endpoint documentation, from the behaviour
of the delivered frontend or from the coding standards is written down in
[DEVIATIONS.md](DEVIATIONS.md).

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
depends on `WHISPER_MODEL`. See [Performance and limits](#performance-and-limits)
for what that costs in seconds.

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
| `GEMINI_MODEL` | no | `gemini-3.5-flash-lite` | Model asked for the quiz. The default is the lite variant on purpose; see [Known limitations](#known-limitations). The 2.x names are retired and answer `404`. |
| `COOKIE_SECURE` | no | `False` | `Secure` flag on both auth cookies. `True` only behind HTTPS. |
| `CORS_ALLOWED_ORIGINS` | no | `http://127.0.0.1:5500` | Comma-separated origins allowed to send credentials. No wildcard. |
| `WHISPER_MODEL` | no | `base` | Whisper model size: `tiny`, `base`, `small`, `medium` or `large`. `small` is the sensible step up in transcript quality and costs roughly three times the runtime of `base`. |

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
`coverage report` enforces a minimum total configured in
[pyproject.toml](pyproject.toml) and exits non-zero below it.

### Postman

A collection covering every documented endpoint lives at
[postman/Quizly.postman_collection.json](postman/Quizly.postman_collection.json).
Import it and run it from top to bottom: register, login, create a quiz, list,
retrieve, patch, delete, refresh, log out — with the documented `400`, `401`
and `404` cases sitting directly below the request they belong to.

The session is carried by the auth cookies out of Postman's own cookie jar, so
no request in the collection sends an `Authorization` header. `Register` gives
itself a fresh username, so the collection survives being run twice, and
`Create quiz` writes the id of the new quiz into the `quiz_id` collection
variable that retrieve, patch and delete read.

Set the `video_url` variable to a real, short, spoken-word video before running
it. Its default is the placeholder URL out of the endpoint documentation, which
passes URL validation and is then rejected with `400` because no such video
exists. `Create quiz` also needs FFmpeg and a `GEMINI_API_KEY`; the other
requests need neither.

## Performance and limits

`POST /api/quizzes/` does the whole chain inside the request, so the time it
takes is the time the client waits. These numbers were measured on an Apple
Silicon development machine with `WHISPER_MODEL=base`, on a **345 second**
video, with the model already in memory:

| Step | Time |
|---|---|
| Download (yt-dlp) | 1.2 s |
| Conversion (FFmpeg) | 0.5 s |
| Whisper model load (cached) | 0.3 s |
| Transcription | 8.5 s |
| **Total** | **10.5 s** |

That is roughly **33× realtime**. Two things are not in the table:

- **The first run in a fresh process costs about 4.3 s extra**, because the
  `base` model weights are downloaded before anything can be transcribed. After
  that the model stays in memory for the lifetime of the process.
- **The Gemini call is on top of it** and depends on the API, not on this
  machine.

### Why videos are capped at 30 minutes

`MAX_VIDEO_DURATION_SECONDS` is **1800**. The duration is read from the video
metadata *before* the download starts, and anything longer is rejected with
`400` and a message that names the limit.

The number is derived, not picked. At 33× realtime, 1800 seconds of video need
about **55 seconds** of local processing, plus the Gemini call. Chrome gives a
`fetch()` without an explicit timeout roughly **300 seconds** before it gives
up, and the delivered frontend sets no timeout of its own — so 300 seconds is
the whole budget for the request. 55 seconds inside a 300 second ceiling leaves
headroom for a machine about **three times slower** than the one measured on,
and still room for Gemini.

`FFMPEG_TIMEOUT_SECONDS` is **120** for the same reason: it has to be generous
enough for the slow machine and short enough that a hung FFmpeg cannot eat the
whole budget.

Raising `WHISPER_MODEL` to `small` roughly triples the transcription time, so
about 165 seconds for a 30 minute video on the reference machine. That still
fits, but not with much left over — lower `MAX_VIDEO_DURATION_SECONDS` along
with it if the deployment machine is slower.

### What else spends the same budget

Those two are not the whole request. Four constants share the 300 second
ceiling, and all four live in [quiz_app/constants.py](quiz_app/constants.py):

| Constant | Value | What it bounds |
|---|---|---|
| `MAX_VIDEO_DURATION_SECONDS` | `1800` | The video length accepted at all. Read from the metadata before the download, and answered with `400` above the limit. |
| `FFMPEG_TIMEOUT_SECONDS` | `120` | One FFmpeg run. A hung conversion is killed instead of waited out. |
| `GEMINI_TIMEOUT_MILLISECONDS` | `120_000` | One HTTP request to Gemini — one request, not one generation. |
| `GEMINI_RETRY_DELAY_SECONDS` | `2` | The pause before a Gemini that answered `429` or `503` is asked once more. |

The last two multiply. One generation can cost up to four Gemini requests: two
prompts, the quiz and the repair after an unusable answer, and each of them may
be sent a second time when the service says "not now". That is 4 × 120 s of
request timeout plus 2 × 2 s of pause, so **484 seconds** of Gemini on top of
the local work. A generation that goes normally costs a few seconds there — the
timeout bounds a connection that hangs, not an answer that arrives.

The two ends of the range are therefore far apart:

| Case | Local work | Gemini | Total |
|---|---|---|---|
| 30 minute video, everything answers | ~55 s | a few s | **~65 s** |
| 30 minute video, every timeout exhausted | ~55 s | 484 s | **~539 s** |

The normal case sits well inside the 300 second ceiling. The worst case does
not, and there the browser gives up before the server does: the client sees a
failed request instead of the `500` the server would have sent eventually.
Reaching it takes four Gemini requests in a row that neither answer nor refuse,
which is a hanging service rather than a busy one. Lowering
`GEMINI_TIMEOUT_MILLISECONDS` to about `60_000` would pull even that case under
the ceiling, at the price of cutting off a slow but working answer.

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
proportion to the video length and the Whisper model size. Videos longer than
`MAX_VIDEO_DURATION_SECONDS` are rejected with `400` rather than left to run
into a timeout; see [Performance and limits](#performance-and-limits) for the
measurements behind that number.

**A `503` comes from Google, not from this backend.** `GEMINI_MODEL` picks the
model that is asked, and its default is `gemini-3.5-flash-lite` rather than the
full `gemini-3.5-flash`. The full model answered `503 UNAVAILABLE` — "This
model is currently experiencing high demand" — on run after run, and the single
retry described below is built for a spike, not for sustained saturation. The
lite variant is under less contention and answers. Nothing about that status
code originates here: it is the Gemini API refusing the request, and no setting
in this project makes a saturated model available. Set `GEMINI_MODEL` in `.env`
to ask for a different one.

**A busy Gemini is asked once more, and then gives up.** The API answers `503`
when the model is under load and `429` when the quota is momentarily
exhausted. Both are retried a single time after a short pause. Everything else
is final — a refused key or a rejected request fails the same way on the
second ask, and retrying it would only add latency to a request the client is
already waiting on. If the second attempt fails too, `POST /api/quizzes/`
answers `500`, and it does so *after* the download, the conversion and the
transcription have already run: the client waits for the whole pipeline before
learning that the last step failed, and a retry repeats all of that work. The
real cause is in the log — the delivered frontend shows only "Error generating
quiz".

**A video without speech is rejected with `400`, not `500`.** Whisper returns
an empty transcript for a silent or music-only video. That is a property of
the URL the client sent, not a broken tool chain, so it is answered like an
unusable video rather than like a server fault.

**A logout without a usable refresh cookie still logs you out.**
`POST /api/logout/` needs a valid access token, but it answers `200` and
clears both cookies even when the refresh cookie is missing, damaged or
already blacklisted. There is nothing left to invalidate in that case, and a
user who asks to be logged out should end up logged out rather than stuck in
a session that cannot be ended.

**The Whisper model stays in memory.** The first transcription in a server
process loads the model named by `WHISPER_MODEL` — `base` by default — and
keeps it there for every request after it. Loading it per request would add
several seconds to every quiz, so this is deliberate. The price is resident
memory for the lifetime of the process: `base` holds 74 million parameters,
which is roughly 300 MB as the 32-bit floats it is loaded as on a CPU. Each
larger size multiplies that, `small` by about three and `medium` by about
ten. Restart the server to release it.

**Game progress is not stored.** The backend keeps quizzes and questions.
How far a user got through a quiz lives in the frontend only, and is gone on
reload.

**Registration does not check password strength.** Neither the endpoint
documentation nor the project checklist asks for one, so `POST /api/register/`
accepts any non-empty password and does not run Django's
`AUTH_PASSWORD_VALIDATORS`. The validators stay configured and still apply
where Django runs them itself, namely `createsuperuser` and the password
forms in the admin.

**A registration error reads `undefined` in the delivered frontend.** That
frontend renders only `data.username` from a `400`, so a rejected email or a
password mismatch produces a toast saying `undefined`. The response body does
carry the real message, under the `email` or `confirmed_password` key. This
is a frontend limitation and is not worked around in the backend.
