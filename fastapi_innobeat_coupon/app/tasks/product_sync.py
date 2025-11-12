from __future__ import annotations

import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.product_sync_service import sync_coufun_products

logger = logging.getLogger(__name__)


def run_product_sync_job() -> None:
    if not settings.product_sync_enabled:
        return

    session = SessionLocal()
    try:
        summary = sync_coufun_products(session)
        logger.info(
            "COUFUN 상품 동기화 완료 (synced=%s, result_code=%s)",
            summary.get("synced"),
            summary.get("result_code"),
        )
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("COUFUN 상품 동기화 실패")
    finally:
        session.close()
