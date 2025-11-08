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
        dispatch.completed_at = _parse_datetime(result.get("DONE_RECEIVE_DATE"))
        job.status = "COMPLETED" if _is_success(dispatch.done_code) else "FAILED"

        _update_coupon_status(db, job.recipient_id, dispatch.done_code, dispatch.done_desc)

        updated += 1

    db.commit()
    return DispatchSyncSummary(updated=updated, skipped=skipped)


def _is_success(done_code: Optional[str]) -> bool:
    if not done_code:
        return False
    return done_code.startswith("0")


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
    done_code: Optional[str],
    done_desc: Optional[str],
) -> None:
    issue = db.scalar(
        select(CouponIssue).where(CouponIssue.recipient_id == recipient_id)
    )
    if not issue:
        return

    new_status = "DELIVERED" if _is_success(done_code) else "FAILED"
    issue.status = new_status

    history = CouponStatusHistory(
        coupon_issue_id=issue.id,
        status=new_status,
        status_source="SNAP",
        status_at=datetime.now(timezone.utc),
        memo=done_desc,
    )
    db.add(history)
