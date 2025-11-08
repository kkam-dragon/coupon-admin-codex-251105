from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings


class CoufunAPIError(RuntimeError):
    """COUFUN API 호출 실패."""


@dataclass
class CoufunProduct:
    goods_id: str
    name: str
    face_value: Optional[float]
    purchase_price: Optional[float]
    valid_days: Optional[int]
    status: str


@dataclass
class CoufunIssueResult:
    order_id: str
    barcode: str
    valid_end_date: Optional[datetime]
    raw_payload: Dict[str, Any]


@dataclass
class CoufunStatus:
    barcode: str
    status: str
    remain_amount: Optional[float]
    raw_payload: Dict[str, Any]


def issue_coupon(*, goods_id: str, tr_id: str, create_count: int = 1) -> CoufunIssueResult:
    payload = {
        "GOODS_ID": goods_id,
        "CREATE_CNT": str(create_count),
        "TR_ID": tr_id,
    }
    xml_text = _post("coufunCreate.do", payload, mock_key="issue")
    parsed = _parse_simple_map(xml_text)
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


def fetch_goods_list() -> List[CoufunProduct]:
    xml_text = _post("coufunGoods.do", {}, mock_key="goods")
    root = ET.fromstring(xml_text)
    products: List[CoufunProduct] = []
    for item in root.findall(".//GOODS"):
        data = {child.tag.upper(): (child.text or "").strip() for child in item}
        goods_id = data.get("GOODS_ID")
        if not goods_id:
            continue
        products.append(
            CoufunProduct(
                goods_id=goods_id,
                name=data.get("GOODS_NM") or data.get("GOODS_NAME") or "",
                face_value=_to_float(data.get("FACE_VALUE")),
                purchase_price=_to_float(data.get("SALE_AMT")),
                valid_days=_to_int(data.get("VALID_DAYS")),
                status=data.get("GOODS_STATUS") or data.get("STATUS") or "UNKNOWN",
            )
        )
    if not products and settings.coufun_mock_mode:
        return _mock_goods_list()
    return products


def get_coupon_status(barcode: str) -> CoufunStatus:
    xml_text = _post("coufunPartAmountStatus.do", {"BARCODE_NUM": barcode}, mock_key="status")
    parsed = _parse_simple_map(xml_text)
    status = parsed.get("RESULT_STATUS") or parsed.get("STATUS") or "UNKNOWN"
    remain_amount = _to_float(parsed.get("REMAIN_AMOUNT"))
    return CoufunStatus(
        barcode=barcode,
        status=status,
        remain_amount=remain_amount,
        raw_payload=parsed,
    )


def cancel_coupon(barcode: str, reason: str | None = None) -> CoufunStatus:
    payload = {"BARCODE_NUM": barcode}
    if reason:
        payload["MEMO"] = reason
    xml_text = _post("coufunCancel.do", payload, mock_key="cancel")
    parsed = _parse_simple_map(xml_text)
    status = parsed.get("RESULT_STATUS") or parsed.get("STATUS") or "CANCELLED"
    return CoufunStatus(
        barcode=barcode,
        status=status,
        remain_amount=None,
        raw_payload=parsed,
    )


# --------------------------------------------------------------------------- #
# Internal helpers

def _post(endpoint: str, payload: Dict[str, Any], *, mock_key: str) -> str:
    if settings.coufun_mock_mode or not settings.coufun_base_url:
        return _mock_response(mock_key, payload)

    if not settings.coufun_poc_id:
        raise CoufunAPIError("COUFUN_POC_ID 환경 변수가 설정되지 않았습니다.")

    final_payload = {"POC_ID": settings.coufun_poc_id}
    final_payload.update(payload)
    url = f"{settings.coufun_base_url.rstrip('/')}/b2c_api/{endpoint}"

    try:
        with httpx.Client(timeout=settings.coufun_timeout, verify=True) as client:
            response = client.post(url, data=final_payload)
    except httpx.HTTPError as exc:
        raise CoufunAPIError(f"COUFUN API 호출 실패: {exc}") from exc

    if response.status_code >= 400:
        raise CoufunAPIError(f"COUFUN API 응답 오류: {response.status_code}")

    return response.text


def _parse_simple_map(xml_text: str) -> Dict[str, Any]:
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


def _to_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _mock_response(kind: str, payload: Dict[str, Any]) -> str:
    if kind == "issue":
        barcode = f"{payload.get('GOODS_ID','GOOD')}-{datetime.now().strftime('%y%m%d')}"
        return f"""
        <RESPONSE>
            <RESULT_CODE>0000</RESULT_CODE>
            <BARCODE_NUM>{barcode}</BARCODE_NUM>
            <ORDER_ID>{payload.get('TR_ID')}</ORDER_ID>
            <VALID_DATE>{(datetime.now(timezone.utc)+timedelta(days=60)).strftime('%Y%m%d')}</VALID_DATE>
        </RESPONSE>
        """
    if kind == "goods":
        return """
        <RESPONSE>
            <GOODS_LIST>
                <GOODS>
                    <GOODS_ID>0000006937</GOODS_ID>
                    <GOODS_NM>Mock Coffee Coupon</GOODS_NM>
                    <FACE_VALUE>4500</FACE_VALUE>
                    <SALE_AMT>0</SALE_AMT>
                    <VALID_DAYS>60</VALID_DAYS>
                    <GOODS_STATUS>ON_SALE</GOODS_STATUS>
                </GOODS>
            </GOODS_LIST>
        </RESPONSE>
        """
    if kind == "status":
        return """
        <RESPONSE>
            <RESULT_STATUS>DELIVERED</RESULT_STATUS>
            <REMAIN_AMOUNT>0</REMAIN_AMOUNT>
        </RESPONSE>
        """
    if kind == "cancel":
        return """
        <RESPONSE>
            <RESULT_STATUS>CANCELLED</RESULT_STATUS>
        </RESPONSE>
        """
    return "<RESPONSE><RESULT_CODE>0000</RESULT_CODE></RESPONSE>"


def _mock_goods_list() -> List[CoufunProduct]:
    return [
        CoufunProduct(
            goods_id="0000006937",
            name="Mock Coffee Coupon",
            face_value=4500.0,
            purchase_price=0.0,
            valid_days=60,
            status="ON_SALE",
        )
    ]
