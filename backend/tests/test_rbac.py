"""Test: RBAC enforcement."""
import pytest


def _login(client, phone, password):
    resp = client.post("/api/auth/login", json={"phone": phone, "password": password})
    return {c.name: c.value for c in client.cookie_jar}


def _cookie_header(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


class TestRBAC:
    def test_customer_cannot_release_table(self, client, app, db, restaurant, customer_user, staff_user):
        from app.models import Table, TableStatus
        with app.app_context():
            table = Table(
                restaurant_id=restaurant.id,
                number=10,
                capacity=4,
                status=TableStatus.OCCUPIED,
            )
            db.session.add(table)
            db.session.commit()
            table_id = table.id

        cookies = _login(client, "11000000003", "Customer@123")
        resp = client.post(
            f"/api/tables/{table_id}/release",
            headers={"Cookie": _cookie_header(cookies)},
        )
        assert resp.status_code == 403

    def test_staff_cannot_create_restaurant(self, client, app, db, restaurant, staff_user):
        cookies = _login(client, "11000000002", "Staff@123")
        resp = client.post(
            "/api/restaurants/",
            json={"name": "New", "address": "addr", "phone": "11999"},
            headers={"Cookie": _cookie_header(cookies)},
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_queue(self, client, app, db, restaurant):
        resp = client.get(f"/api/restaurants/{restaurant.id}/queue")
        assert resp.status_code == 401

    def test_admin_can_create_restaurant(self, client, app, db, restaurant, admin_user):
        cookies = _login(client, "11000000001", "Admin@123")
        resp = client.post(
            "/api/restaurants/",
            json={"name": "New Rest", "address": "Rua Nova 1", "phone": "11900000000"},
            headers={"Cookie": _cookie_header(cookies)},
        )
        assert resp.status_code == 201
