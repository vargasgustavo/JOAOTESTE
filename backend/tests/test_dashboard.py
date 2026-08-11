"""Dashboard agregado: numeros corretos, 1 query e isolado por tenant."""

from __future__ import annotations

from app.models import TableStatus
from tests.conftest import ADMIN_PASSWORD, STAFF_PASSWORD, make_queue_entry, make_table


def _montar_salao(restaurant_id) -> None:
    make_table(restaurant_id, "1", 2, TableStatus.OCCUPIED)
    make_table(restaurant_id, "2", 4, TableStatus.OCCUPIED)
    make_table(restaurant_id, "3", 4, TableStatus.CLEANING)
    make_table(restaurant_id, "4", 6, TableStatus.AVAILABLE)
    make_table(restaurant_id, "5", 8, TableStatus.RESERVED)


def test_dashboard_agrega_mesas_e_fila(api, restaurant, admin):
    _montar_salao(restaurant.id)
    make_queue_entry(restaurant.id, "Joao", "+5511900001001", 4, 1)
    make_queue_entry(restaurant.id, "Maria", "+5511900001002", 2, 2)

    api.login(admin.email, ADMIN_PASSWORD)
    response = api.get(f"/restaurants/{restaurant.id}/dashboard")
    assert response.status_code == 200

    body = response.get_json()
    assert body["total_tables"] == 5
    assert body["occupied_tables"] == 2
    assert body["cleaning_tables"] == 1
    assert body["available_tables"] == 1
    assert body["reserved_tables"] == 1
    assert body["waiting_customers"] == 2
    assert body["called_customers"] == 0
    assert body["average_turnover_minutes"] == 15
    assert body["average_wait_minutes"] > 0


def test_dashboard_usa_uma_unica_query_de_agregacao(app, restaurant):
    from sqlalchemy import event

    from app.extensions import db
    from app.services import DashboardService, WaitTimeService

    _montar_salao(restaurant.id)
    make_queue_entry(restaurant.id, "Joao", "+5511900001011", 4, 1)

    executadas: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ARG001
        if statement.lstrip().upper().startswith("SELECT"):
            executadas.append(statement)

    event.listen(db.engine, "before_cursor_execute", _capture)
    try:
        service = DashboardService(db.s, WaitTimeService(db.s))
        service.metrics(restaurant.id)
    finally:
        event.remove(db.engine, "before_cursor_execute", _capture)

    # 1 query agregada de metricas + 1 do WaitTimeService (servico isolado).
    assert len(executadas) == 2, executadas


def test_dashboard_do_restaurante_alheio_retorna_404(api, restaurant, other_restaurant, admin):
    api.login(admin.email, ADMIN_PASSWORD)
    assert api.get(f"/restaurants/{other_restaurant.id}/dashboard").status_code == 404


def test_staff_tambem_ve_o_dashboard_do_proprio_restaurante(api, restaurant, staff):
    _montar_salao(restaurant.id)
    api.login(staff.email, STAFF_PASSWORD)
    assert api.get(f"/restaurants/{restaurant.id}/dashboard").status_code == 200


def test_dashboard_exige_autenticacao(api, restaurant):
    assert api.get(f"/restaurants/{restaurant.id}/dashboard").status_code == 401


def test_dashboard_reflete_liberacao_de_mesa(api, restaurant, staff):
    mesa = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Joao", "+5511900001021", 4, 1)

    api.login(staff.email, STAFF_PASSWORD)
    assert api.post(f"/tables/{mesa.id}/release").status_code == 200

    body = api.get(f"/restaurants/{restaurant.id}/dashboard").get_json()
    assert body["cleaning_tables"] == 0
    assert body["reserved_tables"] == 1
    assert body["waiting_customers"] == 0
    assert body["called_customers"] == 1
