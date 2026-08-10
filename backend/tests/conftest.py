import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-length-32")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32ch")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_MEMORY_COST", "8192")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_restaurant.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

# Mock Redis globally so tests don't need Redis running
mock_redis = MagicMock()
mock_redis.exists.return_value = False
mock_redis.setex.return_value = True


@pytest.fixture(scope="session", autouse=True)
def mock_redis_globally():
    with patch("app.services.auth_service.redis.from_url", return_value=mock_redis):
        yield


@pytest.fixture(scope="session")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app("testing")
    application.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": TEST_DB_URL,
    })
    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(autouse=True)
def clean_tables(app):
    from app.extensions import db
    yield
    with app.app_context():
        db.session.remove()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def restaurant(app):
    from app.extensions import db
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
        # Return a simple namespace with the id
        class Obj:
            pass
        obj = Obj()
        obj.id = r.id
        obj.name = r.name
        return obj


@pytest.fixture
def admin_user(app, restaurant):
    from argon2 import PasswordHasher

    from app.extensions import db
    from app.models import User, UserRole
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
        class Obj:
            pass
        obj = Obj()
        obj.id = u.id
        obj.phone = u.phone
        obj.restaurant_id = u.restaurant_id
        return obj


@pytest.fixture
def staff_user(app, restaurant):
    from argon2 import PasswordHasher

    from app.extensions import db
    from app.models import User, UserRole
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
        class Obj:
            pass
        obj = Obj()
        obj.id = u.id
        obj.phone = u.phone
        obj.restaurant_id = u.restaurant_id
        return obj


@pytest.fixture
def customer_user(app):
    from argon2 import PasswordHasher

    from app.extensions import db
    from app.models import User, UserRole
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
        class Obj:
            pass
        obj = Obj()
        obj.id = u.id
        obj.phone = u.phone
        obj.restaurant_id = None
        return obj
