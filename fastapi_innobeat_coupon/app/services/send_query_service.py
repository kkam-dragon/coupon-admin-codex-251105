from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.core.phone import mask_phone
from app.models.domain import Campaign, CampaignProduct, CampaignRecipient, CouponProduct
from app.schemas.send_query import (
    CampaignDetail,
    CampaignQueryFilters,
    CampaignQueryResponse,
    CampaignSummary,
    RecipientBrief,
)


def list_campaigns(db: Session, filters: CampaignQueryFilters) -> CampaignQueryResponse:
    stmt = select(Campaign).order_by(Campaign.id.desc())
    if filters.cursor:
        stmt = stmt.where(Campaign.id < filters.cursor)
    if filters.client_name:
        stmt = stmt.where(Campaign.client_name.ilike(f"%{filters.client_name}%"))
    if filters.event_name:
        stmt = stmt.where(Campaign.event_name.ilike(f"%{filters.event_name}%"))
    if filters.start_date:
        start_dt = datetime.combine(filters.start_date, time.min).replace(tzinfo=timezone.utc)
        stmt = stmt.where(Campaign.scheduled_at >= start_dt)
    if filters.end_date:
        end_dt = datetime.combine(filters.end_date, time.max).replace(tzinfo=timezone.utc)
        stmt = stmt.where(Campaign.scheduled_at <= end_dt)

    rows = list(db.scalars(stmt.limit(filters.limit + 1)))
    has_more = len(rows) > filters.limit
    campaigns = rows[: filters.limit]
    stats = _load_recipient_stats(db, [c.id for c in campaigns])
    products = _load_product_snapshots(db, [c.id for c in campaigns])

    items: list[CampaignSummary] = []
    for campaign in campaigns:
        stat = stats.get(campaign.id, {})
        product_snapshot = products.get(campaign.id, {"names": [], "unit_sum": Decimal("0")})
        validated = int(stat.get("validated", 0))
        estimated_amount = product_snapshot["unit_sum"] * Decimal(validated)
        items.append(
            CampaignSummary(
                id=campaign.id,
                client_name=campaign.client_name,
                event_name=campaign.event_name,
                scheduled_at=campaign.scheduled_at,
                status=campaign.status,
                total_recipients=int(stat.get("total", 0)),
                validated_count=validated,
                sent_count=int(stat.get("sent", 0)),
                product_names=product_snapshot["names"],
                estimated_amount=estimated_amount,
                cursor=campaign.id,
            )
        )

    next_cursor = campaigns[-1].id if has_more and campaigns else None
    return CampaignQueryResponse(items=items, next_cursor=next_cursor)


def get_campaign_detail(
    db: Session,
    campaign_id: int,
    recipient_limit: int = 100,
) -> CampaignDetail:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise ValueError("캠페인을 찾을 수 없습니다.")

    filters = CampaignQueryFilters(limit=1)
    filters.cursor = None
    stats = _load_recipient_stats(db, [campaign.id])
    products = _load_product_snapshots(db, [campaign.id])
    stat = stats.get(campaign.id, {})
    product_snapshot = products.get(campaign.id, {"names": [], "unit_sum": Decimal("0")})
    validated = int(stat.get("validated", 0))
    estimated_amount = product_snapshot["unit_sum"] * Decimal(validated)

    summary = CampaignSummary(
        id=campaign.id,
        client_name=campaign.client_name,
        event_name=campaign.event_name,
        scheduled_at=campaign.scheduled_at,
        status=campaign.status,
        total_recipients=int(stat.get("total", 0)),
        validated_count=validated,
        sent_count=int(stat.get("sent", 0)),
        product_names=product_snapshot["names"],
        estimated_amount=estimated_amount,
        cursor=campaign.id,
    )

    recipients = db.scalars(
        select(CampaignRecipient)
        .where(CampaignRecipient.campaign_id == campaign_id)
        .order_by(CampaignRecipient.id.desc())
        .limit(recipient_limit)
    ).all()
    recipient_items = [
        RecipientBrief(
            id=recipient.id,
            status=recipient.status,
            phone_masked=mask_phone(decrypt_value(recipient.enc_phone)),
        )
        for recipient in recipients
    ]

    return CampaignDetail(
        summary=summary,
        message_title=campaign.message_title,
        message_body=campaign.message_body,
        requester_name=decrypt_value(campaign.requester_name_enc),
        requester_phone_masked=mask_phone(decrypt_value(campaign.requester_phone_enc)),
        requester_email=decrypt_value(campaign.requester_email_enc),
        recipients=recipient_items,
    )


def _load_recipient_stats(db: Session, campaign_ids: Iterable[int]) -> dict[int, dict[str, int]]:
    ids = list(campaign_ids)
    if not ids:
        return {}
    stmt = (
        select(
            CampaignRecipient.campaign_id,
            func.count().label("total"),
            func.sum(case((CampaignRecipient.status == "VALIDATED", 1), else_=0)).label("validated"),
            func.sum(case((CampaignRecipient.status == "SENT", 1), else_=0)).label("sent"),
        )
        .where(CampaignRecipient.campaign_id.in_(ids))
        .group_by(CampaignRecipient.campaign_id)
    )
    rows = db.execute(stmt).all()
    stats: dict[int, dict[str, int]] = {}
    for row in rows:
        stats[row.campaign_id] = {
            "total": int(row.total or 0),
            "validated": int(row.validated or 0),
            "sent": int(row.sent or 0),
        }
    return stats


def _load_product_snapshots(db: Session, campaign_ids: Iterable[int]) -> dict[int, dict[str, object]]:
    ids = list(campaign_ids)
    if not ids:
        return {}
    stmt = (
        select(
            CampaignProduct.campaign_id,
            CouponProduct.name,
            CampaignProduct.unit_price,
        )
        .join(CouponProduct, CampaignProduct.coupon_product_id == CouponProduct.id)
        .where(CampaignProduct.campaign_id.in_(ids))
    )
    rows = db.execute(stmt).all()
    snapshots: dict[int, dict[str, object]] = {}
    for row in rows:
        snapshot = snapshots.setdefault(
            row.campaign_id,
            {"names": [], "unit_sum": Decimal("0")},
        )
        snapshot["names"].append(row.name)
        snapshot["unit_sum"] += row.unit_price or Decimal("0")
    return snapshots
