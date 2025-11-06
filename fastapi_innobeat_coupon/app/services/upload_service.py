from __future__ import annotations

from __future__ import annotations

import csv
import io
import re
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_value, hash_value
from app.models.domain import Campaign, CampaignRecipient, RecipientBatch
from app.schemas.uploads import RecipientUploadSummary

PHONE_PATTERN = re.compile(r"^010\d{8}$")


def _parse_csv(file_bytes: bytes) -> Iterable[dict[str, str]]:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if "phone" not in reader.fieldnames or "name" not in reader.fieldnames:
        raise ValueError("CSV 헤더에 phone,name 컬럼이 필요합니다.")
    for row in reader:
        yield {"phone": (row.get("phone") or "").strip(), "name": (row.get("name") or "").strip()}


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
    seen_hashes: set[bytes] = set()

    for row in _parse_csv(file_bytes):
        uploaded_total += 1
        phone = row["phone"]
        name = row["name"]

        if not PHONE_PATTERN.match(phone):
            invalid_count += 1
            errors.append(f"{uploaded_total}행: 전화번호 형식이 올바르지 않습니다.")
            continue
        phone_hash = hash_value(phone)
        if phone_hash in seen_hashes or _phone_exists(db, campaign_id, phone_hash):
            invalid_count += 1
            errors.append(f"{uploaded_total}행: 중복된 전화번호입니다.")
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


def _phone_exists(db: Session, campaign_id: int, phone_hash: bytes) -> bool:
    stmt = select(CampaignRecipient.id).where(
        CampaignRecipient.campaign_id == campaign_id,
        CampaignRecipient.phone_hash == phone_hash,
    )
    return db.execute(stmt).first() is not None
