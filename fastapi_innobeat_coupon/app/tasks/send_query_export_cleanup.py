from __future__ import annotations

import logging

from app.core.config import settings
from app.services.send_query_service import cleanup_old_exports

logger = logging.getLogger(__name__)


def run_send_query_export_cleanup_job() -> None:
    if not settings.export_cleanup_enabled:
        return
    try:
        cleanup_old_exports()
        logger.debug("sendQuery export cleanup executed")
    except Exception:  # noqa: BLE001
        logger.exception("sendQuery export cleanup failed")
