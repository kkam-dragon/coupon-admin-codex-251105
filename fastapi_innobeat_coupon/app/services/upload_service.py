from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.uploads import RecipientUploadSummary


def handle_recipient_upload(
    db: Session,
    campaign_id: int,
    filename: str,
) -> RecipientUploadSummary:
    # TODO: CSV/엑셀 파싱 및 검증 로직 구현
    # 현재는 골격만 제공한다.
    return RecipientUploadSummary(
        batch_id=None,
        uploaded_total=0,
        valid_count=0,
        invalid_count=0,
    )
