from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings

INSERT_UMS_SQL = text(
    """
    INSERT INTO UMS_MSG (
        CLIENT_KEY,
        REQ_CH,
        TRAFFIC_TYPE,
        MSG_STATUS,
        REQ_DATE,
        CALLBACK_NUMBER,
        PHONE,
        MSG,
        TITLE,
        MMS_FILE_LIST,
        REQ_DEPT_CODE,
        REQ_USER_ID
    ) VALUES (
        :client_key,
        :req_ch,
        :traffic_type,
        'ready',
        :req_date,
        :callback_number,
        :phone,
        :msg,
        :title,
        :mms_file_list,
        :req_dept_code,
        :req_user_id
    )
"""
)


def build_client_key(campaign_key: str, recipient_id: int) -> str:
    """
    LG U+ 제약(30 bytes)을 지키기 위해 suffix 해시를 붙인다.
    """
    base = f"{campaign_key}-{recipient_id}"
    if len(base) <= 30:
        return base
    suffix = hashlib.sha1(base.encode("utf-8")).hexdigest()[:6]
    trimmed = campaign_key[: 30 - len(suffix) - 1]
    return f"{trimmed}-{suffix}"


def enqueue_mms_message(
    db: Session,
    *,
    client_key: str,
    phone: str,
    callback_number: str,
    title: str,
    message: str,
    media_path: Optional[str],
) -> None:
    """
    SNAP Agent UMS_MSG 테이블에 레코드를 INSERT 한다.
    """
    params = {
        "client_key": client_key,
        "req_ch": settings.snap_req_channel,
        "traffic_type": settings.snap_traffic_type,
        "req_date": datetime.now(timezone.utc),
        "callback_number": callback_number,
        "phone": phone,
        "msg": message,
        "title": title,
        "mms_file_list": media_path,
        "req_dept_code": settings.snap_req_dept_code,
        "req_user_id": settings.snap_req_user_id,
    }
    db.execute(INSERT_UMS_SQL, params)


def fetch_delivery_status(
    db: Session,
    *,
    client_key: str,
    year_month: Optional[str] = None,
) -> Optional[dict]:
    """
    UMS_LOG_YYYYMM 테이블에서 최근 결과를 조회한다.
    """
    table_suffix = year_month or datetime.now(timezone.utc).strftime("%Y%m")
    if not (len(table_suffix) == 6 and table_suffix.isdigit()):
        raise ValueError("year_month 형식은 YYYYMM 이어야 합니다.")
    table_name = f"UMS_LOG_{table_suffix}"
    sql = text(
        f"""
        SELECT DONE_CODE, DONE_DESC, DONE_RECEIVE_DATE
        FROM {table_name}
        WHERE CLIENT_KEY = :client_key
        ORDER BY DONE_RECEIVE_DATE DESC
        LIMIT 1
        """
    )
    result = db.execute(sql, {"client_key": client_key}).mappings().first()
    if not result:
        return None
    return dict(result)
