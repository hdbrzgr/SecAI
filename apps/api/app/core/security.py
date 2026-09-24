import base64
import hashlib
import secrets
import time

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import get_settings

# argon2id with the library's RFC 9106 "low memory" defaults.
_hasher = PasswordHasher()
# Verified against when the user does not exist, so timing doesn't reveal accounts.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Session tokens are stored hashed so a database leak doesn't hand out live sessions."""
    return hashlib.sha256(token.encode()).hexdigest()


def _fernet() -> Fernet:
    key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"secai-mfa-secret-encryption"
    ).derive(get_settings().secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str | None:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return None


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="SecAI")


def verify_totp(secret: str, code: str, last_counter: int | None) -> int | None:
    """Return the matched time-step counter, or None. Rejects reuse of an already used code."""
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return None
    totp = pyotp.TOTP(secret)
    now_counter = int(time.time()) // totp.interval
    # Allow one step of clock drift either way.
    for counter in (now_counter - 1, now_counter, now_counter + 1):
        if last_counter is not None and counter <= last_counter:
            continue
        if secrets.compare_digest(totp.generate_otp(counter), code):
            return counter
    return None
