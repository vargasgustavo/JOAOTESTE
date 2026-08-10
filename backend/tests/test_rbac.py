"""Test: RBAC enforcement."""


class TestRBAC:
    def test_customer_cannot_release_table(self, client, app, restaurant, customer_user, staff_user):
        from app.extensions import db
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

        # Login as customer
        client.post("/api/auth/login", json={"phone": customer_user.phone, "password": "Customer@123"})
        resp = client.post(f"/api/tables/{table_id}/release")
        assert resp.status_code == 403

    def test_staff_cannot_create_restaurant(self, client, restaurant, staff_user):
        client.post("/api/auth/login", json={"phone": staff_user.phone, "password": "Staff@123"})
        resp = client.post(
            "/api/restaurants/",
            json={"name": "New", "address": "addr", "phone": "11999"},
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_queue(self, client, restaurant):
        resp = client.get(f"/api/restaurants/{restaurant.id}/queue")
        assert resp.status_code == 401

    def test_admin_can_create_restaurant(self, client, restaurant, admin_user):
        client.post("/api/auth/login", json={"phone": admin_user.phone, "password": "Admin@123"})
        resp = client.post(
            "/api/restaurants/",
            json={"name": "New Rest", "address": "Rua Nova 1", "phone": "11900000000"},
        )
        assert resp.status_code == 201
