from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api import deps
from app.core.roles import DEFAULT_READ_ROLES, DEFAULT_WRITE_ROLES
from app.db.session import get_db
from app.schemas.media import MediaListFilters, MediaListResponse, MediaUploadResponse
from app.services import media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/banners", response_model=MediaUploadResponse)
async def upload_banner(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_WRITE_ROLES)),
):
    try:
        asset = await media_service.save_banner_asset(
            db,
            file,
            uploaded_by=current_user.id,
        )
        return MediaUploadResponse.model_validate(asset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/banners", response_model=MediaListResponse)
def list_banners(
    filters: MediaListFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_READ_ROLES)),
):
    items, next_cursor = media_service.list_media_assets(
        db,
        cursor=filters.cursor,
        limit=filters.limit,
    )
    return MediaListResponse(
        items=[MediaUploadResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )
