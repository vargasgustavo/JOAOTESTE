"""Hashing de senha com Argon2id (parametros explicitos, sem defaults implicitos)."""

from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

#: Perfil equilibrado para API web: ~64 MiB, 3 iteracoes, 4 lanes.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

#: Hash descartavel usado para igualar o tempo de resposta quando o e-mail nao existe.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-equalization")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Verifica a senha; sem hash, gasta o mesmo tempo para evitar user enumeration."""
    if not password_hash:
        _safe_verify(_DUMMY_HASH, password)
        return False
    return _safe_verify(password_hash, password)


def _safe_verify(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:  # pragma: no cover
        return True
