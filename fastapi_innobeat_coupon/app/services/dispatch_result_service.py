from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    CouponIssue,
    CouponStatusHistory,
    DispatchResult,
    MmsJob,
)
from app.schemas.dispatch import DispatchSyncSummary
from app.services import snap_service
from app.services.snap_done_code_service import (
    DoneCodeClassification,
    classify_done_code,
)


def sync_dispatch_results(
    db: Session,
    campaign_id: int,
    year_month: Optional[str] = None,
) -> DispatchSyncSummary:
    jobs = db.scalars(
        select(MmsJob).where(MmsJob.campaign_id == campaign_id)
    ).all()

    updated = 0
    skipped = 0

    for job in jobs:
        result = snap_service.fetch_delivery_status(
            db,
            client_key=job.client_key,
            year_month=year_month,
        )
        if not result:
            skipped += 1
            continue

        dispatch = db.scalar(
            select(DispatchResult).where(DispatchResult.mms_job_id == job.id)
        )
        if not dispatch:
            dispatch = DispatchResult(mms_job_id=job.id)
            db.add(dispatch)

        dispatch.done_code = result.get("DONE_CODE")
        dispatch.done_desc = result.get("DONE_DESC")
        dispatch.completed_at = _parse_datetime(
            result.get("DONE_RECEIVE_DATE") or result.get("DONE_DATE")
        )
        dispatch.telco = result.get("DONE_TELCO") or dispatch.telco
        dispatch.sent_at = dispatch.sent_at or _parse_datetime(result.get("SENT_DATE"))

        classification = classify_done_code(dispatch.done_code)
        job.status = classification.job_status

        _update_coupon_status(db, job.recipient_id, classification, dispatch.done_desc)

        updated += 1

    db.commit()
    return DispatchSyncSummary(updated=updated, skipped=skipped)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _update_coupon_status(
    db: Session,
    recipient_id: int,
    classification: DoneCodeClassification,
    done_desc: Optional[str],
) -> None:
    issue = db.scalar(
        select(CouponIssue).where(CouponIssue.recipient_id == recipient_id)
    )
    if not issue:
        return

    issue.status = classification.coupon_status

    history = CouponStatusHistory(
        coupon_issue_id=issue.id,
        status=classification.coupon_status,
        status_source="SNAP",
        status_at=datetime.now(timezone.utc),
        memo=_build_memo(classification, done_desc),
    )
    db.add(history)


def _build_memo(classification: DoneCodeClassification, done_desc: Optional[str]) -> str:
    parts = [classification.label]
    if done_desc:
        parts.append(done_desc)
    else:
        parts.append(classification.description)
    return " | ".join(part for part in parts if part)
