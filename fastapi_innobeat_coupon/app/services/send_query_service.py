from __future__ import annotations

import csv
from datetime import datetime, time, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.core.phone import mask_phone
from app.models.domain import (
    Campaign,
    CampaignProduct,
    CampaignRecipient,
    CouponIssue,
    CouponProduct,
    ReportExport,
)
from app.schemas.send_query import (
    CampaignDetail,
    CampaignQueryFilters,
    CampaignQueryResponse,
    CampaignSummary,
    RecipientBrief,
)
EXPORT_DIR = Path("temp/exports/send_query")


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
    valid_until_map = _load_valid_until_map(db, [c.id for c in campaigns])

    items: list[CampaignSummary] = []
    for campaign in campaigns:
        stat = stats.get(campaign.id, {})
        product_snapshot = products.get(
            campaign.id,
            {"names": [], "unit_sum": Decimal("0"), "unit_prices": [], "valid_days": []},
        )
        validated = int(stat.get("validated", 0))
        unit_price = _resolve_unit_price(product_snapshot)
        total_amount = (unit_price or Decimal("0")) * Decimal(validated)
        items.append(
            CampaignSummary(
                id=campaign.id,
                client_name=campaign.client_name,
                event_name=campaign.event_name,
                scheduled_at=campaign.scheduled_at,
                dispatch_at=campaign.scheduled_at,
                valid_until=valid_until_map.get(campaign.id)
                or _estimate_valid_until(campaign, product_snapshot),
                status=campaign.status,
                total_recipients=int(stat.get("total", 0)),
                validated_count=validated,
                sent_count=int(stat.get("sent", 0)),
                product_names=product_snapshot["names"],
                unit_price=unit_price,
                total_amount=total_amount,
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
    valid_until_map = _load_valid_until_map(db, [campaign.id])
    stat = stats.get(campaign.id, {})
    product_snapshot = products.get(
        campaign.id,
        {"names": [], "unit_sum": Decimal("0"), "unit_prices": [], "valid_days": []},
    )
    validated = int(stat.get("validated", 0))
    unit_price = _resolve_unit_price(product_snapshot)
    total_amount = (unit_price or Decimal("0")) * Decimal(validated)

    summary = CampaignSummary(
        id=campaign.id,
        client_name=campaign.client_name,
        event_name=campaign.event_name,
        scheduled_at=campaign.scheduled_at,
        dispatch_at=campaign.scheduled_at,
        valid_until=valid_until_map.get(campaign.id) or _estimate_valid_until(campaign, product_snapshot),
        status=campaign.status,
        total_recipients=int(stat.get("total", 0)),
        validated_count=validated,
        sent_count=int(stat.get("sent", 0)),
        product_names=product_snapshot["names"],
        unit_price=unit_price,
        total_amount=total_amount,
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


def export_campaigns_to_csv(
    db: Session,
    filters: CampaignQueryFilters,
    *,
    requested_by: int | None,
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_old_exports()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"send_query_{timestamp}.csv"
    export_path = EXPORT_DIR / filename

    local_filters = CampaignQueryFilters(**filters.model_dump())
    local_filters.limit = max(local_filters.limit, 100)
    cursor = None
    row_count = 0

    with export_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "dispatch_at",
                "valid_until",
                "client_name",
                "event_name",
                "products",
                "quantity",
                "unit_price",
                "total_amount",
                "status",
            ]
        )
        while True:
            local_filters.cursor = cursor
            page = list_campaigns(db, local_filters)
            for item in page.items:
                writer.writerow(
                    [
                        item.dispatch_at.isoformat() if item.dispatch_at else "",
                        item.valid_until.isoformat() if item.valid_until else "",
                        item.client_name or "",
                        item.event_name,
                        ", ".join(item.product_names),
                        item.validated_count,
                        f"{item.unit_price:.2f}" if item.unit_price is not None else "",
                        f"{item.total_amount:.2f}",
                        item.status,
                    ]
                )
                row_count += 1
            cursor = page.next_cursor
            if not cursor:
                break

    now = datetime.now(timezone.utc)
    report = ReportExport(
        report_type="SEND_QUERY",
        filter_payload=filters.model_dump(),
        row_count=row_count,
        status="COMPLETED",
        requested_by=requested_by,
        requested_at=now,
        completed_at=now,
        file_path=str(export_path),
    )
    db.add(report)
    db.commit()
    return export_path


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
            CouponProduct.valid_days,
        )
        .join(CouponProduct, CampaignProduct.coupon_product_id == CouponProduct.id)
        .where(CampaignProduct.campaign_id.in_(ids))
    )
    rows = db.execute(stmt).all()
    snapshots: dict[int, dict[str, object]] = {}
    for row in rows:
        snapshot = snapshots.setdefault(
            row.campaign_id,
            {"names": [], "unit_sum": Decimal("0"), "unit_prices": [], "valid_days": []},
        )
        snapshot["names"].append(row.name)
        snapshot["unit_sum"] += row.unit_price or Decimal("0")
        snapshot["unit_prices"].append(row.unit_price or Decimal("0"))
        if row.valid_days is not None:
            snapshot["valid_days"].append(int(row.valid_days))
    return snapshots


def _load_valid_until_map(db: Session, campaign_ids: Iterable[int]) -> dict[int, datetime | None]:
    ids = list(campaign_ids)
    if not ids:
        return {}
    stmt = (
        select(
            CouponIssue.campaign_id,
            func.max(CouponIssue.valid_end_date).label("valid_until"),
        )
        .where(CouponIssue.campaign_id.in_(ids))
        .group_by(CouponIssue.campaign_id)
    )
    rows = db.execute(stmt).all()
    return {row.campaign_id: row.valid_until for row in rows if row.valid_until}


def _resolve_unit_price(snapshot: dict[str, object]) -> Decimal | None:
    prices: list[Decimal] = snapshot.get("unit_prices", [])  # type: ignore[arg-type]
    if not prices:
        return None
    if len(prices) == 1:
        return Decimal(prices[0])
    total = sum(prices, Decimal("0"))
    return (total / Decimal(len(prices))).quantize(Decimal("0.01"))


def _estimate_valid_until(campaign: Campaign, snapshot: dict[str, object]) -> datetime | None:
    valid_days: list[int] = snapshot.get("valid_days", [])  # type: ignore[arg-type]
    if not valid_days or not campaign.scheduled_at:
        return None
    days = max(valid_days)
    return campaign.scheduled_at + timedelta(days=days)


def _cleanup_old_exports(ttl_hours: int = 24) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    if not EXPORT_DIR.exists():
        return
    for path in EXPORT_DIR.glob("send_query_*.csv"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue
