"""Test: Auth routes and basic auth flows."""
import pytest


class TestAuth:
    def test_register_and_login(self, client, app):
        resp = client.post("/api/auth/register", json={
            "name": "Test User",
            "phone": "11999887766",
            "password": "TestPass@123",
        })
        assert resp.status_code == 201, resp.data
        data = resp.get_json()
        assert "user" in data

        resp2 = client.post("/api/auth/login", json={
            "phone": "11999887766",
            "password": "TestPass@123",
        })
        assert resp2.status_code == 200

    def test_login_invalid_password(self, client, app):
        client.post("/api/auth/register", json={
            "name": "User X",
            "phone": "11999887700",
            "password": "ValidPass@123",
        })
        resp = client.post("/api/auth/login", json={
            "phone": "11999887700",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    def test_extra_fields_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Test",
            "phone": "11999887755",
            "password": "TestPass@123",
            "evil_field": "injected",
        })
        assert resp.status_code == 422

    def test_me_requires_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_returns_user(self, client, app):
        client.post("/api/auth/register", json={
            "name": "Me User",
            "phone": "11988776655",
            "password": "MePass@123",
        })
        client.post("/api/auth/login", json={"phone": "11988776655", "password": "MePass@123"})
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["name"] == "Me User"

    def test_phone_masked_in_response(self, client, app):
        client.post("/api/auth/register", json={
            "name": "Masked User",
            "phone": "11977665544",
            "password": "MaskPass@123",
        })
        client.post("/api/auth/login", json={"phone": "11977665544", "password": "MaskPass@123"})
        resp = client.get("/api/auth/me")
        data = resp.get_json()
        phone = data["user"]["phone"]
        assert "5544" in phone
        assert "11977665" not in phone
