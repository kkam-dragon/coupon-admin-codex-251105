from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class AccessToken:
    token: str
    expires_at: datetime
    jti: str


@dataclass
class TokenPayload:
    subject: str
    expires_at: datetime
    issued_at: datetime
    jti: str


class TokenDecodeError(RuntimeError):
    pass


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> AccessToken:
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    jti = uuid4().hex
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return AccessToken(token=token, expires_at=expires, jti=jti)


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # noqa: PERF203 - explicit conversion needed
        raise TokenDecodeError("토큰 검증에 실패했습니다.") from exc

    subject = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")
    iat = payload.get("iat")
    if not subject or not jti or exp is None or iat is None:
        raise TokenDecodeError("토큰 페이로드가 올바르지 않습니다.")

    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    issued_at = datetime.fromtimestamp(int(iat), tz=timezone.utc)
    return TokenPayload(subject=str(subject), expires_at=expires_at, issued_at=issued_at, jti=str(jti))
