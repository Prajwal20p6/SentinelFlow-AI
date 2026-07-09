"""
SentinelFlow AI — Security Utilities
JWT token management, password hashing, AES-256 encryption, and TOTP MFA.
"""

import hashlib
import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from argon2 import PasswordHasher

from .config import get_settings

settings = get_settings()

ph = PasswordHasher()

# ── Password Hashing ────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 or legacy bcrypt hash."""
    if hashed_password.startswith("$argon2"):
        try:
            return ph.verify(hashed_password, plain_password)
        except Exception:
            return False
    else:
        # Legacy bcrypt fallback
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False


# ── JWT Token Management ────────────────────────────────────
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token with unique JTI."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": secrets.token_hex(8)
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed JWT refresh token with extended expiry and unique JTI."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(8)
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


# ── AES-256 Column Encryption ───────────────────────────────
def _derive_key() -> bytes:
    """Derive a 32-byte encryption key from the configured secret."""
    return hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()


def encrypt_text(plaintext: str) -> str:
    """Encrypt plaintext using versioned AES-256 Fernet column encryption."""
    from ..services.encryption_service import EncryptionService
    return EncryptionService.encrypt(plaintext)


def decrypt_text(ciphertext: str) -> str:
    """Decrypt versioned AES-256 Fernet column encryption with cascading fallbacks."""
    from ..services.encryption_service import EncryptionService
    return EncryptionService.decrypt(ciphertext)


# ── Tamper-Evident Hashing ───────────────────────────────────
def compute_chain_hash(data: str, prev_hash: str) -> str:
    """Compute a SHA-256 chain hash for tamper-evident audit logging."""
    payload = f"{prev_hash}:{data}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return f"sf-trace-{secrets.token_hex(6)}"
