from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DoneCodeClassification:
    code: str | None
    label: str
    job_status: str
    coupon_status: str
    retryable: bool
    description: str


SUCCESS_CLASSIFICATION = DoneCodeClassification(
    code="00000",
    label="DELIVERED",
    job_status="COMPLETED",
    coupon_status="DELIVERED",
    retryable=False,
    description="정상 발송",
)


def classify_done_code(code: Optional[str]) -> DoneCodeClassification:
    """
    DONE_CODE → SNAP Job/Coupon 상태 변환.

    참고 문서:
    - MyDocuments/02_LG유플러스/3.LG유플러스-발송결과확인방법.md
    """

    normalized = (code or "").strip()
    if not normalized:
        return DoneCodeClassification(
            code=None,
            label="UNKNOWN",
            job_status="FAILED",
            coupon_status="FAILED",
            retryable=True,
            description="DONE_CODE 미수신",
        )

    if normalized.startswith("0"):
        return SUCCESS_CLASSIFICATION if normalized == "00000" else DoneCodeClassification(
            code=normalized,
            label="DELIVERED",
            job_status="COMPLETED",
            coupon_status="DELIVERED",
            retryable=False,
            description="정상 발송",
        )

    numeric = _to_int(normalized)

    if numeric is not None and _is_gateway_error(numeric):
        return DoneCodeClassification(
            code=normalized,
            label="GATEWAY_ERROR",
            job_status="FAILED",
            coupon_status="FAILED",
            retryable=True,
            description="LG U+ 게이트웨이/전송망 오류",
        )

    if numeric is not None and 90000 <= numeric <= 99999:
        return DoneCodeClassification(
            code=normalized,
            label="AGENT_ERROR",
            job_status="FAILED",
            coupon_status="FAILED",
            retryable=True,
            description="SNAP Agent/시스템 오류",
        )

    return DoneCodeClassification(
        code=normalized,
        label="TELCO_FAILURE",
        job_status="FAILED",
        coupon_status="FAILED",
        retryable=False,
        description="수신자/통신사 오류",
    )


def _is_gateway_error(code_value: int) -> bool:
    """
    21000~25000, 29000 대역은 게이트웨이/네트워크 오류로 분류한다.
    """
    return (21000 <= code_value <= 25999) or (29000 <= code_value <= 29999)


def _to_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None
