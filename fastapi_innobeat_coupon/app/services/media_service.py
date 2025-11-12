from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import MediaAsset
from app.services import virus_scan_service

UPLOAD_DIR = Path("uploads/banners")


async def save_banner_asset(
    db: Session,
    file: UploadFile,
    *,
    uploaded_by: int | None,
) -> MediaAsset:
    contents = await file.read()
    if not contents:
        raise ValueError("업로드된 파일이 비어 있습니다.")
    if file.content_type and not file.content_type.startswith("image/"):
        raise ValueError("이미지 파일만 업로드할 수 있습니다.")

    virus_scan_service.scan_bytes(contents, file.filename or "banner.bin")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = _build_filename(file.filename or "banner.bin")
    path = UPLOAD_DIR / filename
    path.write_bytes(contents)

    asset = MediaAsset(
        file_name=file.filename or filename,
        storage_path=str(path),
        mime_type=file.content_type,
        width=None,
        height=None,
        uploaded_by=uploaded_by,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def list_media_assets(db: Session, *, cursor: int | None, limit: int) -> tuple[list[MediaAsset], int | None]:
    stmt = select(MediaAsset).order_by(MediaAsset.id.desc())
    if cursor:
        stmt = stmt.where(MediaAsset.id < cursor)
    rows = db.scalars(stmt.limit(limit + 1)).all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if (has_more and items) else None
    return items, next_cursor


def _build_filename(original: str) -> str:
    base = os.path.splitext(original)[0].replace(" ", "_")
    ext = os.path.splitext(original)[1] or ".bin"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base}_{timestamp}_{os.getpid()}{ext}"
