import functools
import secrets
from flask import request, jsonify, current_app, g

from ..services.auth_service import AuthService
from ..models import UserRole


def get_token_from_cookie(token_type: str = "access") -> str | None:
    cookie_name = f"{token_type}_token"
    return request.cookies.get(cookie_name)


def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_cookie("access")
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            auth_svc = AuthService()
            payload = auth_svc.decode_token(token)
            g.user_id = payload["sub"]
            g.user_role = payload["role"]
            g.restaurant_id = payload.get("restaurant_id")
        except ValueError as e:
            return jsonify({"error": str(e)}), 401
        return f(*args, **kwargs)
    return decorated


def require_roles(*roles: str):
    def decorator(f):
        @functools.wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if g.user_role not in [r.value if hasattr(r, 'value') else r for r in roles]:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_csrf(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if current_app.config.get("TESTING") or current_app.config.get("WTF_CSRF_ENABLED") is False:
            return f(*args, **kwargs)
        csrf_cookie = request.cookies.get(current_app.config["CSRF_COOKIE_NAME"], "")
        csrf_header = request.headers.get(current_app.config["CSRF_HEADER_NAME"], "")
        if not csrf_cookie or not csrf_header:
            return jsonify({"error": "CSRF token missing"}), 403
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            return jsonify({"error": "CSRF token invalid"}), 403
        return f(*args, **kwargs)
    return decorated


def verify_restaurant_access(restaurant_id: str) -> bool:
    """Verify the logged-in user belongs to the restaurant (or is CUSTOMER)."""
    role = getattr(g, "user_role", None)
    if role == UserRole.CUSTOMER.value:
        return True
    user_restaurant = getattr(g, "restaurant_id", None)
    return user_restaurant == restaurant_id
