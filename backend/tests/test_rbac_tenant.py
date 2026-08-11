"""Testes de RBAC e isolamento de tenant (prevencao de IDOR/BOLA)."""

from __future__ import annotations

from app.models import Restaurant, Role, TableStatus, User
from tests.conftest import (
    ADMIN_PASSWORD,
    CUSTOMER_PASSWORD,
    STAFF_PASSWORD,
    make_table,
    make_user,
)


def test_staff_nao_cria_mesa(api, staff, restaurant):
    api.login(staff.email, STAFF_PASSWORD)

    response = api.post(
        f"/restaurants/{restaurant.id}/tables", json={"number": "99", "capacity": 4}
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "forbidden"


def test_admin_cria_mesa(api, admin, restaurant):
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.post(
        f"/restaurants/{restaurant.id}/tables", json={"number": "99", "capacity": 4}
    )

    assert response.status_code == 201
    assert response.get_json()["status"] == TableStatus.AVAILABLE.value


def test_customer_nao_acessa_dashboard(api, customer, restaurant):
    api.login(customer.email, CUSTOMER_PASSWORD)

    response = api.get(f"/restaurants/{restaurant.id}/dashboard")

    assert response.status_code == 403


def test_admin_nao_le_dashboard_de_outro_restaurante(api, admin, other_restaurant):
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.get(f"/restaurants/{other_restaurant.id}/dashboard")

    # 404 em vez de 403: nao confirma a existencia do recurso de outro tenant.
    assert response.status_code == 404


def test_admin_nao_manipula_mesa_de_outro_restaurante(api, admin, other_restaurant):
    mesa_alheia = make_table(other_restaurant.id, "1", 4, TableStatus.CLEANING)
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.post(f"/tables/{mesa_alheia.id}/release")

    assert response.status_code == 404


def test_admin_nao_lista_fila_de_outro_restaurante(api, admin, other_restaurant):
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.get(f"/restaurants/{other_restaurant.id}/queue")

    assert response.status_code == 404


def test_admin_nao_atualiza_outro_restaurante(api, admin, other_restaurant):
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.put(f"/restaurants/{other_restaurant.id}", json={"name": "Invadido"})

    assert response.status_code == 404


def test_staff_de_outro_restaurante_nao_ve_mesas(api, other_restaurant, restaurant):
    intruso = make_user(
        "intruso@teste.com", Role.STAFF, other_restaurant.id, STAFF_PASSWORD
    )
    api.login(intruso.email, STAFF_PASSWORD)

    response = api.get(f"/restaurants/{restaurant.id}/tables")

    assert response.status_code == 404


def test_criar_restaurante_promove_usuario_a_admin(api, customer):
    api.login(customer.email, CUSTOMER_PASSWORD)

    response = api.post(
        "/restaurants",
        json={
            "name": "Novo Restaurante",
            "address": "Rua Nova, 10",
            "phone": "+551122223333",
            "opening_hours": {"mon": {"open": "10:00", "close": "22:00"}},
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["role"] == Role.RESTAURANT_ADMIN.value
    assert body["user"]["restaurant_id"] == body["id"]
    # Cookies reemitidos com as novas claims permitem seguir sem novo login.
    assert api.get(f"/restaurants/{body['id']}/dashboard").status_code == 200


def test_admin_existente_nao_cria_segundo_restaurante(api, admin):
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.post(
        "/restaurants",
        json={"name": "Segundo", "address": "Rua Dois, 20", "phone": "+551122224444"},
    )

    assert response.status_code == 403


def test_listagem_publica_nao_expoe_telefone_do_restaurante(api, restaurant):
    response = api.get("/restaurants")

    assert response.status_code == 200
    item = response.get_json()["items"][0]
    assert "phone" not in item
    assert "is_active" not in item
    assert {"id", "name", "address", "waiting_groups", "estimated_wait_minutes"} <= set(item)


def test_usuario_sem_restaurante_nao_acessa_rotas_de_mesa(api, customer, restaurant):
    mesa = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    api.login(customer.email, CUSTOMER_PASSWORD)

    response = api.post(f"/tables/{mesa.id}/release")

    assert response.status_code == 403


def test_isolamento_usa_restaurant_id_do_token_e_nao_do_corpo(
    api, admin, restaurant, other_restaurant
):
    """Mesmo informando outro restaurante na URL, a mesa criada fica no tenant do token."""
    api.login(admin.email, ADMIN_PASSWORD)

    negado = api.post(
        f"/restaurants/{other_restaurant.id}/tables", json={"number": "50", "capacity": 2}
    )
    permitido = api.post(
        f"/restaurants/{restaurant.id}/tables", json={"number": "50", "capacity": 2}
    )

    assert negado.status_code == 404
    assert permitido.get_json()["restaurant_id"] == str(restaurant.id)


def test_dados_de_outro_tenant_nunca_vazam_na_listagem(api, admin, restaurant, other_restaurant):
    make_table(restaurant.id, "1", 4)
    make_table(other_restaurant.id, "1", 4)
    api.login(admin.email, ADMIN_PASSWORD)

    response = api.get(f"/restaurants/{restaurant.id}/tables")

    items = response.get_json()["items"]
    assert len(items) == 1
    assert all(item["restaurant_id"] == str(restaurant.id) for item in items)


def test_usuarios_e_restaurantes_usam_uuid_nao_sequencial(admin: User, restaurant: Restaurant):
    assert admin.id.version == 4
    assert restaurant.id.version == 4
