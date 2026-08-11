"""Fixtures compartilhadas. Roda em SQLite por padrao e em PostgreSQL se TEST_DATABASE_URL."""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import Base, QueueEntry, QueueStatus, Restaurant, Role, Table, TableStatus, User
from app.security import hash_password
from app.security.tokens import reset_memory_denylist
from app.services.providers import get_provider, reset_providers

ADMIN_PASSWORD = "SenhaAdmin12345"
STAFF_PASSWORD = "SenhaStaff12345"
CUSTOMER_PASSWORD = "SenhaCliente12345"


def _database_url() -> tuple[str, str | None]:
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        return url, None
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    return f"sqlite:///{handle.name}", handle.name


def _make_app(**overrides: Any) -> tuple[Flask, str | None]:
    url, temp_path = _database_url()
    config: dict[str, Any] = {
        "TESTING": True,
        "ENV": "test",
        "DATABASE_URL": url,
        "SECRET_KEY": "test-secret-key-not-used-in-production",
        "JWT_SECRET_KEY": "test-jwt-secret-key-not-used-in-production",
        "COOKIE_SECURE": False,
        "RATELIMIT_ENABLED": False,
        "SENTRY_DSN": None,
    }
    config.update(overrides)
    return create_app(config), temp_path


@pytest.fixture
def app() -> Iterator[Flask]:
    application, temp_path = _make_app()
    with application.app_context():
        Base.metadata.drop_all(db.engine)
        Base.metadata.create_all(db.engine)
        reset_memory_denylist()
        reset_providers()
        yield application
        db.session.remove()
        Base.metadata.drop_all(db.engine)
        db.engine.dispose()
    if temp_path and os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def rate_limited_app() -> Iterator[Flask]:
    application, temp_path = _make_app(RATELIMIT_ENABLED=True, RATELIMIT_AUTH="3 per minute")
    with application.app_context():
        Base.metadata.drop_all(db.engine)
        Base.metadata.create_all(db.engine)
        reset_memory_denylist()
        yield application
        db.session.remove()
        Base.metadata.drop_all(db.engine)
        db.engine.dispose()
    if temp_path and os.path.exists(temp_path):
        os.unlink(temp_path)


class ApiClient:
    """Cliente de teste que cuida do CSRF double-submit automaticamente."""

    def __init__(self, client: FlaskClient) -> None:
        self.client = client
        self.csrf_token: str | None = None

    def ensure_csrf(self) -> str:
        response = self.client.get("/auth/csrf")
        assert response.status_code == 200
        self.csrf_token = response.get_json()["csrf_token"]
        return self.csrf_token

    def _cookie_token(self) -> str | None:
        cookie = self.client.get_cookie("csrf_token")
        return cookie.value if cookie else None

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        # Como no browser: o valor enviado no header vem sempre do cookie atual.
        token = self._cookie_token() or self.ensure_csrf()
        self.csrf_token = token
        headers = {"X-CSRF-Token": token}
        if extra:
            headers.update(extra)
        return headers

    def get(self, url: str, **kwargs: Any):
        return self.client.get(url, **kwargs)

    def post(self, url: str, json: Any = None, csrf: bool = True, **kwargs: Any):
        headers = self._headers(kwargs.pop("headers", None)) if csrf else kwargs.pop("headers", {})
        return self.client.post(url, json=json, headers=headers, **kwargs)

    def put(self, url: str, json: Any = None, csrf: bool = True, **kwargs: Any):
        headers = self._headers(kwargs.pop("headers", None)) if csrf else kwargs.pop("headers", {})
        return self.client.put(url, json=json, headers=headers, **kwargs)

    def login(self, email: str, password: str):
        response = self.post("/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.get_json()
        self.csrf_token = self._cookie_token()
        return response

    def logout(self):
        return self.post("/auth/logout")


@pytest.fixture
def api(app: Flask) -> ApiClient:
    return ApiClient(app.test_client())


@pytest.fixture
def restaurant(app: Flask) -> Restaurant:
    entity = Restaurant(
        name="Cantina Teste",
        address="Rua Teste, 100",
        phone="+551133334444",
        opening_hours={"mon": {"open": "11:00", "close": "23:00"}},
        is_active=True,
    )
    db.s.add(entity)
    db.s.commit()
    return entity


@pytest.fixture
def other_restaurant(app: Flask) -> Restaurant:
    entity = Restaurant(
        name="Concorrente Teste",
        address="Rua Outra, 200",
        phone="+551133335555",
        opening_hours={},
        is_active=True,
    )
    db.s.add(entity)
    db.s.commit()
    return entity


def make_user(
    email: str, role: Role, restaurant_id: uuid.UUID | None, password: str
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=f"Usuario {role.value}",
        role=role,
        restaurant_id=restaurant_id,
    )
    db.s.add(user)
    db.s.commit()
    return user


@pytest.fixture
def admin(restaurant: Restaurant) -> User:
    return make_user("admin@teste.com", Role.RESTAURANT_ADMIN, restaurant.id, ADMIN_PASSWORD)


@pytest.fixture
def staff(restaurant: Restaurant) -> User:
    return make_user("staff@teste.com", Role.STAFF, restaurant.id, STAFF_PASSWORD)


@pytest.fixture
def customer(app: Flask) -> User:
    return make_user("cliente@teste.com", Role.CUSTOMER, None, CUSTOMER_PASSWORD)


def make_table(
    restaurant_id: uuid.UUID,
    number: str,
    capacity: int,
    status: TableStatus = TableStatus.OCCUPIED,
) -> Table:
    table = Table(
        restaurant_id=restaurant_id,
        number=number,
        capacity=capacity,
        status=status,
        pos_x=0,
        pos_y=0,
    )
    db.s.add(table)
    db.s.commit()
    return table


def make_queue_entry(
    restaurant_id: uuid.UUID,
    name: str,
    phone: str,
    party_size: int,
    position: int,
    status: QueueStatus = QueueStatus.WAITING,
) -> QueueEntry:
    from datetime import timedelta

    from app.models import utcnow

    entry = QueueEntry(
        restaurant_id=restaurant_id,
        customer_name=name,
        customer_phone=phone,
        party_size=party_size,
        status=status,
        position=position,
        # joined_at crescente garante um FIFO deterministico nos testes.
        joined_at=utcnow() + timedelta(seconds=position),
    )
    db.s.add(entry)
    db.s.commit()
    return entry


@pytest.fixture
def mock_provider():
    return get_provider("mock")
