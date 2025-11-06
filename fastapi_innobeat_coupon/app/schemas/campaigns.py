from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field


class CampaignProductItem(BaseModel):
    coupon_product_id: int = Field(..., description="연결할 쿠폰 상품 ID")
    unit_price: Decimal = Field(..., ge=0)


class CampaignCreate(BaseModel):
    client_id: int
    event_name: str = Field(..., max_length=100)
    scheduled_at: datetime | None = None
    sender_number: str = Field(..., max_length=20)
    message_title: str = Field(..., max_length=120)
    message_body: str
    product_items: List[CampaignProductItem] = Field(default_factory=list)


class CampaignRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    campaign_key: str
    client_id: int
    event_name: str
    scheduled_at: datetime | None
    sender_number: str
    message_title: str
    status: str
