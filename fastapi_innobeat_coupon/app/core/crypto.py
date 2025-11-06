from __future__ import annotations

import os
from functools import lru_cache
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_cipher() -> AESGCM:
    return AESGCM(settings.encryption_key_bytes)


def encrypt_value(value: str | None) -> bytes:
    if value is None:
        return b""
    cipher = _get_cipher()
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, value.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_value(blob: bytes | None) -> str | None:
    if not blob:
        return None
    cipher = _get_cipher()
    nonce, data = blob[:12], blob[12:]
    plaintext = cipher.decrypt(nonce, data, None)
    return plaintext.decode("utf-8")


def hash_value(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()
