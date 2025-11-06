from __future__ import annotations

from pydantic import BaseModel, Field


class RecipientUploadSummary(BaseModel):
    uploaded_total: int = Field(..., ge=0)
    valid_count: int = Field(..., ge=0)
    invalid_count: int = Field(..., ge=0)
    batch_id: int | None = None
    errors: list[str] = Field(default_factory=list)
