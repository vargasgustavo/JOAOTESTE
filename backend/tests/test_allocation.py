"""Testes do TableAllocationService: FIFO compativel, eventos e notificacao."""

from __future__ import annotations

from app.extensions import db
from app.models import (
    EventType,
    Notification,
    NotificationStatus,
    QueueEntry,
    QueueStatus,
    TableEvent,
    TableStatus,
)
from app.services import build_table_ready_message
from tests.conftest import ADMIN_PASSWORD, STAFF_PASSWORD, make_queue_entry, make_table


def _event_types(restaurant_id):
    return [
        event.event_type
        for event in db.s.query(TableEvent)
        .filter(TableEvent.restaurant_id == restaurant_id)
        .order_by(TableEvent.timestamp)
        .all()
    ]


def test_fifo_escolhe_primeiro_grupo_compativel(api, staff, restaurant, mock_provider):
    """Mesa cap. 4 + fila Joao(4), Maria(2), Pedro(5) => Joao ganha a mesa."""
    mesa = make_table(restaurant.id, "5", 4, TableStatus.CLEANING)
    joao = make_queue_entry(restaurant.id, "Joao", "+5511999990001", 4, 1)
    maria = make_queue_entry(restaurant.id, "Maria", "+5511999990002", 2, 2)
    pedro = make_queue_entry(restaurant.id, "Pedro", "+5511999990003", 5, 3)
    api.login(staff.email, STAFF_PASSWORD)

    response = api.post(f"/tables/{mesa.id}/release")

    assert response.status_code == 200
    alocacao = response.get_json()["allocation"]
    assert alocacao["customer_name"] == "Joao"
    assert alocacao["table_number"] == "5"

    db.s.expire_all()
    assert db.s.get(QueueEntry, joao.id).status == QueueStatus.CALLED
    assert db.s.get(QueueEntry, joao.id).called_at is not None
    assert db.s.get(QueueEntry, maria.id).status == QueueStatus.WAITING
    assert db.s.get(QueueEntry, pedro.id).status == QueueStatus.WAITING
    assert db.s.get(type(mesa), mesa.id).status == TableStatus.RESERVED


def test_grupo_maior_que_a_mesa_e_ignorado(api, staff, restaurant):
    mesa = make_table(restaurant.id, "1", 2, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Pedro", "+5511999990003", 5, 1)
    maria = make_queue_entry(restaurant.id, "Maria", "+5511999990002", 2, 2)
    api.login(staff.email, STAFF_PASSWORD)

    alocacao = api.post(f"/tables/{mesa.id}/release").get_json()["allocation"]

    assert alocacao["customer_name"] == "Maria"
    db.s.expire_all()
    assert db.s.get(QueueEntry, maria.id).status == QueueStatus.CALLED


def test_sem_grupo_compativel_mesa_fica_available(api, staff, restaurant):
    mesa = make_table(restaurant.id, "1", 2, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Pedro", "+5511999990003", 5, 1)
    api.login(staff.email, STAFF_PASSWORD)

    body = api.post(f"/tables/{mesa.id}/release").get_json()

    assert body["allocation"] is None
    assert body["table"]["status"] == TableStatus.AVAILABLE.value


def test_alocacao_registra_eventos_e_notificacao(api, staff, restaurant, mock_provider):
    mesa = make_table(restaurant.id, "5", 4, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Joao Almeida", "+5511999990001", 4, 1)
    api.login(staff.email, STAFF_PASSWORD)

    api.post(f"/tables/{mesa.id}/release")

    eventos = _event_types(restaurant.id)
    assert eventos == [
        EventType.TABLE_AVAILABLE,
        EventType.CUSTOMER_ASSIGNED,
        EventType.CUSTOMER_CALLED,
    ]

    notificacao = db.s.query(Notification).one()
    assert notificacao.status == NotificationStatus.SENT
    assert notificacao.sent_at is not None
    assert notificacao.message == build_table_ready_message("Joao Almeida", restaurant.name)
    assert mock_provider.sent[-1][0] == "WHATSAPP"


def test_cliente_entrando_na_fila_pega_mesa_livre(api, restaurant, mock_provider):
    make_table(restaurant.id, "1", 4, TableStatus.AVAILABLE)

    response = api.post(
        f"/restaurants/{restaurant.id}/queue",
        json={"customer_name": "Ana", "customer_phone": "+5511999990004", "party_size": 3},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == QueueStatus.CALLED.value
    assert body["allocation"]["table_number"] == "1"


def test_alocacao_escolhe_a_menor_mesa_compativel(api, restaurant):
    make_table(restaurant.id, "8", 8, TableStatus.AVAILABLE)
    make_table(restaurant.id, "4", 4, TableStatus.AVAILABLE)

    body = api.post(
        f"/restaurants/{restaurant.id}/queue",
        json={"customer_name": "Ana", "customer_phone": "+5511999990004", "party_size": 3},
    ).get_json()

    assert body["allocation"]["table_number"] == "4"


def test_ocupar_mesa_reservada_marca_cliente_como_seated(api, staff, restaurant):
    mesa = make_table(restaurant.id, "5", 4, TableStatus.CLEANING)
    joao = make_queue_entry(restaurant.id, "Joao", "+5511999990001", 4, 1)
    api.login(staff.email, STAFF_PASSWORD)
    api.post(f"/tables/{mesa.id}/release")

    response = api.post(f"/tables/{mesa.id}/occupy")

    assert response.get_json()["table"]["status"] == TableStatus.OCCUPIED.value
    db.s.expire_all()
    entrada = db.s.get(QueueEntry, joao.id)
    assert entrada.status == QueueStatus.SEATED
    assert entrada.seated_at is not None
    assert EventType.CUSTOMER_SEATED in _event_types(restaurant.id)


def test_alocacao_manual_e_fallback_para_mesa_available(api, staff, restaurant):
    mesa = make_table(restaurant.id, "5", 4, TableStatus.AVAILABLE)
    api.login(staff.email, STAFF_PASSWORD)
    make_queue_entry(restaurant.id, "Joao", "+5511999990001", 4, 1)

    response = api.post(f"/tables/{mesa.id}/allocate")

    assert response.status_code == 200
    assert response.get_json()["allocation"]["customer_name"] == "Joao"


def test_alocacao_manual_em_mesa_ocupada_retorna_409(api, staff, restaurant):
    mesa = make_table(restaurant.id, "5", 4, TableStatus.OCCUPIED)
    api.login(staff.email, STAFF_PASSWORD)

    assert api.post(f"/tables/{mesa.id}/allocate").status_code == 409


def test_cancelar_chamado_libera_mesa_e_chama_o_proximo(api, admin, restaurant):
    mesa = make_table(restaurant.id, "5", 4, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Joao", "+5511999990001", 4, 1)
    maria = make_queue_entry(restaurant.id, "Maria", "+5511999990002", 2, 2)
    api.login(admin.email, ADMIN_PASSWORD)
    chamado = api.post(f"/tables/{mesa.id}/release").get_json()["allocation"]

    response = api.post(f"/queue/{chamado['queue_entry_id']}/cancel")

    assert response.status_code == 200
    assert response.get_json()["reallocation"]["customer_name"] == "Maria"
    db.s.expire_all()
    assert db.s.get(QueueEntry, maria.id).status == QueueStatus.CALLED
