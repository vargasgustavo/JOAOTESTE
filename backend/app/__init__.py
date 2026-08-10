import os
import secrets
import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration

from .config import config_map
from .extensions import db, migrate, cors, limiter, celery


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    cfg = config_map.get(config_name, config_map["development"])
    app.config.from_object(cfg)

    _init_sentry(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)

    return app


def _init_sentry(app: Flask) -> None:
    dsn = app.config.get("SENTRY_DSN", "")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )


def _init_extensions(app: Flask) -> Flask:
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_URL"]}},
        supports_credentials=True,
    )

    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    celery.conf.update(app.config)

    @app.after_request
    def set_csrf_cookie(response):
        if not app.config.get("TESTING"):
            if "csrf_token" not in app.cookies_to_set if hasattr(app, "cookies_to_set") else True:
                csrf_val = secrets.token_hex(32)
                response.set_cookie(
                    app.config["CSRF_COOKIE_NAME"],
                    csrf_val,
                    httponly=False,
                    secure=app.config.get("JWT_COOKIE_SECURE", True),
                    samesite="Strict",
                    max_age=3600,
                )
        return response

    return app


def _register_blueprints(app: Flask) -> None:
    from .controllers.auth_controller import auth_bp
    from .controllers.restaurant_controller import restaurant_bp
    from .controllers.table_controller import table_bp
    from .controllers.queue_controller import queue_bp
    from .controllers.dashboard_controller import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(restaurant_bp, url_prefix="/api/restaurants")
    app.register_blueprint(table_bp, url_prefix="/api")
    app.register_blueprint(queue_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api/restaurants")


def _register_error_handlers(app: Flask) -> None:
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": "Conflict", "message": str(e)}), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "Validation error", "message": str(e)}), 422

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"error": "Too many requests", "message": str(e)}), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500
