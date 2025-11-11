from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import DEFAULT_READ_ROLES
from app.core.security import TokenDecodeError, decode_access_token
from app.db.session import get_db
from app.models.domain import AuthSession, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass
class AuthenticatedUser:
    user: User
    roles: set[str]
    session: AuthSession
    token_jti: str

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def username(self) -> str:
        return self.user.username


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AuthenticatedUser:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")
    try:
        payload = decode_access_token(token)
    except TokenDecodeError as exc:
        raise unauthorized from exc

    session = db.scalar(select(AuthSession).where(AuthSession.jwt_id == payload.jti))
    if not session or session.expires_at <= datetime.now(timezone.utc):
        raise unauthorized

    user = db.get(User, int(payload.subject))
    if not user or user.status != "ACTIVE":
        raise unauthorized
    if session.user_id != user.id:
        raise unauthorized

    role_codes = {role.code for role in (user.roles or [])}
    return AuthenticatedUser(user=user, roles=role_codes, session=session, token_jti=session.jwt_id)


def require_roles(allowed_roles: set[str] | None = None):
    allowed = allowed_roles or DEFAULT_READ_ROLES

    def _dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not current_user.roles.intersection(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
        return current_user

    return _dependency
