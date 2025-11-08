from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.models.domain import CouponIssue, CouponStatusHistory
from app.services import coufun_service


def refresh_coupon_status(db: Session, coupon_issue_id: int) -> dict:
    issue = db.get(CouponIssue, coupon_issue_id)
    if not issue:
        raise ValueError("쿠폰 발급 건을 찾을 수 없습니다.")
    barcode = decrypt_value(issue.barcode_enc)
    if not barcode:
        raise ValueError("바코드 정보가 없습니다.")

    status = coufun_service.get_coupon_status(barcode)
    issue.status = status.status

    history = CouponStatusHistory(
        coupon_issue_id=issue.id,
        status=status.status,
        status_source="COUFUN",
        status_at=datetime.now(timezone.utc),
        memo=f"remain={status.remain_amount}",
    )
    db.add(history)
    db.commit()
    return {
        "barcode": barcode,
        "status": status.status,
        "remain_amount": status.remain_amount,
    }


def cancel_coupon(db: Session, coupon_issue_id: int, reason: str | None = None) -> dict:
    issue = db.get(CouponIssue, coupon_issue_id)
    if not issue:
        raise ValueError("쿠폰 발급 건을 찾을 수 없습니다.")
    barcode = decrypt_value(issue.barcode_enc)
    if not barcode:
        raise ValueError("바코드 정보가 없습니다.")

    status = coufun_service.cancel_coupon(barcode, reason)
    issue.status = status.status

    history = CouponStatusHistory(
        coupon_issue_id=issue.id,
        status=status.status,
        status_source="COUFUN",
        status_at=datetime.now(timezone.utc),
        memo=reason or "cancel_coupon",
    )
    db.add(history)
    db.commit()
    return {"barcode": barcode, "status": status.status}
