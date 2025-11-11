from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CsSearchResponse(BaseModel):
    coupon_issue_id: int
    campaign_id: int
    campaign_name: str | None
    recipient_id: int
    phone_masked: str | None
    barcode_masked: str | None
    status: str
    order_id: str
    valid_end_date: datetime | None


class CsResendRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class CsResendResponse(BaseModel):
    client_key: str
    queued: bool


class CsChangePhoneRequest(BaseModel):
    new_phone: str = Field(..., max_length=20)
    reason: str | None = Field(default=None, max_length=255)


class CsNoteRequest(BaseModel):
    memo: str = Field(..., max_length=500)


class CsActionResponse(BaseModel):
    action_id: int
    action_type: str
