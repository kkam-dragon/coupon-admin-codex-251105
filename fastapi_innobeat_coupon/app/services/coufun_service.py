from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings

T = TypeVar("T")

COUFUN_SUCCESS_CODES = {"00", "0000"}
COUFUN_RETRYABLE_CODES = {"50", "95", "98", "99"}
COUFUN_RESULT_CODE_MESSAGES = {
    "00": "처리 성공",
    "01": "IP 오류 (등록되지 않은 IP)",
    "02": "POC_ID 오류",
    "03": "ORDER_ID 오류",
    "04": "유효기간 오류",
    "05": "사용기간 오류",
    "08": "상품권종 오류",
    "09": "상품번호 조회 횟수 초과",
    "10": "상품정보 오류",
    "11": "TR_ID 길이 오류",
    "12": "TR_ID 중복 오류",
    "13": "발신번호 오류",
    "14": "수신번호 오류",
    "15": "수신번호 건수 초과",
    "16": "바코드 오류",
    "17": "사용 완료 건 재요청",
    "18": "취소 완료 건 재요청",
    "19": "발송유형 오류",
    "20": "발송횟수 초과",
    "21": "제목 오류",
    "22": "메시지 오류",
    "23": "중복 요청 오류",
    "24": "추가입력1 길이 오류",
    "25": "추가입력2 길이 오류",
    "26": "유효기간 정보 없음",
    "27": "유효기간 포맷 오류",
    "28": "유효기간 연장이 불가한 상품",
    "29": "유효기간 연장 입력 오류",
    "30": "상품 판매 기간 오류",
    "31": "상품 ID 오류",
    "50": "시스템 점검 또는 지연",
    "95": "선처리 필요",
    "98": "API 권한 부족",
    "99": "기타 시스템 오류",
}
COUFUN_STATUS_LABELS = {
    "000": "미사용",
    "001": "사용완료",
    "100": "취소",
}
COUFUN_STATUS_TO_INTERNAL = {
    "000": "ISSUED",
    "001": "USED",
    "100": "CANCELLED",
}
MAX_RETRY_ATTEMPTS = 3
BASE_RETRY_DELAY = 0.4


class CoufunAPIError(RuntimeError):
    """COUFUN API 호출 오류."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retryable: bool = False,
        payload: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.payload = payload or {}


@dataclass
class CoufunProduct:
    goods_id: str
    name: str
    face_value: Optional[float]
    purchase_price: Optional[float]
    valid_days: Optional[int]
    status: str
    category_id: Optional[str] = None
    valid_end_type: Optional[str] = None
    valid_end_date: Optional[datetime] = None
    send_type: Optional[str] = None
    image_path: Optional[str] = None
    raw_payload: Dict[str, Any] | None = None


@dataclass
class CoufunGoodsResponse:
    products: List[CoufunProduct]
    result_code: Optional[str]
    result_message: Optional[str]


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
    coupon_type: Optional[str]
    status_code: Optional[str]
    status_label: Optional[str]
    total_amount: Optional[float]
    order_date: Optional[datetime]
    valid_end_date: Optional[datetime]
    exchanged_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    raw_payload: Dict[str, Any]


def issue_coupon(*, goods_id: str, tr_id: str, create_count: int = 1) -> CoufunIssueResult:
    payload = {
        "GOODS_ID": goods_id,
        "CREATE_CNT": str(create_count),
        "TR_ID": tr_id,
    }

    def _call() -> CoufunIssueResult:
        xml_text = _post("coufunCreate.do", payload, mock_key="issue")
        parsed = _parse_simple_map(xml_text)
        _ensure_success(parsed, "coufunCreate", raw_payload=parsed)

        barcode = parsed.get("BARCODE_NUM") or parsed.get("barcodeNum")
        order_id = parsed.get("ORDER_ID") or parsed.get("orderId") or tr_id
        valid_end = parsed.get("VALID_DATE") or parsed.get("VALID_END_DATE")
        valid_dt = _parse_datetime(valid_end)

        if not barcode:
            raise CoufunAPIError("COUFUN 응답에 BARCODE_NUM이 없습니다.", payload=parsed)

        return CoufunIssueResult(
            order_id=order_id,
            barcode=barcode,
            valid_end_date=valid_dt,
            raw_payload=parsed,
        )

    return _run_with_retry("coufunCreate", _call)


def fetch_goods_list() -> CoufunGoodsResponse:
    def _call() -> CoufunGoodsResponse:
        xml_text = _post("coufunProduct.do", {}, mock_key="goods")
        root = _load_xml(xml_text)
        _ensure_success(root, "coufunProduct")

        products: List[CoufunProduct] = []
        items = root.findall(".//PRODUCT_INFO")
        if not items:
            items = root.findall(".//GOODS")
        for item in items:
            data = {child.tag.upper(): (child.text or "").strip() for child in item}
            goods_id = data.get("GOODS_ID")
            if not goods_id:
                continue
            valid_end_type = data.get("VALID_END_TYPE")
            valid_end_date = _parse_datetime(data.get("VALID_END_DATE"))
            valid_days = _to_int(data.get("VALID_DAYS"))
            if valid_days is None and valid_end_type == "D":
                valid_days = _to_int(data.get("VALID_END_DATE"))
            products.append(
                CoufunProduct(
                    goods_id=goods_id,
                    name=data.get("GOODS_NM") or data.get("GOODS_NAME") or "",
                    face_value=_to_float(data.get("FACE_VALUE") or data.get("GOODS_ORI_PRICE")),
                    purchase_price=_to_float(data.get("SALE_AMT") or data.get("GOODS_PRICE")),
                    valid_days=valid_days,
                    status=data.get("GOODS_STATUS") or "AVAILABLE",
                    category_id=data.get("CAT_ID"),
                    valid_end_type=valid_end_type,
                    valid_end_date=valid_end_date,
                    send_type=data.get("SEND_TYPE"),
                    image_path=data.get("IMAGE_PATH_B") or data.get("IMAGE_PATH_M"),
                    raw_payload=data,
                )
            )

        if not products and settings.coufun_mock_mode:
            mock_products = _mock_goods_list()
            return CoufunGoodsResponse(
                products=mock_products,
                result_code="00",
                result_message="MOCK",
            )

        return CoufunGoodsResponse(
            products=products,
            result_code=_normalize_code(_extract_value(root, "RESULT_CODE")),
            result_message=_extract_value(root, "RESULT_MSG"),
        )

    return _run_with_retry("coufunProduct", _call)


def get_coupon_status(goods_id: str, barcode: str) -> CoufunStatus:
    payload = {"GOODS_ID": goods_id, "BARCODE_NUM": barcode}

    def _call() -> CoufunStatus:
        xml_text = _post("coufunPartAmountStatus.do", payload, mock_key="status")
        parsed = _parse_simple_map(xml_text)
        _ensure_success(parsed, "coufunPartAmountStatus", raw_payload=parsed)

        status_code = _normalize_code(parsed.get("RESULT_STATUS") or parsed.get("STATUS"))
        status_label = COUFUN_STATUS_LABELS.get(status_code)
        internal_status = COUFUN_STATUS_TO_INTERNAL.get(status_code, status_code or "UNKNOWN")

        return CoufunStatus(
            barcode=barcode,
            status=internal_status,
            remain_amount=_to_float(parsed.get("REMAIN_AMOUNT")),
            coupon_type=parsed.get("COUPON_TYPE"),
            status_code=status_code,
            status_label=status_label,
            total_amount=_to_float(parsed.get("TOTAL_AMOUNT")),
            order_date=_parse_datetime(parsed.get("ORDER_DATE")),
            valid_end_date=_parse_datetime(parsed.get("VALID_END_DATE")),
            exchanged_at=_parse_datetime(parsed.get("EXCHANGE_DATE")),
            cancelled_at=_parse_datetime(parsed.get("CANCEL_DATE")),
            raw_payload=parsed,
        )

    return _run_with_retry("coufunPartAmountStatus", _call)


def cancel_coupon(goods_id: str, barcode: str, reason: str | None = None) -> CoufunStatus:
    payload = {"GOODS_ID": goods_id, "BARCODE_NUM": barcode}
    if reason:
        payload["MEMO"] = reason

    def _call() -> CoufunStatus:
        xml_text = _post("coufunPartCancel.do", payload, mock_key="cancel")
        parsed = _parse_simple_map(xml_text)
        _ensure_success(parsed, "coufunPartCancel", raw_payload=parsed)
        return CoufunStatus(
            barcode=barcode,
            status="CANCELLED",
            remain_amount=None,
            coupon_type=None,
            status_code="100",
            status_label=COUFUN_STATUS_LABELS.get("100"),
            total_amount=None,
            order_date=None,
            valid_end_date=None,
            exchanged_at=None,
            cancelled_at=_parse_datetime(parsed.get("CANCEL_DATE")),
            raw_payload=parsed,
        )

    return _run_with_retry("coufunPartCancel", _call)


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
    except httpx.HTTPError as exc:  # 네트워크/타임아웃 오류
        raise CoufunAPIError(f"COUFUN API 호출 실패: {exc}", retryable=True) from exc

    if response.status_code >= 400:
        retryable = response.status_code >= 500
        raise CoufunAPIError(
            f"COUFUN API HTTP 오류: {response.status_code}",
            retryable=retryable,
        )

    return response.text


def _parse_simple_map(xml_text: str) -> Dict[str, Any]:
    root = _load_xml(xml_text)
    data: Dict[str, Any] = {}
    for element in root.iter():
        tag = element.tag.upper()
        data[tag] = (element.text or "").strip()
    return data


def _load_xml(xml_text: str) -> ET.Element:
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise CoufunAPIError(f"COUFUN 응답 XML 파싱 실패: {exc}") from exc


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
        <COUFUNCREATE>
            <RESULT_CODE>00</RESULT_CODE>
            <RESULT_MSG>SUCCESS</RESULT_MSG>
            <BARCODE_NUM>{barcode}</BARCODE_NUM>
            <ORDER_ID>{payload.get('TR_ID')}</ORDER_ID>
            <VALID_DATE>{(datetime.now(timezone.utc)+timedelta(days=60)).strftime('%Y%m%d')}</VALID_DATE>
        </COUFUNCREATE>
        """
    if kind == "goods":
        return """
        <PRODUCTLIST>
            <RESULT_CODE>00</RESULT_CODE>
            <RESULT_MSG>SUCCESS</RESULT_MSG>
            <LIST_CNT>1</LIST_CNT>
            <PRODUCT_INFO>
                <CAT_ID>001</CAT_ID>
                <GOODS_ID>0000006937</GOODS_ID>
                <GOODS_NAME>Mock Coffee Coupon</GOODS_NAME>
                <GOODS_ORI_PRICE>4500</GOODS_ORI_PRICE>
                <GOODS_PRICE>0</GOODS_PRICE>
                <VALID_END_TYPE>D</VALID_END_TYPE>
                <VALID_END_DATE>60</VALID_END_DATE>
                <SEND_TYPE>M</SEND_TYPE>
            </PRODUCT_INFO>
        </PRODUCTLIST>
        """
    if kind == "status":
        return f"""
        <COUFUNSEARCH>
            <RESULT_CODE>00</RESULT_CODE>
            <RESULT_MSG>SUCCESS</RESULT_MSG>
            <COUPON_TYPE>BARCODE</COUPON_TYPE>
            <STATUS>000</STATUS>
            <BARCODE_NUM>{payload.get('BARCODE_NUM')}</BARCODE_NUM>
            <REMAIN_AMOUNT>0</REMAIN_AMOUNT>
            <TOTAL_AMOUNT>0</TOTAL_AMOUNT>
            <VALID_END_DATE>{(datetime.now(timezone.utc)+timedelta(days=60)).strftime('%Y%m%d')}</VALID_END_DATE>
        </COUFUNSEARCH>
        """
    if kind == "cancel":
        return f"""
        <COUFUNCANCEL>
            <RESULT_CODE>00</RESULT_CODE>
            <RESULT_MSG>SUCCESS</RESULT_MSG>
            <BARCODE_NUM>{payload.get('BARCODE_NUM')}</BARCODE_NUM>
        </COUFUNCANCEL>
        """
    return "<RESPONSE><RESULT_CODE>00</RESULT_CODE></RESPONSE>"


def _mock_goods_list() -> List[CoufunProduct]:
    return [
        CoufunProduct(
            goods_id="0000006937",
            name="Mock Coffee Coupon",
            face_value=4500.0,
            purchase_price=0.0,
            valid_days=60,
            status="AVAILABLE",
            category_id="001",
            valid_end_type="D",
            raw_payload={"GOODS_ID": "0000006937"},
        )
    ]


def _extract_value(source: Dict[str, Any] | ET.Element, tag: str) -> Optional[str]:
    if isinstance(source, dict):
        for key in (tag, tag.upper(), tag.lower()):
            if key in source:
                value = source[key]
                if isinstance(value, str):
                    value = value.strip()
                return value
        return None

    for candidate in {tag, tag.upper(), tag.lower()}:
        element = source.find(f".//{candidate}")
        if element is not None and element.text:
            return element.text.strip()
    return None


def _normalize_code(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ensure_success(
    source: Dict[str, Any] | ET.Element,
    endpoint: str,
    *,
    raw_payload: Dict[str, Any] | None = None,
) -> None:
    code = _normalize_code(_extract_value(source, "RESULT_CODE"))
    if code and code not in COUFUN_SUCCESS_CODES:
        message = _extract_value(source, "RESULT_MSG")
        catalog = COUFUN_RESULT_CODE_MESSAGES.get(code)
        detail = message or catalog or "Unknown error"
        raise CoufunAPIError(
            f"{endpoint} 실패({code}): {detail}",
            code=code,
            retryable=code in COUFUN_RETRYABLE_CODES,
            payload=raw_payload,
        )


def _run_with_retry(operation: str, func: Callable[[], T]) -> T:
    attempt = 1
    while True:
        try:
            return func()
        except CoufunAPIError as exc:
            if (
                not exc.retryable
                or attempt >= MAX_RETRY_ATTEMPTS
                or settings.coufun_mock_mode
            ):
                raise
            delay = min(BASE_RETRY_DELAY * (2 ** (attempt - 1)), 2.0)
            time.sleep(delay)
            attempt += 1
