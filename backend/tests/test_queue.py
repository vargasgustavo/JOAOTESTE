"""Fila: entrada publica, posicao/estimativa, listagem interna e cancelamento."""

from __future__ import annotations

from app.models import QueueStatus, TableStatus
from tests.conftest import STAFF_PASSWORD, make_queue_entry, make_table


def _join(api, restaurant_id, name="Joao", phone="+5511999990000", party_size=4):
    return api.post(
        f"/restaurants/{restaurant_id}/queue",
        json={"customer_name": name, "customer_phone": phone, "party_size": party_size},
    )


def test_cliente_entra_na_fila_sem_conta(api, restaurant):
    response = _join(api, restaurant.id)
    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == QueueStatus.WAITING.value
    assert body["position"] == 1
    assert body["restaurant_name"] == restaurant.name
    assert body["allocation"] is None


def test_resposta_publica_nunca_expoe_telefone_nem_ids_internos(api, restaurant):
    body = _join(api, restaurant.id).get_json()
    assert "customer_phone" not in body
    assert "assigned_table_id" not in body
    assert "user_id" not in body
    assert "restaurant_id" not in body


def test_posicao_e_estimativa_usam_fallback_de_15_minutos(api, restaurant):
    _join(api, restaurant.id, name="Joao", phone="+5511999990001")
    _join(api, restaurant.id, name="Maria", phone="+5511999990002", party_size=2)
    terceiro = _join(api, restaurant.id, name="Pedro", phone="+5511999990003", party_size=2)

    ticket = api.get(f"/queue/{terceiro.get_json()['id']}").get_json()
    assert ticket["position"] == 3
    assert ticket["estimated_wait_minutes"] == 45  # 3 x 15 min (sem historico)


def test_telefone_duplicado_na_mesma_fila_e_rejeitado(api, restaurant):
    assert _join(api, restaurant.id, phone="+5511988887777").status_code == 201
    repetido = _join(api, restaurant.id, name="Outro", phone="+5511988887777")
    assert repetido.status_code == 409


def test_entrada_invalida_e_campos_extras_sao_rejeitados(api, restaurant):
    sem_campos = api.post(f"/restaurants/{restaurant.id}/queue", json={"customer_name": "Ana"})
    assert sem_campos.status_code == 422

    extra = api.post(
        f"/restaurants/{restaurant.id}/queue",
        json={
            "customer_name": "Ana",
            "customer_phone": "+5511999990009",
            "party_size": 2,
            "status": "SEATED",
        },
    )
    assert extra.status_code == 422

    grupo_absurdo = api.post(
        f"/restaurants/{restaurant.id}/queue",
        json={
            "customer_name": "Ana",
            "customer_phone": "+5511999990010",
            "party_size": 999,
        },
    )
    assert grupo_absurdo.status_code == 422


def test_fila_de_restaurante_inexistente_retorna_404(api):
    response = api.post(
        "/restaurants/2f1d5ad7-05c4-4a6a-9f1e-6a2f0a5b7c1d/queue",
        json={"customer_name": "Ana", "customer_phone": "+5511999990011", "party_size": 2},
    )
    assert response.status_code == 404


def test_listagem_interna_mostra_telefone_e_ordem_fifo(api, restaurant, staff):
    make_queue_entry(restaurant.id, "Joao", "+5511900000001", 4, 1)
    make_queue_entry(restaurant.id, "Maria", "+5511900000002", 2, 2)

    api.login(staff.email, STAFF_PASSWORD)
    response = api.get(f"/restaurants/{restaurant.id}/queue")
    assert response.status_code == 200
    items = response.get_json()["items"]
    assert [item["customer_name"] for item in items] == ["Joao", "Maria"]
    assert [item["position"] for item in items] == [1, 2]
    assert items[0]["customer_phone"] == "+5511900000001"


def test_cliente_cancela_pelo_ticket_e_sai_da_fila(api, restaurant):
    ticket = _join(api, restaurant.id).get_json()
    cancel = api.post(f"/queue/{ticket['id']}/cancel")
    assert cancel.status_code == 200
    assert cancel.get_json()["status"] == QueueStatus.CANCELLED.value

    de_novo = api.post(f"/queue/{ticket['id']}/cancel")
    assert de_novo.status_code == 409


def test_cancelar_chamado_devolve_mesa_e_realoca_proximo(api, restaurant, staff):
    make_table(restaurant.id, "1", 4, TableStatus.AVAILABLE)
    chamado = _join(api, restaurant.id, name="Joao", phone="+5511900000021", party_size=4)
    assert chamado.get_json()["status"] == QueueStatus.CALLED.value

    _join(api, restaurant.id, name="Maria", phone="+5511900000022", party_size=2)

    cancel = api.post(f"/queue/{chamado.get_json()['id']}/cancel").get_json()
    assert cancel["status"] == QueueStatus.CANCELLED.value
    # A mesa liberada e imediatamente reaproveitada pelo proximo compativel.
    assert cancel["reallocation"]["customer_name"] == "Maria"


def test_ticket_de_outro_restaurante_e_invisivel_para_staff(
    api, restaurant, other_restaurant, staff
):
    intruso = make_queue_entry(other_restaurant.id, "Alheio", "+5511900000031", 2, 1)
    api.login(staff.email, STAFF_PASSWORD)
    assert api.get(f"/queue/{intruso.id}").status_code == 404
    assert api.post(f"/queue/{intruso.id}/cancel").status_code == 404


def test_ticket_vinculado_a_conta_exige_sessao_do_dono(api, restaurant, customer):
    from app.extensions import db

    entry = make_queue_entry(restaurant.id, "Cliente", "+5511900000041", 2, 1)
    entry.user_id = customer.id
    db.s.commit()

    assert api.get(f"/queue/{entry.id}").status_code == 404


def test_fila_publica_do_restaurante_nao_lista_clientes(api, restaurant):
    make_queue_entry(restaurant.id, "Joao", "+5511900000051", 4, 1)
    response = api.get(f"/restaurants/{restaurant.id}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["waiting_groups"] == 1
    assert "phone" not in body
    assert "queue" not in body
