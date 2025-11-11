from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value, encrypt_value, hash_value
from app.core.phone import is_valid_phone, mask_phone, normalize_phone
from app.models.domain import (
    Campaign,
    CampaignRecipient,
    CouponIssue,
    CsAction,
    MediaAsset,
    MmsJob,
    RecipientHistory,
    RenderedMmsAsset,
)
from app.schemas.cs import CsActionResponse, CsResendResponse, CsSearchResponse
from app.services import snap_service


def search_coupon_issue(
    db: Session,
    *,
    phone: str | None = None,
    order_id: str | None = None,
) -> CsSearchResponse:
    if not phone and not order_id:
        raise ValueError("휴대폰 번호 또는 주문번호 중 하나는 필수입니다.")

    stmt = select(CouponIssue).join(CampaignRecipient)
    if phone:
        normalized = normalize_phone(phone)
        if not is_valid_phone(normalized):
            raise ValueError("휴대폰 번호 형식이 올바르지 않습니다.")
        phone_hash = hash_value(normalized)
        stmt = stmt.where(CampaignRecipient.phone_hash == phone_hash)
    if order_id:
        stmt = stmt.where(CouponIssue.order_id == order_id)

    issue = db.scalars(stmt.limit(1)).first()
    if not issue:
        raise ValueError("조건에 해당하는 쿠폰을 찾을 수 없습니다.")

    campaign = db.get(Campaign, issue.campaign_id)
    recipient = db.get(CampaignRecipient, issue.recipient_id)
    if not campaign or not recipient:
        raise ValueError("쿠폰 데이터가 손상되었습니다.")

    phone_plain = decrypt_value(recipient.enc_phone)
    barcode_plain = decrypt_value(issue.barcode_enc)

    return CsSearchResponse(
        coupon_issue_id=issue.id,
        campaign_id=campaign.id,
        campaign_name=campaign.event_name,
        recipient_id=recipient.id,
        phone_masked=mask_phone(phone_plain),
        barcode_masked=_mask_barcode(barcode_plain),
        status=issue.status,
        order_id=issue.order_id,
        valid_end_date=issue.valid_end_date,
    )


def resend_coupon(
    db: Session,
    *,
    coupon_issue_id: int,
    performed_by: int,
    reason: str | None = None,
) -> CsResendResponse:
    issue, campaign, recipient = _load_issue_bundle(db, coupon_issue_id)
    phone = decrypt_value(recipient.enc_phone)
    if not phone:
        raise ValueError("수신자 전화번호 복호화에 실패했습니다.")

    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    client_key_seed = f"{campaign.campaign_key}-CS{timestamp}"
    client_key = snap_service.build_client_key(client_key_seed, recipient.id)
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

    action = _create_cs_action(
        db,
        coupon_issue_id=issue.id,
        recipient_id=recipient.id,
        action_type="RESEND",
        result_status="QUEUED",
        reason=reason,
        performed_by=performed_by,
    )
    db.commit()
    return CsResendResponse(client_key=client_key, queued=True)


def change_recipient_phone(
    db: Session,
    *,
    coupon_issue_id: int,
    new_phone: str,
    performed_by: int,
    reason: str | None = None,
) -> CsActionResponse:
    if not new_phone:
        raise ValueError("변경할 전화번호가 필요합니다.")
    normalized = normalize_phone(new_phone)
    if not is_valid_phone(normalized):
        raise ValueError("전화번호 형식이 올바르지 않습니다.")

    issue, campaign, recipient = _load_issue_bundle(db, coupon_issue_id)
    new_hash = hash_value(normalized)
    duplicate = db.scalar(
        select(CampaignRecipient.id)
        .where(
            CampaignRecipient.campaign_id == campaign.id,
            CampaignRecipient.phone_hash == new_hash,
            CampaignRecipient.id != recipient.id,
        )
        .limit(1)
    )
    if duplicate:
        raise ValueError("동일한 번호가 이미 캠페인에 존재합니다.")

    old_phone = decrypt_value(recipient.enc_phone)
    recipient.enc_phone = encrypt_value(normalized)
    recipient.phone_hash = new_hash
    recipient.updated_by = str(performed_by)

    history = RecipientHistory(
        recipient_id=recipient.id,
        action="CHANGE_PHONE",
        old_value=old_phone,
        new_value=normalized,
        created_by=str(performed_by),
    )
    db.add(history)

    action = _create_cs_action(
        db,
        coupon_issue_id=issue.id,
        recipient_id=recipient.id,
        action_type="CHANGE_PHONE",
        result_status="UPDATED",
        reason=reason,
        performed_by=performed_by,
    )
    db.commit()
    return CsActionResponse(action_id=action.id, action_type=action.action_type)


def add_note(
    db: Session,
    *,
    coupon_issue_id: int,
    memo: str,
    performed_by: int,
) -> CsActionResponse:
    if not memo:
        raise ValueError("메모 내용이 필요합니다.")
    issue = db.get(CouponIssue, coupon_issue_id)
    if not issue:
        raise ValueError("쿠폰 발급 정보를 찾을 수 없습니다.")

    action = _create_cs_action(
        db,
        coupon_issue_id=issue.id,
        recipient_id=issue.recipient_id,
        action_type="NOTE",
        result_status="RECORDED",
        reason=memo,
        performed_by=performed_by,
    )
    db.commit()
    return CsActionResponse(action_id=action.id, action_type=action.action_type)


def _create_cs_action(
    db: Session,
    *,
    coupon_issue_id: int,
    recipient_id: int,
    action_type: str,
    result_status: str,
    performed_by: int,
    reason: str | None = None,
) -> CsAction:
    action = CsAction(
        coupon_issue_id=coupon_issue_id,
        recipient_id=recipient_id,
        action_type=action_type,
        reason=reason,
        performed_by=performed_by,
        performed_at=datetime.now(timezone.utc),
        result_status=result_status,
        created_by=str(performed_by),
        updated_by=str(performed_by),
    )
    db.add(action)
    db.flush()
    return action


def _load_issue_bundle(db: Session, coupon_issue_id: int) -> tuple[CouponIssue, Campaign, CampaignRecipient]:
    issue = db.get(CouponIssue, coupon_issue_id)
    if not issue:
        raise ValueError("쿠폰 발급 정보를 찾을 수 없습니다.")
    campaign = db.get(Campaign, issue.campaign_id)
    recipient = db.get(CampaignRecipient, issue.recipient_id)
    if not campaign or not recipient:
        raise ValueError("연관된 캠페인/수신자를 찾을 수 없습니다.")
    return issue, campaign, recipient


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


def _mask_barcode(barcode: str | None) -> str | None:
    if not barcode:
        return None
    if len(barcode) <= 4:
        return "****"
    return f"****{barcode[-4:]}"
