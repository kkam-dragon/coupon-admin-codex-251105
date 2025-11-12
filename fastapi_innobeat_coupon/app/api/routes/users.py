from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.roles import RoleCode
from app.db.session import get_db
from app.schemas.users import UserCreate, UserRead
from app.services.audit_service import log_action
from app.services.user_service import create_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles({RoleCode.ADMIN.value})),
):
    try:
        user = create_user(db, payload, actor=current_user.username)
        log_action(
            db,
            user_id=current_user.id,
            action="user.create",
            target_type="user",
            target_id=str(user.id),
            commit=True,
        )
        return UserRead.model_validate(user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
