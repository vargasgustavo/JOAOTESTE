"""Rate limiting nas rotas sensiveis: login (brute force) e entrada na fila (flood)."""

from __future__ import annotations

import pytest
from flask import Flask

from app.extensions import db
from app.models import Restaurant, Role
from tests.conftest import ADMIN_PASSWORD, ApiClient, make_user


@pytest.fixture
def limited_api(rate_limited_app: Flask) -> ApiClient:
    return ApiClient(rate_limited_app.test_client())


@pytest.fixture
def limited_restaurant(rate_limited_app: Flask) -> Restaurant:
    entity = Restaurant(
        name="Cantina Limitada",
        address="Rua Teste, 100",
        phone="+551133334444",
        opening_hours={},
        is_active=True,
    )
    db.s.add(entity)
    db.s.commit()
    return entity


def test_login_bloqueia_apos_o_limite(limited_api, limited_restaurant):
    make_user("admin@limite.com", Role.RESTAURANT_ADMIN, limited_restaurant.id, ADMIN_PASSWORD)

    codigos = [
        limited_api.post(
            "/auth/login", json={"email": "admin@limite.com", "password": "SenhaErrada123"}
        ).status_code
        for _ in range(4)
    ]

    assert codigos[:3] == [401, 401, 401]
    assert codigos[3] == 429


def test_resposta_429_nao_vaza_detalhes_internos(limited_api, limited_restaurant):
    for _ in range(4):
        resposta = limited_api.post(
            "/auth/login", json={"email": "ninguem@limite.com", "password": "SenhaErrada123"}
        )
    assert resposta.status_code == 429
    body = resposta.get_json()
    assert body["error"] == "rate_limited"
    assert "traceback" not in body


def test_credencial_correta_tambem_conta_no_limite(limited_api, limited_restaurant):
    make_user("dono@limite.com", Role.RESTAURANT_ADMIN, limited_restaurant.id, ADMIN_PASSWORD)

    for _ in range(3):
        limited_api.post(
            "/auth/login", json={"email": "dono@limite.com", "password": "SenhaErrada123"}
        )
    bloqueado = limited_api.post(
        "/auth/login", json={"email": "dono@limite.com", "password": ADMIN_PASSWORD}
    )
    assert bloqueado.status_code == 429


def test_entrada_na_fila_tem_limite_proprio(limited_api, limited_restaurant):
    codigos = []
    for indice in range(7):
        resposta = limited_api.post(
            f"/restaurants/{limited_restaurant.id}/queue",
            json={
                "customer_name": f"Cliente {indice}",
                "customer_phone": f"+55119000030{indice:02d}",
                "party_size": 2,
            },
        )
        codigos.append(resposta.status_code)

    assert codigos.count(201) == 5  # RATELIMIT_QUEUE_JOIN padrao: 5 por minuto
    assert codigos[-1] == 429
