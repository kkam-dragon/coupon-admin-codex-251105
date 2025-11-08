from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings


class CoufunAPIError(RuntimeError):
    """COUFUN API 호출 실패."""


@dataclass
class CoufunIssueResult:
    order_id: str
    barcode: str
    valid_end_date: Optional[datetime]
    raw_payload: Dict[str, Any]


def issue_coupon(
    *,
    goods_id: str,
    tr_id: str,
    create_count: int = 1,
) -> CoufunIssueResult:
    """
    COUFUN `coufunCreate` API를 호출해 쿠폰을 발급한다.
    """
    if settings.coufun_mock_mode or not settings.coufun_base_url:
        return _mock_issue(goods_id=goods_id, tr_id=tr_id)

    if not settings.coufun_poc_id:
        raise CoufunAPIError("COUFUN_POC_ID 환경 변수가 설정되지 않았습니다.")

    payload = {
        "POC_ID": settings.coufun_poc_id,
        "GOODS_ID": goods_id,
        "CREATE_CNT": str(create_count),
        "TR_ID": tr_id,
    }

    url = f"{settings.coufun_base_url.rstrip('/')}/b2c_api/coufunCreate.do"
    try:
        with httpx.Client(timeout=settings.coufun_timeout, verify=True) as client:
            response = client.post(url, data=payload)
    except httpx.HTTPError as exc:
        raise CoufunAPIError(f"COUFUN API 호출 실패: {exc}") from exc

    if response.status_code >= 400:
        raise CoufunAPIError(f"COUFUN API 응답 오류: {response.status_code}")

    parsed = _parse_xml_response(response.text)
    result_code = parsed.get("RESULT_CODE") or parsed.get("resultCode")
    if result_code not in {None, "", "0000"}:
        message = parsed.get("RESULT_MSG") or parsed.get("resultMsg") or "Unknown error"
        raise CoufunAPIError(f"COUFUN 발급 실패: {result_code} {message}")

    barcode = parsed.get("BARCODE_NUM") or parsed.get("barcodeNum")
    order_id = parsed.get("ORDER_ID") or parsed.get("orderId") or tr_id
    valid_end = parsed.get("VALID_DATE") or parsed.get("VALID_END_DATE")
    valid_dt = _parse_datetime(valid_end)

    if not barcode:
        raise CoufunAPIError("COUFUN 응답에 BARCODE_NUM이 없습니다.")

    return CoufunIssueResult(
        order_id=order_id,
        barcode=barcode,
        valid_end_date=valid_dt,
        raw_payload=parsed,
    )


def _parse_xml_response(xml_text: str) -> Dict[str, Any]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise CoufunAPIError(f"COUFUN 응답 XML 파싱 실패: {exc}") from exc

    data: Dict[str, Any] = {}
    for element in root.iter():
        tag = element.tag.upper()
        data[tag] = (element.text or "").strip()
    return data


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    formats = ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d")
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _mock_issue(*, goods_id: str, tr_id: str) -> CoufunIssueResult:
    barcode = f"{goods_id}-{secrets.token_hex(4)}".upper()
    order_id = tr_id
    valid_end = datetime.now(timezone.utc) + timedelta(days=90)
    payload = {
        "RESULT_CODE": "0000",
        "BARCODE_NUM": barcode,
        "ORDER_ID": order_id,
        "VALID_DATE": valid_end.strftime("%Y%m%d"),
    }
    return CoufunIssueResult(
        order_id=order_id,
        barcode=barcode,
        valid_end_date=valid_end,
        raw_payload=payload,
    )
