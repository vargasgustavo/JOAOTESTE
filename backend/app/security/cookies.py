"""Cookies de autenticacao (HttpOnly/Secure/SameSite) e CSRF double-submit."""

from __future__ import annotations

import secrets

from flask import Response, current_app, request

from app.errors import AuthorizationError

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
REFRESH_COOKIE_PATH = "/auth"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _cookie_kwargs() -> dict[str, object]:
    return {
        "secure": current_app.config["COOKIE_SECURE"],
        "samesite": current_app.config["COOKIE_SAMESITE"],
        "domain": current_app.config.get("COOKIE_DOMAIN"),
    }


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str, csrf_token: str
) -> Response:
    common = _cookie_kwargs()
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        max_age=current_app.config["ACCESS_TOKEN_TTL_SECONDS"],
        path="/",
        **common,
    )
    # Refresh so trafega nas rotas /auth/*, reduzindo a superficie de exposicao.
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        max_age=current_app.config["REFRESH_TOKEN_TTL_SECONDS"],
        path=REFRESH_COOKIE_PATH,
        **common,
    )
    set_csrf_cookie(response, csrf_token)
    return response


def set_csrf_cookie(response: Response, csrf_token: str) -> Response:
    # Legivel por JS de proposito: e o lado "double submit" da protecao CSRF.
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        max_age=current_app.config["REFRESH_TOKEN_TTL_SECONDS"],
        path="/",
        **_cookie_kwargs(),
    )
    return response


def clear_auth_cookies(response: Response) -> Response:
    common = _cookie_kwargs()
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, **common)
    response.delete_cookie(CSRF_COOKIE, path="/", **common)
    return response


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def enforce_csrf() -> None:
    """Double submit: cookie csrf_token deve bater com o header X-CSRF-Token."""
    if request.method in SAFE_METHODS:
        return
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get(CSRF_HEADER, "")
    if not cookie_token or not header_token:
        raise AuthorizationError("Token CSRF ausente.", error_code="csrf_missing")
    if not secrets.compare_digest(cookie_token, header_token):
        raise AuthorizationError("Token CSRF invalido.", error_code="csrf_invalid")
