"""Service layer of the quiz_app app.

The modules here own the flow of quiz generation and every external
effect it has: the YouTube lookup, the download, the FFmpeg call, the
transcription, the Gemini call and the write to the database.

generation.py is the only one that knows the order of those steps.
Every other module does one of them and nothing else, which is what
makes each of them replaceable on its own in a test.

None of them knows about HTTP. Every failure leaves as one of the
exceptions in exceptions.py, and the API layer is what maps those onto
status codes.
"""
