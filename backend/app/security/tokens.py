"""Emissao/validacao de JWT e denylist de revogacao (Redis com fallback em memoria)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

import jwt
from flask import current_app

from app.errors import AuthenticationError
from app.extensions import get_redis

TokenType = Literal["access", "refresh"]
ALGORITHM = "HS256"
ISSUER = "mesas-filas-api"

#: Fallback de denylist quando nao ha Redis (dev/teste em processo unico).
_memory_denylist: dict[str, float] = {}


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: uuid.UUID
    role: str
    restaurant_id: uuid.UUID | None
    token_version: int
    jti: str
    token_type: TokenType
    expires_at: int


def _secret() -> str:
    return current_app.config["JWT_SECRET_KEY"]


def create_token(
    *,
    user_id: uuid.UUID,
    role: str,
    restaurant_id: uuid.UUID | None,
    token_version: int,
    token_type: TokenType,
    ttl_seconds: int,
) -> tuple[str, str, int]:
    """Retorna (token, jti, expires_at_epoch)."""
    now = int(time.time())
    expires_at = now + ttl_seconds
    jti = uuid.uuid4().hex
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "rid": str(restaurant_id) if restaurant_id else None,
        "tv": token_version,
        "jti": jti,
        "type": token_type,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": ISSUER,
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM), jti, expires_at


def decode_token(token: str, expected_type: TokenType) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "jti", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Sessao expirada.", error_code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Token invalido.", error_code="invalid_token") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError("Tipo de token invalido.", error_code="invalid_token")

    jti = str(payload["jti"])
    if is_revoked(jti):
        raise AuthenticationError("Token revogado.", error_code="token_revoked")

    restaurant_id = payload.get("rid")
    return TokenClaims(
        subject=uuid.UUID(str(payload["sub"])),
        role=str(payload.get("role", "")),
        restaurant_id=uuid.UUID(restaurant_id) if restaurant_id else None,
        token_version=int(payload.get("tv", 0)),
        jti=jti,
        token_type=expected_type,
        expires_at=int(payload["exp"]),
    )


def revoke(jti: str, expires_at: int) -> None:
    """Marca o jti como revogado ate o exp original (nao guarda nada apos isso)."""
    ttl = max(int(expires_at - time.time()), 1)
    redis = get_redis()
    if redis is not None:
        redis.setex(f"denylist:{jti}", ttl, "1")
        return
    _purge_memory_denylist()
    _memory_denylist[jti] = time.time() + ttl


def is_revoked(jti: str) -> bool:
    redis = get_redis()
    if redis is not None:
        return bool(redis.exists(f"denylist:{jti}"))
    _purge_memory_denylist()
    return jti in _memory_denylist


def _purge_memory_denylist() -> None:
    now = time.time()
    for key, expiry in list(_memory_denylist.items()):
        if expiry <= now:
            _memory_denylist.pop(key, None)


def reset_memory_denylist() -> None:
    """Usado somente por testes."""
    _memory_denylist.clear()
