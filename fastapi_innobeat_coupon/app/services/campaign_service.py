from __future__ import annotations

from datetime import datetime
from secrets import token_hex

from sqlalchemy.orm import Session

from app.models.domain import Campaign, CampaignProduct
from app.schemas.campaigns import CampaignCreate


def _generate_campaign_key() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}{token_hex(4)}"


def create_campaign(db: Session, payload: CampaignCreate) -> Campaign:
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
