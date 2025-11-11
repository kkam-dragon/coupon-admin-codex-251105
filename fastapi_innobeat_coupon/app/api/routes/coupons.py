from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.roles import DEFAULT_READ_ROLES, DEFAULT_WRITE_ROLES
from app.db.session import get_db
from app.services.coupon_status_service import cancel_coupon, refresh_coupon_status
from app.services.audit_service import log_action

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("/{coupon_issue_id}/status")
def refresh_status(
    coupon_issue_id: int,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_READ_ROLES)),
):
    try:
        result = refresh_coupon_status(db, coupon_issue_id)
        log_action(
            db,
            user_id=current_user.id,
            action="coupon.status.refresh",
            target_type="coupon_issue",
            target_id=str(coupon_issue_id),
            commit=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{coupon_issue_id}/cancel")
def cancel_coupon_endpoint(
    coupon_issue_id: int,
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_WRITE_ROLES)),
):
    try:
        result = cancel_coupon(db, coupon_issue_id, reason)
        log_action(
            db,
            user_id=current_user.id,
            action="coupon.cancel",
            target_type="coupon_issue",
            target_id=str(coupon_issue_id),
            commit=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
