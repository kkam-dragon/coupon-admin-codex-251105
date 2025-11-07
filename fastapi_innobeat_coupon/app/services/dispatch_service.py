from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.models.domain import (
    Campaign,
    CampaignRecipient,
    MediaAsset,
    MmsJob,
    RenderedMmsAsset,
)
from app.schemas.dispatch import DispatchError, DispatchSummary
from app.services import snap_service


def dispatch_campaign_messages(db: Session, campaign_id: int) -> DispatchSummary:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise ValueError("캠페인을 찾을 수 없습니다.")

    recipients = db.scalars(
        select(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "VALIDATED",
        )
    ).all()
    if not recipients:
        raise ValueError("VALIDATED 상태의 수신자가 없습니다.")

    errors: List[DispatchError] = []
    success_count = 0

    for recipient in recipients:
        try:
            phone = decrypt_value(recipient.enc_phone)
            if not phone:
                raise ValueError("전화번호 복호화 실패")

            media_path = _resolve_media_path(db, campaign.id, recipient.id, campaign.banner_asset_id)
            client_key = snap_service.build_client_key(campaign.campaign_key, recipient.id)

            snap_service.enqueue_mms_message(
                db,
                client_key=client_key,
                phone=phone,
                callback_number=campaign.sender_number,
                title=campaign.message_title,
                message=campaign.message_body,
                media_path=media_path,
            )

            job = MmsJob(
                campaign_id=campaign.id,
                recipient_id=recipient.id,
                client_key=client_key,
                ums_msg_id=client_key,
                req_date=datetime.now(timezone.utc),
                status="READY",
            )
            db.add(job)
            success_count += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(DispatchError(recipient_id=recipient.id, reason=str(exc)))

    db.commit()

    if success_count == 0 and errors:
        raise ValueError("모든 수신자 발송 준비에 실패했습니다.")

    return DispatchSummary(enqueued=success_count, failed=len(errors), errors=errors)


def _resolve_media_path(
    db: Session,
    campaign_id: int,
    recipient_id: int,
    banner_asset_id: int | None,
) -> str | None:
    rendered = db.scalars(
        select(RenderedMmsAsset).where(
            RenderedMmsAsset.campaign_id == campaign_id,
            RenderedMmsAsset.recipient_id == recipient_id,
        )
    ).first()
    if rendered and rendered.file_path:
        return rendered.file_path
    if banner_asset_id:
        media = db.get(MediaAsset, banner_asset_id)
        if media:
            return media.storage_path
    return None
