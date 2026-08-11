"""Instancia Celery com contexto Flask (worker compartilha config e sessao do app)."""

from __future__ import annotations

from celery import Celery, Task
from flask import Flask

celery_app = Celery("mesas_filas")


def init_celery(app: Flask) -> Celery:
    eager = app.config.get("CELERY_TASK_ALWAYS_EAGER", False)
    # Publicacao "fail fast": se o broker estiver fora, a acao do staff nao pode
    # ficar presa em retentativas de rede. A notificacao fica PENDING e e logada.
    fail_fast = {
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
        "retry_policy": {"max_retries": 1, "interval_start": 0, "interval_max": 0.5, "timeout": 3},
    }
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
        task_always_eager=eager,
        task_eager_propagates=eager,
        task_ignore_result=True,
        task_publish_retry=False,
        broker_connection_retry_on_startup=False,
        broker_connection_max_retries=1,
        broker_transport_options=fail_fast,
        result_backend_transport_options=fail_fast,
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
