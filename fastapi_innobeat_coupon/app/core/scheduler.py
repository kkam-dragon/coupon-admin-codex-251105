from __future__ import annotations

import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    BackgroundScheduler = None  # type: ignore[assignment]
    IntervalTrigger = None  # type: ignore[assignment]
    CronTrigger = None  # type: ignore[assignment]

from app.core.config import settings
from app.tasks.coupon_status_sync import run_coupon_status_sync_job
from app.tasks.product_sync import run_product_sync_job
from app.tasks.send_query_export_cleanup import run_send_query_export_cleanup_job
from app.tasks.snap_result_sync import run_snap_result_sync_job

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None or not settings.snap_sync_enabled:
        if not settings.snap_sync_enabled:
            logger.info("SNAP 동기화 스케줄러 비활성화 상태 (SNAP_SYNC_ENABLED=false)")
        return
    if BackgroundScheduler is None or IntervalTrigger is None:
        logger.warning("APScheduler 미설치 상태로 스케줄러를 시작할 수 없습니다.")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_snap_result_sync_job,
        IntervalTrigger(seconds=settings.snap_sync_interval_seconds),
        id="snap_result_sync",
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    if settings.product_sync_enabled and CronTrigger is not None:
        _scheduler.add_job(
            run_product_sync_job,
            CronTrigger(hour=settings.product_sync_hour_utc, minute=0),
            id="product_sync",
            max_instances=1,
            replace_existing=True,
        )
    if settings.coupon_status_sync_enabled:
        _scheduler.add_job(
            run_coupon_status_sync_job,
            IntervalTrigger(seconds=settings.coupon_status_sync_interval_seconds),
            id="coupon_status_sync",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )
    if settings.export_cleanup_enabled:
        _scheduler.add_job(
            run_send_query_export_cleanup_job,
            IntervalTrigger(minutes=settings.export_cleanup_interval_minutes),
            id="send_query_export_cleanup",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )

    _scheduler.start()
    logger.info("스케줄러 시작")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("SNAP 동기화 스케줄러 종료")
        _scheduler = None
