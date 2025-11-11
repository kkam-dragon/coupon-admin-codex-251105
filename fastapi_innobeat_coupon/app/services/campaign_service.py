from __future__ import annotations

import re
from datetime import datetime
from secrets import token_hex

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_value, hash_value
from app.models.domain import Campaign, CampaignProduct, Client, CouponProduct
from app.schemas.campaigns import CampaignCreate


def _generate_campaign_key() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}{token_hex(4)}"


def create_campaign(db: Session, payload: CampaignCreate, actor: str | None = None) -> Campaign:
    client_name_snapshot = payload.client_name.strip()
    client = None
    if payload.client_id is not None:
        client = db.get(Client, payload.client_id)
        if not client:
            raise ValueError("�������� �ʴ� Ŭ���̾�Ʈ�Դϴ�.")
        if not client_name_snapshot:
            client_name_snapshot = client.name

    if not payload.product_items:
        raise ValueError("�ּ� 1���� ��ǰ�� �����ؾ� �մϴ�.")

    product_ids = {item.coupon_product_id for item in payload.product_items}
    existing_ids = set(
        db.scalars(
            select(CouponProduct.id).where(CouponProduct.id.in_(product_ids))
        )
    )
    if product_ids - existing_ids:
        raise ValueError("������ ��ǰ �� �Ϻΰ� �������� �ʽ��ϴ�.")

    normalized_phone = _normalize_phone(payload.requester_phone)

    campaign = Campaign(
        campaign_key=_generate_campaign_key(),
        client_id=payload.client_id if client else None,
        client_name=client_name_snapshot,
        event_name=payload.event_name,
        scheduled_at=payload.scheduled_at,
        sender_number=payload.sender_number,
        message_title=payload.message_title,
        message_body=payload.message_body,
        sales_manager_name=payload.sales_manager_name,
        requester_name_enc=encrypt_value(payload.requester_name),
        requester_phone_enc=encrypt_value(normalized_phone)
        if normalized_phone
        else None,
        requester_phone_hash=hash_value(normalized_phone)
        if normalized_phone
        else None,
        requester_email_enc=encrypt_value(payload.requester_email)
        if payload.requester_email
        else None,
        status="DRAFT",
        created_by=actor,
        updated_by=actor,
    )
    db.add(campaign)
    db.flush()

    for item in payload.product_items:
        campaign_product = CampaignProduct(
            campaign_id=campaign.id,
            coupon_product_id=item.coupon_product_id,
            unit_price=item.unit_price,
            settle_price=None,
            created_by=actor,
            updated_by=actor,
        )
        db.add(campaign_product)

    db.commit()
    db.refresh(campaign)
    return campaign


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits or None
