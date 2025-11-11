from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.roles import DEFAULT_READ_ROLES, DEFAULT_WRITE_ROLES
from app.db.session import get_db
from app.schemas.cs import (
    CsActionResponse,
    CsChangePhoneRequest,
    CsNoteRequest,
    CsResendRequest,
    CsResendResponse,
    CsSearchResponse,
)
from app.services import cs_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/cs", tags=["cs"])


@router.get("/coupons/search", response_model=CsSearchResponse)
def search_coupon(
    phone: str | None = None,
    order_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_READ_ROLES)),
):
    try:
        result = cs_service.search_coupon_issue(db, phone=phone, order_id=order_id)
        log_action(
            db,
            user_id=current_user.id,
            action="cs.search",
            target_type="coupon_issue",
            target_id=str(result.coupon_issue_id),
            commit=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/coupons/{coupon_issue_id}/resend", response_model=CsResendResponse)
def resend_coupon(
    coupon_issue_id: int,
    payload: CsResendRequest,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_WRITE_ROLES)),
):
    try:
        result = cs_service.resend_coupon(
            db,
            coupon_issue_id=coupon_issue_id,
            performed_by=current_user.id,
            reason=payload.reason,
        )
        log_action(
            db,
            user_id=current_user.id,
            action="cs.resend",
            target_type="coupon_issue",
            target_id=str(coupon_issue_id),
            commit=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/coupons/{coupon_issue_id}/change-phone", response_model=CsActionResponse)
def change_phone(
    coupon_issue_id: int,
    payload: CsChangePhoneRequest,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_WRITE_ROLES)),
):
    try:
        result = cs_service.change_recipient_phone(
            db,
            coupon_issue_id=coupon_issue_id,
            new_phone=payload.new_phone,
            performed_by=current_user.id,
            reason=payload.reason,
        )
        log_action(
            db,
            user_id=current_user.id,
            action="cs.change_phone",
            target_type="coupon_issue",
            target_id=str(coupon_issue_id),
            commit=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/coupons/{coupon_issue_id}/notes", response_model=CsActionResponse)
def add_note(
    coupon_issue_id: int,
    payload: CsNoteRequest,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_WRITE_ROLES)),
):
    try:
        result = cs_service.add_note(
            db,
            coupon_issue_id=coupon_issue_id,
            memo=payload.memo,
            performed_by=current_user.id,
        )
        log_action(
            db,
            user_id=current_user.id,
            action="cs.note",
            target_type="coupon_issue",
            target_id=str(coupon_issue_id),
            commit=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
