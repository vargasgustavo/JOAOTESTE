import os
import pytest
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-length-32")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32ch")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_MEMORY_COST", "8192")
os.environ.setdefault("ARGON2_PARALLELISM", "1")


@pytest.fixture(scope="session")
def app():
    from app import create_app
    application = create_app("testing")
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    application.config["RATELIMIT_ENABLED"] = False
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    return application


@pytest.fixture(scope="session")
def db(app):
    from app.extensions import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_db(db):
    yield
    db.session.rollback()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def restaurant(db, app):
    from app.models import Restaurant
    with app.app_context():
        r = Restaurant(
            name="Test Restaurant",
            address="Rua Teste, 1",
            phone="11000000000",
            is_active=True,
        )
        db.session.add(r)
        db.session.commit()
        db.session.refresh(r)
        return r


@pytest.fixture
def admin_user(db, app, restaurant):
    from app.models import User, UserRole
    from argon2 import PasswordHasher
    ph = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    with app.app_context():
        u = User(
            name="Admin",
            phone="11000000001",
            password_hash=ph.hash("Admin@123"),
            role=UserRole.RESTAURANT_ADMIN,
            restaurant_id=restaurant.id,
        )
        db.session.add(u)
        db.session.commit()
        db.session.refresh(u)
        return u


@pytest.fixture
def staff_user(db, app, restaurant):
    from app.models import User, UserRole
    from argon2 import PasswordHasher
    ph = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    with app.app_context():
        u = User(
            name="Staff",
            phone="11000000002",
            password_hash=ph.hash("Staff@123"),
            role=UserRole.STAFF,
            restaurant_id=restaurant.id,
        )
        db.session.add(u)
        db.session.commit()
        db.session.refresh(u)
        return u


@pytest.fixture
def customer_user(db, app):
    from app.models import User, UserRole
    from argon2 import PasswordHasher
    ph = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    with app.app_context():
        u = User(
            name="Customer",
            phone="11000000003",
            password_hash=ph.hash("Customer@123"),
            role=UserRole.CUSTOMER,
        )
        db.session.add(u)
        db.session.commit()
        db.session.refresh(u)
        return u


def get_auth_cookies(client, phone: str, password: str) -> dict:
    """Helper: login and return cookies."""
    resp = client.post("/api/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.data}"
    return {c.name: c.value for c in client.cookie_jar}
