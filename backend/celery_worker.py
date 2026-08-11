"""Entrypoint do worker Celery: celery -A celery_worker.celery worker."""

from __future__ import annotations

from dotenv import load_dotenv

from app import create_app
from app.tasks import celery_app as celery
from app.tasks import notifications  # noqa: F401 - registra as tasks

load_dotenv()

flask_app = create_app()
celery.set_default()

__all__ = ["celery", "flask_app"]
