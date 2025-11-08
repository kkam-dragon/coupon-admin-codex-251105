from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.models.domain import (
    CampaignProduct,
    CouponIssue,
    CouponProduct,
    CouponStatusHistory,
)
from app.services import coufun_service


def refresh_coupon_status(db: Session, coupon_issue_id: int) -> dict:
    issue = db.get(CouponIssue, coupon_issue_id)
    if not issue:
        raise ValueError("쿠폰 발급 정보를 찾을 수 없습니다.")
    barcode = decrypt_value(issue.barcode_enc)
    if not barcode:
        raise ValueError("바코드 복호화에 실패했습니다.")

    goods_id = _resolve_goods_id(db, issue.campaign_id)
    status = coufun_service.get_coupon_status(goods_id, barcode)
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
        "status_label": status.status_label,
        "remain_amount": status.remain_amount,
        "coupon_type": status.coupon_type,
    }


def cancel_coupon(db: Session, coupon_issue_id: int, reason: str | None = None) -> dict:
    issue = db.get(CouponIssue, coupon_issue_id)
    if not issue:
        raise ValueError("쿠폰 발급 정보를 찾을 수 없습니다.")
    barcode = decrypt_value(issue.barcode_enc)
    if not barcode:
        raise ValueError("바코드 복호화에 실패했습니다.")

    goods_id = _resolve_goods_id(db, issue.campaign_id)
    status = coufun_service.cancel_coupon(goods_id, barcode, reason)
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
    return {
        "barcode": barcode,
        "status": status.status,
        "status_label": status.status_label,
    }


def _resolve_goods_id(db: Session, campaign_id: int) -> str:
    goods_id = db.scalar(
        select(CouponProduct.goods_id)
        .join(CampaignProduct, CampaignProduct.coupon_product_id == CouponProduct.id)
        .where(CampaignProduct.campaign_id == campaign_id)
    )
    if not goods_id:
        raise ValueError("캠페인에 연결된 COUFUN GOODS_ID를 찾을 수 없습니다.")
    return goods_id
