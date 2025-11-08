from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value, encrypt_value
from app.models.domain import (
    Campaign,
    CampaignProduct,
    CampaignRecipient,
    CouponIssue,
    CouponProduct,
    MediaAsset,
    MmsJob,
    RenderedMmsAsset,
)
from app.schemas.dispatch import DispatchError, DispatchSummary
from app.services import coufun_service, snap_service


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

            client_key = snap_service.build_client_key(campaign.campaign_key, recipient.id)
            _ensure_coupon_issue(db, campaign, recipient, client_key)

            media_path = _resolve_media_path(db, campaign.id, recipient.id, campaign.banner_asset_id)

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


def _ensure_coupon_issue(
    db: Session,
    campaign: Campaign,
    recipient: CampaignRecipient,
    client_key: str,
) -> CouponIssue:
    existing = db.scalar(
        select(CouponIssue).where(CouponIssue.recipient_id == recipient.id)
    )
    if existing:
        return existing

    coupon_product = db.scalar(
        select(CouponProduct)
        .join(CampaignProduct, CampaignProduct.coupon_product_id == CouponProduct.id)
        .where(CampaignProduct.campaign_id == campaign.id)
    )
    if not coupon_product:
        raise ValueError("캠페인에 연결된 쿠폰 상품이 없습니다.")

    issue_result = coufun_service.issue_coupon(
        goods_id=coupon_product.goods_id,
        tr_id=client_key,
        create_count=1,
    )

    issue = CouponIssue(
        campaign_id=campaign.id,
        recipient_id=recipient.id,
        order_id=issue_result.order_id,
        barcode_enc=encrypt_value(issue_result.barcode),
        valid_end_date=issue_result.valid_end_date,
        status="ISSUED",
        vendor_payload=issue_result.raw_payload,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(issue)
    return issue
