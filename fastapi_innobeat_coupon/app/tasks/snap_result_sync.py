from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.domain import MmsJob
from app.services.dispatch_result_service import sync_dispatch_results

logger = logging.getLogger(__name__)
FINAL_STATUSES = {"COMPLETED", "FAILED"}


def run_snap_result_sync_job() -> None:
    if not settings.snap_sync_enabled:
        return

    campaign_ids = _load_target_campaign_ids()
    if not campaign_ids:
        return

    for campaign_id in campaign_ids:
        session = SessionLocal()
        try:
            summary = sync_dispatch_results(session, campaign_id)
            logger.debug(
                "SNAP 결과 동기화 완료 (campaign_id=%s, updated=%s, skipped=%s)",
                campaign_id,
                summary.updated,
                summary.skipped,
            )
        except Exception:  # noqa: BLE001
            session.rollback()
            logger.exception("SNAP 결과 동기화 실패 (campaign_id=%s)", campaign_id)
        finally:
            session.close()


def _load_target_campaign_ids() -> list[int]:
    session = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.snap_sync_lookback_minutes
        )
        stmt = (
            select(MmsJob.campaign_id)
            .where(
                (MmsJob.status.notin_(FINAL_STATUSES))
                | (MmsJob.updated_at >= cutoff)
            )
            .distinct()
        )
        return session.scalars(stmt).all()
    finally:
        session.close()
