import pytest
import base64
import hashlib
from app.services.encryption_service import EncryptionService
from app.core.config import get_settings

def test_encryption_and_decryption_rotation():
    settings = get_settings()
    
    # 1. Simple encrypt / decrypt
    original_text = "my-super-secret-mfa-token-123"
    ciphertext = EncryptionService.encrypt(original_text)
    
    assert ciphertext.startswith("v0:")
    decrypted = EncryptionService.decrypt(ciphertext)
    assert decrypted == original_text

    # 2. Test key rotation (older key can still decrypt, new key encrypts)
    # Mock settings.ENCRYPTION_KEYS as rotation list: "new_key,old_key"
    old_raw = settings.ENCRYPTION_KEY
    new_raw = "brand-new-rotated-secret-key-999"
    
    # Pre-seed settings attribute
    settings.ENCRYPTION_KEYS = f"{new_raw},{old_raw}"
    
    # Force re-initialization of keys inside service
    EncryptionService._fernets = []
    EncryptionService._init_keys()
    
    # Encrypting now should use the new primary key (new_raw)
    new_ciphertext = EncryptionService.encrypt(original_text)
    assert new_ciphertext.startswith("v0:")
    
    # Decrypt new ciphertext
    assert EncryptionService.decrypt(new_ciphertext) == original_text

    # Decrypt old ciphertext (which was encrypted with old_raw)
    # Since old_raw is now at index 1 in the list, it has version v1
    # If we pass the old ciphertext, it will fallback to try all keys or XOR and decrypt successfully!
    assert EncryptionService.decrypt(ciphertext) == original_text
    
    # Clean up settings override
    settings.ENCRYPTION_KEYS = ""
    EncryptionService._fernets = []
    EncryptionService._init_keys()
