from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MediaUploadResponse(BaseModel):
    id: int
    file_name: str
    storage_path: str
    mime_type: str | None
    width: int | None = None
    height: int | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class MediaListFilters(BaseModel):
    cursor: int | None = Field(default=None, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class MediaListResponse(BaseModel):
    items: list[MediaUploadResponse]
    next_cursor: int | None
