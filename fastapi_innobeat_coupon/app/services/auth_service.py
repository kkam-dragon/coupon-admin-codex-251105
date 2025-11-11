from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AccessToken, create_access_token, verify_password
from app.models.domain import AuthSession, Role, User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        return None
    if user.status != "ACTIVE":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def issue_login_token(
    db: Session,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> AccessToken:
    token = create_access_token(str(user.id))
    session = AuthSession(
        user_id=user.id,
        jwt_id=token.jti,
        expires_at=token.expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(user)
    return token


def revoke_session(db: Session, jwt_id: str) -> None:
    session = db.scalar(select(AuthSession).where(AuthSession.jwt_id == jwt_id))
    if session:
        db.delete(session)
        db.commit()


def list_role_codes(user: User) -> set[str]:
    if not user.roles:
        return set()
    return {role.code for role in user.roles}


def ensure_roles_loaded(user: User) -> Iterable[Role]:
    # 관계 접근을 트리거하여 lazy-loading 시점 오류를 피한다.
    return user.roles or []
