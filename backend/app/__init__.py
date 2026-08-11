"""Application factory: composicao de config, extensoes, seguranca e rotas."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import Settings, build_settings
from app.controllers import register_blueprints
from app.errors import AppError, RateLimitError
from app.extensions import db, init_redis, limiter
from app.logging_utils import configure_logging
from app.security import SAFE_METHODS, enforce_csrf, register_security_headers
from app.tasks.celery_app import init_celery

CSRF_EXEMPT_ENDPOINTS: frozenset[str] = frozenset()


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    settings = build_settings(overrides)
    settings.validate_runtime()

    app = Flask(__name__)
    _apply_config(app, settings)
    configure_logging(settings.LOG_LEVEL)
    _init_sentry(settings)

    db.init_app(app)
    init_redis(app)
    limiter.init_app(app)
    register_security_headers(app)
    _init_cors(app, settings)
    _register_request_scope(app)
    _register_csrf_guard(app)
    _register_error_handlers(app)
    register_blueprints(app)
    init_celery(app)
    return app


def _apply_config(app: Flask, settings: Settings) -> None:
    app.config.update(settings.model_dump())
    app.config["CELERY_BROKER_URL"] = settings.celery_broker
    app.config["CELERY_RESULT_BACKEND"] = settings.celery_backend
    app.config["CELERY_TASK_ALWAYS_EAGER"] = settings.TESTING
    app.config["RATELIMIT_ENABLED"] = settings.RATELIMIT_ENABLED
    app.config["RATELIMIT_DEFAULT"] = settings.RATELIMIT_DEFAULT
    app.config["RATELIMIT_HEADERS_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = (
        "memory://" if settings.TESTING else settings.REDIS_URL
    )
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 256 * 1024
    app.config["PROPAGATE_EXCEPTIONS"] = False
    # Nao expor a versao do servidor nem confiar em proxies desconhecidos.
    app.config["TRUSTED_HOSTS"] = None


def _init_sentry(settings: Settings) -> None:
    if not settings.SENTRY_DSN:
        return
    try:  # pragma: no cover - depende de rede
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
    except Exception:  # pragma: no cover
        logging.getLogger(__name__).warning("Sentry indisponivel; seguindo sem monitoramento.")


def _init_cors(app: Flask, settings: Settings) -> None:
    CORS(
        app,
        resources={r"/*": {"origins": settings.cors_origin_list}},
        supports_credentials=True,
        allow_headers=["Content-Type", "X-CSRF-Token"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        max_age=600,
    )


def _register_request_scope(app: Flask) -> None:
    """A identidade e SEMPRE recalculada por request.

    O Flask reaproveita um app context externo (ex.: testes/CLI), e nesse caso `g`
    sobreviveria entre requisicoes — o que faria um token revogado continuar valendo.
    """

    @app.before_request
    def _reset_identity() -> None:
        g.pop("current_user", None)
        g.pop("token_claims", None)


def _register_csrf_guard(app: Flask) -> None:
    @app.before_request
    def _csrf() -> None:
        if request.method in SAFE_METHODS:
            return
        if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
            return
        enforce_csrf()


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _app_error(exc: AppError) -> tuple[Response, int]:
        if exc.status_code >= 500:  # pragma: no cover
            app.logger.error("Erro de aplicacao: %s", exc.message)
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(429)
    def _rate_limited(exc: HTTPException) -> tuple[Response, int]:  # noqa: ARG001
        error = RateLimitError("Muitas requisicoes. Tente novamente em instantes.")
        return jsonify(error.to_dict()), 429

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException) -> tuple[Response, int]:
        return (
            jsonify({"error": exc.name.lower().replace(" ", "_"), "message": exc.description}),
            exc.code or 500,
        )

    @app.errorhandler(Exception)
    def _unhandled(exc: Exception) -> tuple[Response, int]:
        app.logger.exception("Erro nao tratado: %s", type(exc).__name__)
        # Nunca vazar stack trace/detalhes internos para o cliente.
        return jsonify({"error": "internal_error", "message": "Erro interno."}), 500


__all__ = ["create_app"]
