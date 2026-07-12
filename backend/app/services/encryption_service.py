"""
SentinelFlow AI — Database Encryption Service
Implements AES-256 Fernet column encryption with transparent multi-key version rotation.
"""

import base64
import hashlib
from typing import List, Optional
from cryptography.fernet import Fernet
from ..core.config import get_settings
from ..core.observability import logger

settings = get_settings()

class EncryptionService:
    """Manages symmetric cryptographic keys and transparent column encryption/decryption."""

    _fernets: List[Fernet] = []
    _legacy_key: bytes = b""

    @classmethod
    def _init_keys(cls):
        """Initializes the active and rotated Fernet key instances."""
        if cls._fernets:
            return

        # Derive legacy XOR key
        cls._legacy_key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()

        # Parse encryption keys (can be list of comma-separated secrets or Fernet keys)
        keys_source = getattr(settings, "ENCRYPTION_KEYS", "") or settings.ENCRYPTION_KEY
        key_list = [k.strip() for k in keys_source.split(",") if k.strip()]

        for key_str in key_list:
            try:
                # If key is already a valid 32-byte base64 Fernet key, use it
                decoded = base64.urlsafe_b64decode(key_str)
                if len(decoded) == 32:
                    cls._fernets.append(Fernet(key_str.encode()))
                    continue
            except Exception:
                pass

            # Otherwise, derive a valid Fernet key from the raw password
            derived = base64.urlsafe_b64encode(hashlib.sha256(key_str.encode()).digest())
            cls._fernets.append(Fernet(derived))

        if not cls._fernets:
            # Emergency fallback key derivation
            fallback = base64.urlsafe_b64encode(hashlib.sha256(b"sentinelflow-fallback-secret-key").digest())
            cls._fernets.append(Fernet(fallback))

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypts a string using the primary (latest) Fernet key.
        Returns ciphertext formatted with version prefix: v0:<ciphertext>
        """
        if not plaintext:
            return plaintext
        cls._init_keys()
        
        # Primary key is the first key (index 0)
        primary_fernet = cls._fernets[0]
        encrypted_bytes = primary_fernet.encrypt(plaintext.encode("utf-8"))
        
        # Return format v0:base64_string
        return f"v0:{encrypted_bytes.decode('utf-8')}"

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """
        Decrypts ciphertext by inspecting version prefix, falling back to older keys,
        and finally falling back to legacy XOR decryption to maintain backward compatibility.
        """
        if not ciphertext:
            return ciphertext
        cls._init_keys()

        # 1. Parse version prefix (e.g. "v0:gAAAAAB...")
        if ciphertext.startswith("v") and ":" in ciphertext:
            parts = ciphertext.split(":", 1)
            try:
                v_index = int(parts[0][1:])
                raw_cipher = parts[1]
                if 0 <= v_index < len(cls._fernets):
                    decrypted_bytes = cls._fernets[v_index].decrypt(raw_cipher.encode("utf-8"))
                    return decrypted_bytes.decode("utf-8")
            except Exception as e:
                logger.warning("versioned_decryption_failed", error=str(e))
                # Fall through to try all keys cascadingly

        # 2. Cascade try all Fernet keys
        stripped_cipher = ciphertext.split(":", 1)[1] if (ciphertext.startswith("v") and ":" in ciphertext) else ciphertext
        for idx, f in enumerate(cls._fernets):
            try:
                decrypted_bytes = f.decrypt(stripped_cipher.encode("utf-8"))
                return decrypted_bytes.decode("utf-8")
            except Exception:
                continue

        # 3. Legacy XOR cipher fallback
        try:
            encrypted = base64.b64decode(ciphertext.encode("utf-8"))
            decrypted = bytes(b ^ cls._legacy_key[i % len(cls._legacy_key)] for i, b in enumerate(encrypted))
            return decrypted.decode("utf-8")
        except Exception as xor_err:
            logger.warning("legacy_decryption_failed", error=str(xor_err))
            # Return original ciphertext if all decryptions fail
            return ciphertext
