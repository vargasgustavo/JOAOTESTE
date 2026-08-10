"""Test: Tenant isolation."""


class TestTenantIsolation:
    def test_staff_cannot_see_other_restaurant_queue(self, client, app, restaurant, staff_user):
        from app.extensions import db
        from app.models import QueueEntry, QueueStatus, Restaurant

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

        client.post("/api/auth/login", json={"phone": staff_user.phone, "password": "Staff@123"})
        resp = client.get(f"/api/restaurants/{rest_b_id}/queue")
        assert resp.status_code == 403

    def test_staff_can_see_own_restaurant_queue(self, client, app, restaurant, staff_user):
        from app.extensions import db
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

        client.post("/api/auth/login", json={"phone": staff_user.phone, "password": "Staff@123"})
        resp = client.get(f"/api/restaurants/{restaurant.id}/queue")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["queue"]) >= 1
