from __future__ import annotations

import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.uploads import RecipientUploadSummary, RecipientValidationErrorRead
from app.services.upload_service import (
    generate_validation_error_csv,
    handle_recipient_upload,
    list_validation_errors,
)

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


@router.get(
    "/{campaign_id}/recipients/errors",
    response_model=list[RecipientValidationErrorRead],
)
def get_recipient_errors(campaign_id: int, db: Session = Depends(get_db)):
    """
    최신 업로드 배치에서 발생한 검증 오류 목록을 제공한다.
    """
    errors = list_validation_errors(db, campaign_id)
    return [
        RecipientValidationErrorRead.model_validate(err)
        for err in errors
    ]


@router.get("/{campaign_id}/recipients/errors/export")
def export_errors_csv(campaign_id: int, db: Session = Depends(get_db)):
    """
    검증 오류 목록을 CSV로 다운로드한다.
    """
    csv_text = generate_validation_error_csv(db, campaign_id)
    if not csv_text.strip():
        raise HTTPException(status_code=404, detail="오류 데이터가 없습니다.")
    filename = f"campaign_{campaign_id}_validation_errors.csv"
    stream = io.BytesIO(csv_text.encode("utf-8-sig"))
    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
