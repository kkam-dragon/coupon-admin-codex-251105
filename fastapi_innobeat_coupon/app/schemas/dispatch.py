from __future__ import annotations

from pydantic import BaseModel


class DispatchError(BaseModel):
    recipient_id: int
    reason: str


class DispatchSummary(BaseModel):
    enqueued: int
    failed: int
    errors: list[DispatchError]
