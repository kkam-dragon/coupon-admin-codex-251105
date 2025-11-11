from __future__ import annotations

import csv
import io
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_value, hash_value
from app.core.phone import is_valid_phone
from app.models.domain import (
    Campaign,
    CampaignRecipient,
    RecipientBatch,
    RecipientValidationError,
)
from app.schemas.uploads import RecipientUploadSummary

MAX_UPLOAD_ROWS = 20_000


def _parse_csv(file_bytes: bytes) -> Iterable[tuple[int, str, str]]:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    expected_headers = {"phone", "name"}
    if not reader.fieldnames or not expected_headers.issubset({h.strip() for h in reader.fieldnames}):
        raise ValueError("CSV 헤더에 phone,name 컬럼이 필요합니다.")
    for idx, row in enumerate(reader, start=2):  # header is row 1
        phone = (row.get("phone") or "").strip()
        name = (row.get("name") or "").strip()
        yield idx, phone, name


def handle_recipient_upload(
    db: Session,
    campaign_id: int,
    filename: str,
    file_bytes: bytes,
) -> RecipientUploadSummary:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise ValueError("캠페인을 찾을 수 없습니다.")
    if not file_bytes:
        raise ValueError("업로드된 파일이 비어 있습니다.")

    batch = RecipientBatch(
        campaign_id=campaign_id,
        upload_type="FILE",
        original_filename=filename,
    )
    db.add(batch)
    db.flush()

    uploaded_total = 0
    valid_count = 0
    invalid_count = 0
    errors: list[str] = []
    error_records: List[RecipientValidationError] = []
    seen_hashes: set[bytes] = set()

    for row_number, phone, name in _parse_csv(file_bytes):
        uploaded_total += 1
        if uploaded_total > MAX_UPLOAD_ROWS:
            raise ValueError(f"CSV 1회 업로드는 최대 {MAX_UPLOAD_ROWS:,}건까지 지원합니다.")

        if not is_valid_phone(phone):
            invalid_count += 1
            errors.append(f"{row_number}행: 전화번호 형식이 올바르지 않습니다.")
            error_records.append(
                RecipientValidationError(
                    batch_id=batch.id,
                    row_number=row_number,
                    raw_phone=phone,
                    raw_name=name or None,
                    reason="INVALID_PHONE_FORMAT",
                )
            )
            continue

        phone_hash = hash_value(phone)
        if phone_hash in seen_hashes:
            _append_error(
                batch_id=batch.id,
                row_number=row_number,
                raw_phone=phone,
                raw_name=name,
                reason="DUPLICATE_IN_FILE",
                errors=errors,
                error_records=error_records,
            )
            invalid_count += 1
            continue

        if _phone_exists(db, campaign_id, phone_hash):
            _append_error(
                batch_id=batch.id,
                row_number=row_number,
                raw_phone=phone,
                raw_name=name,
                reason="DUPLICATE_IN_CAMPAIGN",
                errors=errors,
                error_records=error_records,
            )
            invalid_count += 1
            continue

        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            batch_id=batch.id,
            enc_phone=encrypt_value(phone),
            phone_hash=phone_hash,
            enc_name=encrypt_value(name) if name else None,
            status="VALIDATED",
            validation_error=None,
        )
        db.add(recipient)
        seen_hashes.add(phone_hash)
        valid_count += 1

    if error_records:
        db.add_all(error_records)

    batch.total_count = uploaded_total
    batch.valid_count = valid_count
    batch.invalid_count = invalid_count

    db.commit()

    return RecipientUploadSummary(
        batch_id=batch.id,
        uploaded_total=uploaded_total,
        valid_count=valid_count,
        invalid_count=invalid_count,
        errors=errors,
    )


def list_validation_errors(db: Session, campaign_id: int) -> list[RecipientValidationError]:
    stmt = (
        select(RecipientValidationError)
        .join(RecipientBatch, RecipientBatch.id == RecipientValidationError.batch_id)
        .where(RecipientBatch.campaign_id == campaign_id)
        .order_by(RecipientValidationError.row_number.asc())
    )
    return list(db.scalars(stmt).all())


def generate_validation_error_csv(db: Session, campaign_id: int) -> str:
    errors = list_validation_errors(db, campaign_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_number", "phone", "name", "reason", "logged_at"])
    for err in errors:
        writer.writerow(
            [
                err.row_number,
                err.raw_phone or "",
                err.raw_name or "",
                err.reason,
                err.created_at.isoformat() if err.created_at else "",
            ]
        )
    return output.getvalue()


def _append_error(
    batch_id: int,
    row_number: int,
    raw_phone: str,
    raw_name: str | None,
    reason: str,
    errors: list[str],
    error_records: List[RecipientValidationError],
) -> None:
    errors.append(f"{row_number}행: {reason}")
    error_records.append(
        RecipientValidationError(
            batch_id=batch_id,
            row_number=row_number,
            raw_phone=raw_phone,
            raw_name=raw_name or None,
            reason=reason,
        )
    )


def _phone_exists(db: Session, campaign_id: int, phone_hash: bytes) -> bool:
    stmt = select(CampaignRecipient.id).where(
        CampaignRecipient.campaign_id == campaign_id,
        CampaignRecipient.phone_hash == phone_hash,
    )
    return db.execute(stmt).first() is not None
