from flask import Blueprint, jsonify, g

from ..services.dashboard_service import DashboardService
from .middleware import require_auth, verify_restaurant_access

dashboard_bp = Blueprint("dashboard", __name__)
_svc = DashboardService()


@dashboard_bp.get("/<restaurant_id>/dashboard")
@require_auth
def get_dashboard(restaurant_id: str):
    if not verify_restaurant_access(restaurant_id):
        return jsonify({"error": "Access denied"}), 403
    data = _svc.get_dashboard(restaurant_id)
    if data is None:
        return jsonify({"error": "Restaurant not found"}), 404
    return jsonify({"dashboard": data}), 200
