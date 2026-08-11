"""AuthService: cadastro, login, refresh rotativo e revogacao."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from flask import current_app
from sqlalchemy.orm import Session

from app.errors import AuthenticationError, ConflictError
from app.models import Role, User
from app.repositories import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, StaffCreateRequest
from app.security.cookies import generate_csrf_token
from app.security.passwords import hash_password, needs_rehash, verify_password
from app.security.tokens import create_token, decode_token, revoke


@dataclass(frozen=True, slots=True)
class TokenBundle:
    access_token: str
    refresh_token: str
    csrf_token: str


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def register_customer(self, payload: RegisterRequest) -> User:
        """Cadastro publico cria apenas CUSTOMER (nunca aceita role do cliente)."""
        if self.users.email_exists(payload.email):
            raise ConflictError("Nao foi possivel concluir o cadastro.", error_code="conflict")
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            role=Role.CUSTOMER,
            restaurant_id=None,
        )
        return self.users.add(user)

    def create_staff_user(self, payload: StaffCreateRequest, restaurant_id: uuid.UUID) -> User:
        if self.users.email_exists(payload.email):
            raise ConflictError("Nao foi possivel criar o usuario.", error_code="conflict")
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            restaurant_id=restaurant_id,
        )
        return self.users.add(user)

    def authenticate(self, payload: LoginRequest) -> User:
        user = self.users.get_by_email(payload.email)
        password_hash = user.password_hash if user else None
        # verify_password sempre executa Argon2 (mesmo sem usuario) para nao vazar timing.
        if not verify_password(password_hash, payload.password) or user is None:
            raise AuthenticationError("Credenciais invalidas.", error_code="invalid_credentials")
        if not user.is_active:
            raise AuthenticationError("Conta desativada.", error_code="inactive_account")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)
            self.session.flush()
        return user

    def issue_tokens(self, user: User) -> TokenBundle:
        access, _, _ = create_token(
            user_id=user.id,
            role=user.role.value,
            restaurant_id=user.restaurant_id,
            token_version=user.token_version,
            token_type="access",  # noqa: S106 - tipo de token, nao credencial
            ttl_seconds=current_app.config["ACCESS_TOKEN_TTL_SECONDS"],
        )
        refresh, _, _ = create_token(
            user_id=user.id,
            role=user.role.value,
            restaurant_id=user.restaurant_id,
            token_version=user.token_version,
            token_type="refresh",  # noqa: S106 - tipo de token, nao credencial
            ttl_seconds=current_app.config["REFRESH_TOKEN_TTL_SECONDS"],
        )
        return TokenBundle(access, refresh, generate_csrf_token())

    def rotate_refresh(self, refresh_token: str) -> tuple[User, TokenBundle]:
        """Rotacao: o refresh usado e revogado imediatamente (detecta reuso)."""
        claims = decode_token(refresh_token, "refresh")
        user = self.users.get(claims.subject)
        if user is None or not user.is_active or user.token_version != claims.token_version:
            raise AuthenticationError("Sessao invalida.", error_code="invalid_session")
        revoke(claims.jti, claims.expires_at)
        return user, self.issue_tokens(user)

    def logout(self, access_token: str | None, refresh_token: str | None) -> None:
        for token, token_type in ((access_token, "access"), (refresh_token, "refresh")):
            if not token:
                continue
            try:
                claims = decode_token(token, token_type)  # type: ignore[arg-type]
            except AuthenticationError:
                continue
            revoke(claims.jti, claims.expires_at)
