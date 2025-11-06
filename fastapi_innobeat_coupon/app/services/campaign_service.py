from __future__ import annotations

from datetime import datetime
from secrets import token_hex

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Campaign, CampaignProduct, Client, CouponProduct
from app.schemas.campaigns import CampaignCreate


def _generate_campaign_key() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}{token_hex(4)}"


def create_campaign(db: Session, payload: CampaignCreate) -> Campaign:
    client = db.get(Client, payload.client_id)
    if not client:
        raise ValueError("존재하지 않는 클라이언트입니다.")
    if not payload.product_items:
        raise ValueError("최소 1개의 상품을 선택해야 합니다.")

    product_ids = {item.coupon_product_id for item in payload.product_items}
    existing_ids = set(
        db.scalars(
            select(CouponProduct.id).where(CouponProduct.id.in_(product_ids))
        )
    )
    if product_ids - existing_ids:
        raise ValueError("선택한 상품 중 일부가 존재하지 않습니다.")

    campaign = Campaign(
        campaign_key=_generate_campaign_key(),
        client_id=payload.client_id,
        event_name=payload.event_name,
        scheduled_at=payload.scheduled_at,
        sender_number=payload.sender_number,
        message_title=payload.message_title,
        message_body=payload.message_body,
        status="DRAFT",
    )
    db.add(campaign)
    db.flush()

    for item in payload.product_items:
        campaign_product = CampaignProduct(
            campaign_id=campaign.id,
            coupon_product_id=item.coupon_product_id,
            unit_price=item.unit_price,
            settle_price=None,
        )
        db.add(campaign_product)

    db.commit()
    db.refresh(campaign)
    return campaign
