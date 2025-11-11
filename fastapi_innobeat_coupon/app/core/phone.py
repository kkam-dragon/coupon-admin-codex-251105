from __future__ import annotations

import re

PHONE_PATTERN = re.compile(r"^010\d{8}$")


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits or None


def is_valid_phone(phone: str | None) -> bool:
    if not phone:
        return False
    return bool(PHONE_PATTERN.match(phone))


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = normalize_phone(phone)
    if not digits or len(digits) < 4:
        return "****"
    prefix = digits[:3]
    suffix = digits[-4:]
    return f"{prefix}-****-{suffix}"
