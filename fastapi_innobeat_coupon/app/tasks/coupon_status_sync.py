from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.crypto import decrypt_value
from app.db.session import SessionLocal
from app.models.domain import CampaignProduct, CouponIssue, CouponProduct, CouponStatusHistory
from app.services import coufun_service

logger = logging.getLogger(__name__)
TRACKING_STATUSES = {"ISSUED", "SENT", "DELIVERED", "REUSABLE"}


def run_coupon_status_sync_job() -> None:
    if not settings.coupon_status_sync_enabled:
        return

    session = SessionLocal()
    try:
        issues = session.scalars(
            select(CouponIssue)
            .where(CouponIssue.status.in_(TRACKING_STATUSES))
            .order_by(CouponIssue.updated_at.asc())
            .limit(settings.coupon_status_sync_batch_size)
        ).all()
        if not issues:
            return

        for issue in issues:
            try:
                _sync_issue(session, issue)
            except Exception:  # noqa: BLE001
                logger.exception("쿠폰 상태 동기화 실패 (issue_id=%s)", issue.id)
        session.commit()
    finally:
        session.close()


def _sync_issue(session: SessionLocal, issue: CouponIssue) -> None:
    goods_id = _resolve_goods_id(session, issue.campaign_id)
    barcode = decrypt_value(issue.barcode_enc)
    if not goods_id or not barcode:
        return
    status = coufun_service.get_coupon_status(goods_id, barcode)
    issue.status = status.status
    if status.valid_end_date:
        issue.valid_end_date = status.valid_end_date
    history = CouponStatusHistory(
        coupon_issue_id=issue.id,
        status=status.status,
        status_source="COUFUN_SYNC",
        status_at=datetime.now(timezone.utc),
        memo=status.status_label,
    )
    session.add(history)


def _resolve_goods_id(session: SessionLocal, campaign_id: int) -> str | None:
    return session.scalar(
        select(CouponProduct.goods_id)
        .join(CampaignProduct, CampaignProduct.coupon_product_id == CouponProduct.id)
        .where(CampaignProduct.campaign_id == campaign_id)
    )
