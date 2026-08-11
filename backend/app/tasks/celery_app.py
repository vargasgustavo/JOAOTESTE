"""Instancia Celery com contexto Flask (worker compartilha config e sessao do app)."""

from __future__ import annotations

from celery import Celery, Task
from flask import Flask

celery_app = Celery("mesas_filas")


def init_celery(app: Flask) -> Celery:
    celery_app.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        task_eager_propagates=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        broker_connection_retry_on_startup=True,
    )

    class FlaskTask(Task):
        abstract = True

        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
