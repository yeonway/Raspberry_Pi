from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from .config import get_settings

VERSION = "v1"
NONCE_SIZE = 16
TAG_SIZE = 32


class TokenCryptoError(ValueError):
    pass


def encrypt_token(plain_text: str) -> str:
    plain_text = (plain_text or "").strip()
    if not plain_text:
        raise TokenCryptoError("저장할 토큰이 없습니다.")
    key = _load_key()
    nonce = secrets.token_bytes(NONCE_SIZE)
    cipher_text = _xor_bytes(plain_text.encode("utf-8"), _key_stream(key, nonce))
    tag = hmac.new(key, _mac_body(nonce, cipher_text), hashlib.sha256).digest()
    return ":".join(
        (
            VERSION,
            _b64(nonce),
            _b64(cipher_text),
            _b64(tag),
        )
    )


def decrypt_token(encrypted_text: str) -> str:
    encrypted_text = (encrypted_text or "").strip()
    if not encrypted_text:
        raise TokenCryptoError("암호화된 토큰이 없습니다.")
    try:
        version, nonce_text, cipher_text, tag_text = encrypted_text.split(":", 3)
    except ValueError as exc:
        raise TokenCryptoError("토큰 저장 형식이 올바르지 않습니다.") from exc
    if version != VERSION:
        raise TokenCryptoError("지원하지 않는 토큰 저장 형식입니다.")

    key = _load_key()
    nonce = _unb64(nonce_text)
    cipher = _unb64(cipher_text)
    tag = _unb64(tag_text)
    expected = hmac.new(key, _mac_body(nonce, cipher), hashlib.sha256).digest()
    if len(tag) != TAG_SIZE or not hmac.compare_digest(tag, expected):
        raise TokenCryptoError("토큰 복호화 검증에 실패했습니다.")
    return _xor_bytes(cipher, _key_stream(key, nonce)).decode("utf-8")


def _load_key() -> bytes:
    value = get_settings().token_encryption_key.strip()
    if not value:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY 값이 설정되어 있지 않습니다.")
    return hashlib.sha256(value.encode("utf-8")).digest()


def _mac_body(nonce: bytes, cipher_text: bytes) -> bytes:
    return VERSION.encode("ascii") + b":" + nonce + b":" + cipher_text


def _key_stream(key: bytes, nonce: bytes):
    counter = 0
    while True:
        counter_bytes = counter.to_bytes(8, "big")
        block = hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest()
        for item in block:
            yield item
        counter += 1


def _xor_bytes(data: bytes, stream) -> bytes:
    return bytes(value ^ next(stream) for value in data)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
