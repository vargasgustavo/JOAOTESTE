"""Test: Tenant isolation - user from restaurant A cannot see restaurant B's queue."""
import pytest


def _login(client, phone, password):
    resp = client.post("/api/auth/login", json={"phone": phone, "password": password})
    return {c.name: c.value for c in client.cookie_jar}


def _cookie_header(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


class TestTenantIsolation:
    def test_staff_cannot_see_other_restaurant_queue(self, client, app, db, restaurant, staff_user):
        """Staff of restaurant A cannot list queue of restaurant B."""
        from app.models import Restaurant, User, UserRole, QueueEntry, QueueStatus
        from argon2 import PasswordHasher
        ph = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)

        with app.app_context():
            rest_b = Restaurant(
                name="Restaurant B",
                address="Rua B, 2",
                phone="11888888888",
                is_active=True,
            )
            db.session.add(rest_b)
            db.session.flush()

            entry = QueueEntry(
                restaurant_id=rest_b.id,
                customer_name="Secret Customer",
                customer_phone="11999999999",
                party_size=2,
                status=QueueStatus.WAITING,
            )
            db.session.add(entry)
            db.session.commit()
            rest_b_id = rest_b.id

        cookies = _login(client, "11000000002", "Staff@123")
        resp = client.get(
            f"/api/restaurants/{rest_b_id}/queue",
            headers={"Cookie": _cookie_header(cookies)},
        )
        assert resp.status_code == 403

    def test_staff_can_see_own_restaurant_queue(self, client, app, db, restaurant, staff_user):
        from app.models import QueueEntry, QueueStatus
        with app.app_context():
            entry = QueueEntry(
                restaurant_id=restaurant.id,
                customer_name="Own Customer",
                customer_phone="11100000000",
                party_size=2,
                status=QueueStatus.WAITING,
            )
            db.session.add(entry)
            db.session.commit()

        cookies = _login(client, "11000000002", "Staff@123")
        resp = client.get(
            f"/api/restaurants/{restaurant.id}/queue",
            headers={"Cookie": _cookie_header(cookies)},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["queue"]) >= 1
