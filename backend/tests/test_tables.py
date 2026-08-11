"""Testes das transicoes de status de mesa (invalidas devem retornar 409)."""

from __future__ import annotations

import pytest

from app.extensions import db
from app.models import EventType, TableEvent, TableStatus
from tests.conftest import STAFF_PASSWORD, make_table


def _events(restaurant_id):
    return [
        event.event_type
        for event in db.s.query(TableEvent)
        .filter(TableEvent.restaurant_id == restaurant_id)
        .order_by(TableEvent.timestamp)
        .all()
    ]


def test_ciclo_completo_de_status(api, staff, restaurant):
    mesa = make_table(restaurant.id, "1", 4, TableStatus.OCCUPIED)
    api.login(staff.email, STAFF_PASSWORD)

    limpeza = api.post(f"/tables/{mesa.id}/cleaning")
    assert limpeza.get_json()["table"]["status"] == TableStatus.CLEANING.value

    liberacao = api.post(f"/tables/{mesa.id}/release")
    assert liberacao.get_json()["table"]["status"] == TableStatus.AVAILABLE.value

    ocupacao = api.post(f"/tables/{mesa.id}/occupy")
    assert ocupacao.get_json()["table"]["status"] == TableStatus.OCCUPIED.value

    assert _events(restaurant.id) == [
        EventType.TABLE_CLEANING,
        EventType.TABLE_AVAILABLE,
        EventType.TABLE_OCCUPIED,
    ]


@pytest.mark.parametrize(
    ("status_inicial", "acao"),
    [
        (TableStatus.AVAILABLE, "release"),
        (TableStatus.RESERVED, "release"),
        (TableStatus.CLEANING, "occupy"),
        (TableStatus.AVAILABLE, "cleaning"),
        (TableStatus.CLEANING, "cleaning"),
        (TableStatus.RESERVED, "cleaning"),
    ],
)
def test_transicoes_invalidas_retornam_409(api, staff, restaurant, status_inicial, acao):
    mesa = make_table(restaurant.id, "1", 4, status_inicial)
    api.login(staff.email, STAFF_PASSWORD)

    response = api.post(f"/tables/{mesa.id}/{acao}")

    assert response.status_code == 409
    assert response.get_json()["error"] == "conflict"


def test_liberar_mesa_ocupada_em_um_clique_gera_os_dois_eventos(api, staff, restaurant):
    """Reduz trabalho manual: OCCUPIED -> CLEANING -> AVAILABLE em uma unica chamada."""
    mesa = make_table(restaurant.id, "1", 4, TableStatus.OCCUPIED)
    api.login(staff.email, STAFF_PASSWORD)

    response = api.post(f"/tables/{mesa.id}/release")

    assert response.status_code == 200
    assert response.get_json()["table"]["status"] == TableStatus.AVAILABLE.value
    assert _events(restaurant.id) == [EventType.TABLE_CLEANING, EventType.TABLE_AVAILABLE]


def test_numero_de_mesa_duplicado_retorna_409(api, admin, restaurant):
    from tests.conftest import ADMIN_PASSWORD

    make_table(restaurant.id, "7", 4)
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.post(f"/restaurants/{restaurant.id}/tables", json={"number": "7", "capacity": 2})

    assert response.status_code == 409


def test_atualizar_mesa_valida_capacidade(api, admin, restaurant):
    from tests.conftest import ADMIN_PASSWORD

    mesa = make_table(restaurant.id, "1", 4)
    api.login(admin.email, ADMIN_PASSWORD)

    invalido = api.put(f"/tables/{mesa.id}", json={"capacity": 0})
    valido = api.put(f"/tables/{mesa.id}", json={"capacity": 8})

    assert invalido.status_code == 422
    assert valido.get_json()["capacity"] == 8


def test_mesa_inexistente_retorna_404(api, staff, restaurant):
    import uuid

    api.login(staff.email, STAFF_PASSWORD)

    response = api.post(f"/tables/{uuid.uuid4()}/release")

    assert response.status_code == 404
