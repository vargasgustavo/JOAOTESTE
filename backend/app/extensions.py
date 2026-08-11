"""Extensoes compartilhadas: engine/sessao SQLAlchemy, Redis, rate limiter e Celery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

if TYPE_CHECKING:  # pragma: no cover
    from redis import Redis


class Database:
    """Wrapper minimo em volta do SQLAlchemy 2.x (sem Flask-SQLAlchemy)."""

    def __init__(self) -> None:
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None
        self.session: scoped_session[Session] | None = None

    def init_app(self, app: Flask) -> None:
        url = app.config["DATABASE_URL"]
        engine_options: dict[str, Any] = {"pool_pre_ping": True, "future": True}
        if url.startswith("postgresql"):
            engine_options.update(pool_size=10, max_overflow=20, pool_recycle=1800)
        self.engine = create_engine(url, **engine_options)
        self.session_factory = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False, future=True
        )
        self.session = scoped_session(self.session_factory)

        @app.teardown_appcontext
        def _remove_session(exception: BaseException | None = None) -> None:  # noqa: ARG001
            if self.session is not None:
                self.session.remove()

    @property
    def s(self) -> Session:
        """Sessao do escopo atual."""
        if self.session is None:
            raise RuntimeError("Database nao inicializado. Chame init_app primeiro.")
        return self.session()

    @property
    def dialect(self) -> str:
        if self.engine is None:
            raise RuntimeError("Database nao inicializado. Chame init_app primeiro.")
        return self.engine.dialect.name

    @property
    def supports_skip_locked(self) -> bool:
        return self.dialect == "postgresql"


db = Database()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    strategy="fixed-window",
    headers_enabled=True,
)

_redis_client: Redis | None = None


def init_redis(app: Flask) -> Redis | None:
    """Redis e opcional: sem ele o denylist cai para um cache em memoria do processo."""
    global _redis_client
    if app.config.get("TESTING") and not app.config.get("FORCE_REDIS"):
        _redis_client = None
        return None
    try:
        from redis import Redis as RedisClient

        client = RedisClient.from_url(app.config["REDIS_URL"], decode_responses=True)
        client.ping()
        _redis_client = client
    except Exception:  # pragma: no cover - ambiente sem Redis
        app.logger.warning("Redis indisponivel; usando denylist em memoria (apenas dev/teste).")
        _redis_client = None
    return _redis_client


def get_redis() -> Redis | None:
    return _redis_client
