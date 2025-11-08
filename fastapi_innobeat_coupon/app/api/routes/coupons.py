from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.coupon_status_service import cancel_coupon, refresh_coupon_status

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("/{coupon_issue_id}/status")
def refresh_status(coupon_issue_id: int, db: Session = Depends(get_db)):
    try:
        return refresh_coupon_status(db, coupon_issue_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{coupon_issue_id}/cancel")
def cancel_coupon_endpoint(
    coupon_issue_id: int,
    reason: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        return cancel_coupon(db, coupon_issue_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
