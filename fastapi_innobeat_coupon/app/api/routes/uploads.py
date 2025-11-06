from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.uploads import RecipientUploadSummary
from app.services.upload_service import handle_recipient_upload

router = APIRouter(prefix="/campaigns", tags=["recipients"])


@router.post("/{campaign_id}/recipients/upload", response_model=RecipientUploadSummary)
async def upload_recipients(
    campaign_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """
    수신자 파일 업로드 엔드포인트 (현재는 요약 정보만 반환하는 골격 상태).
    """
    file_bytes = await file.read()
    try:
        summary = handle_recipient_upload(
            db,
            campaign_id=campaign_id,
            filename=file.filename,
            file_bytes=file_bytes,
        )
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
