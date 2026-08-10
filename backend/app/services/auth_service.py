import secrets
from datetime import datetime, timezone
from typing import Any

import jwt
import redis
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask import current_app

from ..extensions import db
from ..models import User, UserRole
from ..repositories import UserRepository


class AuthService:
    def __init__(self):
        self._user_repo = UserRepository()

    def _get_hasher(self) -> PasswordHasher:
        return PasswordHasher(
            time_cost=current_app.config["ARGON2_TIME_COST"],
            memory_cost=current_app.config["ARGON2_MEMORY_COST"],
            parallelism=current_app.config["ARGON2_PARALLELISM"],
        )

    def _get_redis(self) -> redis.Redis:
        return redis.from_url(current_app.config["REDIS_URL"], decode_responses=True)

    def register(self, name: str, phone: str, password: str, role: str = "CUSTOMER",
                 email: str | None = None, restaurant_id: str | None = None) -> User:
        if self._user_repo.get_by_phone(phone):
            raise ValueError("Phone already registered")
        if email and self._user_repo.get_by_email(email):
            raise ValueError("Email already registered")

        hasher = self._get_hasher()
        password_hash = hasher.hash(password)

        user = self._user_repo.create(
            name=name,
            phone=phone,
            email=email,
            password_hash=password_hash,
            role=UserRole(role),
            restaurant_id=restaurant_id,
        )
        db.session.commit()
        return user

    def login(self, phone: str, password: str) -> tuple[str, str, "User"]:
        user = self._user_repo.get_by_phone(phone)
        if not user:
            raise ValueError("Invalid credentials")

        hasher = self._get_hasher()
        try:
            hasher.verify(user.password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            raise ValueError("Invalid credentials")

        if hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hasher.hash(password)
            db.session.commit()

        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)
        return access_token, refresh_token, user

    def _create_access_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.id,
            "role": user.role.value,
            "restaurant_id": user.restaurant_id,
            "type": "access",
            "iat": now,
            "exp": now + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(
            payload,
            current_app.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )

    def _create_refresh_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.id,
            "type": "refresh",
            "iat": now,
            "exp": now + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"],
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(
            payload,
            current_app.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

        r = self._get_redis()
        if r.exists(f"denylist:{payload['jti']}"):
            raise ValueError("Token revoked")

        return payload

    def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        payload = self.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")

        self._revoke_jti(payload["jti"], payload["exp"])

        user = self._user_repo.get_by_id(payload["sub"])
        if not user:
            raise ValueError("User not found")

        return self._create_access_token(user), self._create_refresh_token(user)

    def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        try:
            payload = self.decode_token(access_token)
            self._revoke_jti(payload["jti"], payload["exp"])
        except ValueError:
            pass

        if refresh_token:
            try:
                payload = self.decode_token(refresh_token)
                self._revoke_jti(payload["jti"], payload["exp"])
            except ValueError:
                pass

    def _revoke_jti(self, jti: str, exp: Any) -> None:
        r = self._get_redis()
        now = datetime.now(timezone.utc).timestamp()
        if isinstance(exp, (int, float)):
            exp_ts = float(exp)
        elif hasattr(exp, "timestamp"):
            # PyJWT may return a datetime object depending on config
            exp_ts = exp.timestamp()
        else:
            exp_ts = now + 3600
        ttl = max(int(exp_ts - now), 1)
        r.setex(f"denylist:{jti}", ttl, "1")
