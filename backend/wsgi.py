"""Entrypoint WSGI (gunicorn: wsgi:app)."""

from __future__ import annotations

from dotenv import load_dotenv

from app import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":  # pragma: no cover
    app.run(host="127.0.0.1", port=8000)
