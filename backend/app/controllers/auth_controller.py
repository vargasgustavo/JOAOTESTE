from flask import Blueprint, request, jsonify, make_response, current_app, g
from marshmallow import ValidationError

from ..services.auth_service import AuthService
from ..schemas import RegisterSchema, LoginSchema, UserSchema
from ..extensions import limiter
from .middleware import require_auth, require_csrf

auth_bp = Blueprint("auth", __name__)
_register_schema = RegisterSchema()
_login_schema = LoginSchema()
_user_schema = UserSchema()


@auth_bp.post("/register")
@limiter.limit("5 per minute")
@require_csrf
def register():
    try:
        data = _register_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422

    auth_svc = AuthService()
    try:
        user = auth_svc.register(**data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409

    access_token, refresh_token, _ = auth_svc.login(data["phone"], data["password"])
    response = make_response(jsonify({"user": _user_schema.dump(user), "message": "Registered"}), 201)
    _set_tokens(response, access_token, refresh_token)
    return response


@auth_bp.post("/login")
@limiter.limit("5 per minute")
@require_csrf
def login():
    try:
        data = _login_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422

    auth_svc = AuthService()
    try:
        access_token, refresh_token, user = auth_svc.login(data["phone"], data["password"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    response = make_response(jsonify({"user": _user_schema.dump(user), "message": "Logged in"}), 200)
    _set_tokens(response, access_token, refresh_token)
    return response


@auth_bp.post("/logout")
@require_auth
@require_csrf
def logout():
    access_token = request.cookies.get("access_token", "")
    refresh_token = request.cookies.get("refresh_token", "")
    auth_svc = AuthService()
    auth_svc.logout(access_token, refresh_token)

    response = make_response(jsonify({"message": "Logged out"}), 200)
    _clear_tokens(response)
    return response


@auth_bp.post("/refresh")
@require_csrf
def refresh():
    refresh_token = request.cookies.get("refresh_token", "")
    if not refresh_token:
        return jsonify({"error": "Refresh token missing"}), 401

    auth_svc = AuthService()
    try:
        access_token, new_refresh_token = auth_svc.refresh_tokens(refresh_token)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    response = make_response(jsonify({"message": "Tokens refreshed"}), 200)
    _set_tokens(response, access_token, new_refresh_token)
    return response


@auth_bp.get("/me")
@require_auth
def me():
    from ..repositories import UserRepository
    user_repo = UserRepository()
    user = user_repo.get_by_id(g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": _user_schema.dump(user)}), 200


def _set_tokens(response, access_token: str, refresh_token: str) -> None:
    secure = current_app.config.get("JWT_COOKIE_SECURE", True)
    response.set_cookie(
        "access_token", access_token,
        httponly=True, secure=secure, samesite="Strict",
        max_age=int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, secure=secure, samesite="Strict",
        max_age=int(current_app.config["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds()),
        path="/api/auth/refresh",
    )


def _clear_tokens(response) -> None:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/auth/refresh")
