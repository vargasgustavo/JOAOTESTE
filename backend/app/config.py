import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "true").lower() == "true"
    JWT_COOKIE_SAMESITE = "Strict"
    JWT_COOKIE_HTTPONLY = True

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STRATEGY = "fixed-window"

    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

    ARGON2_TIME_COST = int(os.environ.get("ARGON2_TIME_COST", "3"))
    ARGON2_MEMORY_COST = int(os.environ.get("ARGON2_MEMORY_COST", "65536"))
    ARGON2_PARALLELISM = int(os.environ.get("ARGON2_PARALLELISM", "1"))

    CSRF_COOKIE_NAME = "csrf_token"
    CSRF_HEADER_NAME = "X-CSRF-Token"


class DevelopmentConfig(Config):
    DEBUG = True
    JWT_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    JWT_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key-change-me"
    JWT_SECRET_KEY = "test-jwt-secret-key-change-me"


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        for key in ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL"):
            import os as _os
            if not _os.environ.get(key):
                raise RuntimeError(f"{key} must be set in production")


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
