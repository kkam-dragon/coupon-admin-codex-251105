from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CampaignQueryFilters(BaseModel):
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    client_name: str | None = Field(default=None, max_length=100)
    event_name: str | None = Field(default=None, max_length=100)
    cursor: int | None = Field(default=None, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class CampaignSummary(BaseModel):
    id: int
    client_name: str | None
    event_name: str
    scheduled_at: datetime | None
    status: str
    total_recipients: int
    validated_count: int
    sent_count: int
    product_names: list[str]
    estimated_amount: Decimal
    cursor: int


class CampaignQueryResponse(BaseModel):
    items: list[CampaignSummary]
    next_cursor: int | None


class RecipientBrief(BaseModel):
    id: int
    status: str
    phone_masked: str | None


class CampaignDetail(BaseModel):
    summary: CampaignSummary
    message_title: str
    message_body: str
    requester_name: str | None
    requester_phone_masked: str | None
    requester_email: str | None
    recipients: list[RecipientBrief]
