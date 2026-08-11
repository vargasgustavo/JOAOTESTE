"""Rotas de autenticacao. Toda logica fica no AuthService."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, make_response

from app.controllers.helpers import parse_body, serialize
from app.errors import AuthenticationError
from app.extensions import limiter
from app.schemas.auth import CsrfResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    auth_required,
    clear_auth_cookies,
    current_user,
    generate_csrf_token,
    set_auth_cookies,
    set_csrf_cookie,
)
from app.services import AuthService, transaction

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _auth_limit() -> str:
    return current_app.config["RATELIMIT_AUTH"]


@bp.get("/csrf")
@limiter.limit("60 per minute")
def csrf():
    """Emite o cookie CSRF antes de qualquer requisicao mutavel."""
    token = generate_csrf_token()
    response = make_response(jsonify(serialize(CsrfResponse(csrf_token=token))), 200)
    set_csrf_cookie(response, token)
    return response


@bp.post("/register")
@limiter.limit(_auth_limit)
def register():
    payload = parse_body(RegisterRequest)
    with transaction() as session:
        service = AuthService(session)
        user = service.register_customer(payload)
        tokens = service.issue_tokens(user)
        body = serialize(UserResponse.model_validate(user))
    response = make_response(jsonify(body), 201)
    return set_auth_cookies(response, tokens.access_token, tokens.refresh_token, tokens.csrf_token)


@bp.post("/login")
@limiter.limit(_auth_limit)
def login():
    payload = parse_body(LoginRequest)
    with transaction() as session:
        service = AuthService(session)
        user = service.authenticate(payload)
        tokens = service.issue_tokens(user)
        body = serialize(UserResponse.model_validate(user))
    response = make_response(jsonify(body), 200)
    return set_auth_cookies(response, tokens.access_token, tokens.refresh_token, tokens.csrf_token)


@bp.post("/refresh")
@limiter.limit("30 per minute")
def refresh():
    from flask import request

    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise AuthenticationError("Refresh token ausente.")
    with transaction() as session:
        service = AuthService(session)
        user, tokens = service.rotate_refresh(token)
        body = serialize(UserResponse.model_validate(user))
    response = make_response(jsonify(body), 200)
    return set_auth_cookies(response, tokens.access_token, tokens.refresh_token, tokens.csrf_token)


@bp.post("/logout")
def logout():
    from flask import request

    with transaction() as session:
        AuthService(session).logout(
            request.cookies.get(ACCESS_COOKIE), request.cookies.get(REFRESH_COOKIE)
        )
    response = make_response(jsonify({"message": "Sessao encerrada."}), 200)
    return clear_auth_cookies(response)


@bp.get("/me")
@auth_required
def me():
    return jsonify(serialize(UserResponse.model_validate(current_user()))), 200
