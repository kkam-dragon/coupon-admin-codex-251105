from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RecipientUploadSummary(BaseModel):
    uploaded_total: int = Field(..., ge=0)
    valid_count: int = Field(..., ge=0)
    invalid_count: int = Field(..., ge=0)
    batch_id: int | None = None
    errors: list[str] = Field(default_factory=list)


class RecipientValidationErrorRead(BaseModel):
    model_config = {"from_attributes": True}

    row_number: int
    raw_phone: str | None
    raw_name: str | None
    reason: str
    created_at: datetime
