"""Testes de autenticacao: Argon2id, cookies, CSRF, rotacao e revogacao."""

from __future__ import annotations

from app.extensions import db
from app.models import Role, User
from app.repositories import UserRepository
from tests.conftest import CUSTOMER_PASSWORD

REGISTER_PAYLOAD = {
    "email": "novo@cliente.com",
    "password": "SenhaForte12345",
    "full_name": "Novo Cliente",
    "phone": "+5511988887777",
}


def test_register_cria_customer_com_argon2id(api, app):
    response = api.post("/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.get_json()
    assert body["role"] == Role.CUSTOMER.value
    assert "password" not in body and "password_hash" not in body

    user = UserRepository(db.s).get_by_email(REGISTER_PAYLOAD["email"])
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")


def test_register_rejeita_campos_extras(api):
    payload = {**REGISTER_PAYLOAD, "role": "RESTAURANT_ADMIN"}

    response = api.post("/auth/register", json=payload)

    assert response.status_code == 422
    assert response.get_json()["error"] == "validation_error"


def test_register_rejeita_senha_fraca(api):
    response = api.post("/auth/register", json={**REGISTER_PAYLOAD, "password": "curta1"})

    assert response.status_code == 422


def test_login_define_cookies_seguros(api, customer):
    response = api.login(customer.email, CUSTOMER_PASSWORD)

    cookies = response.headers.getlist("Set-Cookie")
    access_cookie = next(c for c in cookies if c.startswith("access_token="))
    refresh_cookie = next(c for c in cookies if c.startswith("refresh_token="))
    csrf_cookie = next(c for c in cookies if c.startswith("csrf_token="))

    assert "HttpOnly" in access_cookie and "SameSite=Lax" in access_cookie
    assert "HttpOnly" in refresh_cookie and "Path=/auth" in refresh_cookie
    # O cookie de CSRF precisa ser legivel por JS (double submit).
    assert "HttpOnly" not in csrf_cookie


def test_login_invalido_nao_revela_existencia(api, customer):
    inexistente = api.post(
        "/auth/login", json={"email": "naoexiste@teste.com", "password": "QualquerCoisa1"}
    )
    senha_errada = api.post(
        "/auth/login", json={"email": customer.email, "password": "SenhaErrada12345"}
    )

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.get_json() == senha_errada.get_json()


def test_rota_mutavel_sem_csrf_e_bloqueada(api, customer):
    api.login(customer.email, CUSTOMER_PASSWORD)

    response = api.client.post("/auth/logout")

    assert response.status_code == 403
    assert response.get_json()["error"] == "csrf_missing"


def test_csrf_invalido_e_bloqueado(api, customer):
    api.login(customer.email, CUSTOMER_PASSWORD)

    response = api.client.post("/auth/logout", headers={"X-CSRF-Token": "token-falso"})

    assert response.status_code == 403
    assert response.get_json()["error"] == "csrf_invalid"


def test_me_exige_autenticacao(api):
    assert api.get("/auth/me").status_code == 401


def test_refresh_rotaciona_e_revoga_token_antigo(api, customer):
    api.login(customer.email, CUSTOMER_PASSWORD)
    refresh_antigo = api.client.get_cookie("refresh_token", path="/auth").value

    primeira = api.post("/auth/refresh")
    assert primeira.status_code == 200
    novo_refresh = api.client.get_cookie("refresh_token", path="/auth").value
    assert novo_refresh != refresh_antigo

    # Reuso do refresh antigo deve falhar (denylist).
    api.client.set_cookie("refresh_token", refresh_antigo, path="/auth")
    reuso = api.post("/auth/refresh")
    assert reuso.status_code == 401
    assert reuso.get_json()["error"] == "token_revoked"


def test_logout_revoga_access_token(api, customer):
    api.login(customer.email, CUSTOMER_PASSWORD)
    assert api.get("/auth/me").status_code == 200

    logout = api.logout()
    assert logout.status_code == 200
    assert api.get("/auth/me").status_code == 401


def test_usuario_inativo_nao_autentica(api, customer, app):
    user = db.s.get(User, customer.id)
    user.is_active = False
    db.s.commit()

    response = api.post(
        "/auth/login", json={"email": customer.email, "password": CUSTOMER_PASSWORD}
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "inactive_account"
