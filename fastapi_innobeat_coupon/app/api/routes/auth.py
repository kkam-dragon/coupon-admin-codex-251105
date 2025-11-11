from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, TokenUser
from app.services import auth_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, payload.username, payload.password)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if not user:
        log_action(
            db,
            user_id=None,
            action="login",
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    auth_service.ensure_roles_loaded(user)
    token = auth_service.issue_login_token(
        db,
        user=user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    role_codes = list(auth_service.list_role_codes(user))
    log_action(
        db,
        user_id=user.id,
        action="login",
        ip_address=client_ip,
        user_agent=user_agent,
        success=True,
        commit=True,
    )
    return TokenResponse(
        access_token=token.token,
        token_type="bearer",
        expires_at=token.expires_at,
        user=TokenUser(id=user.id, username=user.username, roles=role_codes),
    )


@router.post("/logout")
def logout(current_user: deps.AuthenticatedUser = Depends(deps.get_current_user), db: Session = Depends(get_db)):
    auth_service.revoke_session(db, current_user.token_jti)
    log_action(
        db,
        user_id=current_user.id,
        action="logout",
        success=True,
        commit=True,
    )
    return {"status": "ok"}
