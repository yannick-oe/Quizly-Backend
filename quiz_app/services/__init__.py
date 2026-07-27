"""Service layer of the quiz_app app.

The modules here own the flow of quiz generation and every external
effect it has: the YouTube lookup, the download, the FFmpeg call and
the transcription.

None of them knows about HTTP. Every failure leaves as one of the
exceptions in exceptions.py, and the API layer is what maps those onto
status codes.
"""
