import pytest
import pyotp
from sqlalchemy.orm import Session
from app.models.models import User
from app.core.security import hash_password
from app.services.auth_service import setup_mfa, enable_mfa, verify_mfa_code, disable_mfa

@pytest.fixture
def test_user(db_session: Session):
    """Fixture creating a test user in DB."""
    user = User(
        email="mfa_test_user@sentinelflow.ai",
        hashed_password=hash_password("MfaPassword123!"),
        role="engineer",
        mfa_enabled=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_mfa_setup_and_encrypted_secret_roundtrip(db_session: Session, test_user: User):
    """Verify MFA setup, EncryptedText column persistence round-trip, and TOTP verification."""
    # 1. Setup MFA
    res = setup_mfa(test_user, db_session)
    assert "secret" in res
    assert "qr_uri" in res
    assert res["qr_uri"].startswith("data:image/png;base64,")

    secret = res["secret"]

    # 2. Refresh from DB to exercise EncryptedText decryption
    db_session.expire_all()
    reloaded_user = db_session.query(User).filter(User.id == test_user.id).first()
    assert reloaded_user.mfa_secret == secret

    # 3. Generate valid TOTP token and verify
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    assert verify_mfa_code(reloaded_user, valid_code) is True

def test_mfa_enable_and_single_use_backup_codes(db_session: Session, test_user: User):
    """Verify MFA enablement, backup code generation, and single-use backup code consumption."""
    setup_mfa(test_user, db_session)
    backup_codes = enable_mfa(test_user, db_session)

    assert len(backup_codes) == 5
    assert test_user.mfa_enabled is True

    first_backup_code = backup_codes[0]

    # Verify backup code works
    assert verify_mfa_code(test_user, first_backup_code) is True

    # Verify backup code is consumed and single-use (fails second time)
    assert verify_mfa_code(test_user, first_backup_code) is False

def test_mfa_invalid_code_rejected(db_session: Session, test_user: User):
    """Verify invalid TOTP code and invalid backup code are rejected."""
    setup_mfa(test_user, db_session)
    enable_mfa(test_user, db_session)

    assert verify_mfa_code(test_user, "000000") is False
    assert verify_mfa_code(test_user, "invalid_backup_code") is False

def test_mfa_disable_clears_credentials(db_session: Session, test_user: User):
    """Verify disabling MFA clears mfa_secret and backup codes in DB."""
    setup_mfa(test_user, db_session)
    enable_mfa(test_user, db_session)

    disable_mfa(test_user, db_session)

    db_session.expire_all()
    reloaded_user = db_session.query(User).filter(User.id == test_user.id).first()

    assert reloaded_user.mfa_enabled is False
    assert reloaded_user.mfa_secret is None
    assert reloaded_user.mfa_backup_codes is None
    assert verify_mfa_code(reloaded_user, "123456") is False
