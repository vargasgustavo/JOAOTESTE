"""Decorators de autenticacao/RBAC e helpers de isolamento por tenant."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from flask import g, request

from app.errors import AuthenticationError, AuthorizationError
from app.extensions import db
from app.models import Role, User
from app.repositories import UserRepository
from app.security.cookies import ACCESS_COOKIE
from app.security.tokens import decode_token

F = TypeVar("F", bound=Callable[..., Any])


def load_current_user() -> User:
    """Valida o access token do cookie e carrega o usuario correspondente."""
    cached = getattr(g, "current_user", None)
    if cached is not None:
        return cast(User, cached)

    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise AuthenticationError("Autenticacao necessaria.")

    claims = decode_token(token, "access")
    user = UserRepository(db.s).get(claims.subject)
    if user is None or not user.is_active:
        raise AuthenticationError("Sessao invalida.")
    # token_version invalida tokens antigos apos logout global/troca de senha.
    if user.token_version != claims.token_version:
        raise AuthenticationError("Sessao expirada.", error_code="token_stale")
    # O vinculo de tenant do token precisa refletir o estado atual no banco.
    if user.restaurant_id != claims.restaurant_id or user.role.value != claims.role:
        raise AuthenticationError("Sessao invalida.", error_code="claims_mismatch")

    g.current_user = user
    g.token_claims = claims
    return user


def current_user() -> User:
    user = getattr(g, "current_user", None)
    if user is None:
        raise AuthenticationError("Autenticacao necessaria.")
    return cast(User, user)


def current_user_optional() -> User | None:
    """Identidade opcional: rotas publicas que enriquecem a resposta se houver login."""
    if not request.cookies.get(ACCESS_COOKIE):
        return None
    try:
        return load_current_user()
    except AuthenticationError:
        return None


def current_restaurant_id() -> uuid.UUID:
    """restaurant_id vem SEMPRE do token, nunca do payload/URL do cliente."""
    user = current_user()
    if user.restaurant_id is None:
        raise AuthorizationError("Usuario nao esta vinculado a um restaurante.")
    return user.restaurant_id


def auth_required(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        load_current_user()
        return func(*args, **kwargs)

    return cast(F, wrapper)


def require_roles(*roles: Role) -> Callable[[F], F]:
    """RBAC explicito por rota. Sem este decorator a rota nao e considerada protegida."""
    allowed = frozenset(roles)

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = load_current_user()
            if user.role not in allowed:
                raise AuthorizationError("Permissao insuficiente para esta operacao.")
            return func(*args, **kwargs)

        wrapper.__rbac_roles__ = allowed  # type: ignore[attr-defined]
        return cast(F, wrapper)

    return decorator


def assert_same_restaurant(restaurant_id: uuid.UUID) -> uuid.UUID:
    """Bloqueia acesso cruzado entre tenants quando o id vem da URL."""
    scoped = current_restaurant_id()
    if scoped != restaurant_id:
        # 404 em vez de 403 para nao confirmar a existencia de recursos de outro tenant.
        from app.errors import NotFoundError

        raise NotFoundError("Restaurante nao encontrado.")
    return scoped
