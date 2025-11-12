from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_value
from app.core.security import hash_password
from app.models.domain import User
from app.schemas.users import UserCreate


def create_user(db: Session, payload: UserCreate, actor: str | None = None) -> User:
    if db.scalar(select(User.id).where(User.username == payload.username)):
        raise ValueError("이미 사용 중인 아이디입니다.")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        enc_name=encrypt_value(payload.name) if payload.name else None,
        enc_email=encrypt_value(payload.email) if payload.email else None,
        enc_phone=encrypt_value(payload.phone) if payload.phone else None,
        status=payload.status,
        created_by=actor,
        updated_by=actor,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
