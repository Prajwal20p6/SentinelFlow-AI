"""
SentinelFlow AI — Authentication Service
Handles user registration, login, MFA setup, and token management with session tracking.
"""

import pyotp
import qrcode
import io
import base64
import secrets
import jwt
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from ..core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from ..core.config import get_settings
from ..core.observability import logger
from ..models.models import User, UserSession

settings = get_settings()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.hashed_password):
        # Migrating bcrypt passwords to Argon2 transparently on successful login
        if not user.hashed_password.startswith("$argon2"):
            user.hashed_password = hash_password(password)
            db.commit()
            logger.info("user_password_migrated_to_argon2", email=email)
        return user
    return None


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str = "",
    role: str = "engineer",
    organization_id: str = None,
    email_verified: bool = False,
    is_active: bool = False,
) -> User:
    """Create a new user with hashed password."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        organization_id=organization_id,
        email_verified=email_verified,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def generate_tokens(user: User, db: Session, ip_address: str = None, user_agent: str = None) -> dict:
    """Generate access and refresh tokens for a user and track the session."""
    token_data = {"sub": user.email, "role": user.role, "user_id": user.id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Store refresh token in user_sessions table
    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)

    # Track login stats
    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def refresh_user_session(db: Session, refresh_token: str, ip_address: str = None, user_agent: str = None) -> dict | None:
    """Validate refresh token from DB and rotate it."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            return None
    except Exception:
        return None

    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.is_revoked == False
    ).first()

    if not session:
        return None

    # SQLite datetime might not have tzinfo, make it offset-aware
    expires_at = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
    if expires_at < datetime.now(timezone.utc):
        return None

    user = session.user
    if not user or not user.is_active:
        return None

    # Rotate refresh token: revoke old one
    session.is_revoked = True
    db.commit()

    # Generate new tokens
    return generate_tokens(user, db, ip_address, user_agent)


def revoke_session(db: Session, refresh_token: str) -> bool:
    """Revoke a specific session by its refresh token."""
    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    if session:
        session.is_revoked = True
        db.commit()
        return True
    return False


def revoke_all_sessions(db: Session, user_id: int):
    """Revoke all active sessions for a user (e.g. on password reset)."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False
    ).all()
    for s in sessions:
        s.is_revoked = True
    db.commit()


def setup_mfa(user: User, db: Session) -> dict:
    """Generate a new TOTP secret for MFA setup with local/offline QR code."""
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    db.commit()

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="SentinelFlow AI",
    )

    # Local QR code generation as base64 PNG data URI
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    qr_uri = f"data:image/png;base64,{qr_base64}"

    return {
        "secret": secret,
        "qr_uri": qr_uri,
        "message": "Scan the QR code with your authenticator app, then verify with a code.",
    }


def verify_mfa_code(user: User, code: str) -> bool:
    """Verify a TOTP code or check against one-time backup codes."""
    if not user.mfa_secret:
        return False

    # Check standard TOTP
    totp = pyotp.TOTP(user.mfa_secret)
    if totp.verify(code, valid_window=1):
        return True

    # Check backup codes
    if user.mfa_backup_codes:
        codes = user.mfa_backup_codes.split(",")
        if code in codes:
            codes.remove(code)
            user.mfa_backup_codes = ",".join(codes) if codes else None
            return True

    return False


def enable_mfa(user: User, db: Session) -> list[str]:
    """Enable MFA and generate backup codes."""
    user.mfa_enabled = True
    backup_codes = [secrets.token_hex(4) for _ in range(5)]
    user.mfa_backup_codes = ",".join(backup_codes)
    db.commit()
    return backup_codes


def disable_mfa(user: User, db: Session) -> None:
    """Disable MFA and clear secret and backup codes."""
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    db.commit()


def generate_verification_token(email: str) -> str:
    """Generate a stateless email verification JWT."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": email, "exp": expire, "type": "email_verify"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generate_reset_token(email: str) -> str:
    """Generate a stateless password reset JWT."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": email, "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def seed_default_users(db: Session) -> None:
    """Seed default users for development/demo mode with verified status."""
    defaults = [
        {"email": "admin@sentinelflow.ai", "password": "admin123", "full_name": "Admin User", "role": "admin"},
        {"email": "engineer@sentinelflow.ai", "password": "eng123", "full_name": "SRE Engineer", "role": "engineer"},
        {"email": "viewer@sentinelflow.ai", "password": "view123", "full_name": "Dashboard Viewer", "role": "viewer"},
        {"email": "judge@sentinelflow.ai", "password": "JudgeDemo123!", "full_name": "Hackathon Judge", "role": "engineer"},
    ]

    for u in defaults:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if not existing:
            create_user(
                db=db,
                email=u["email"],
                password=u["password"],
                full_name=u["full_name"],
                role=u["role"],
                email_verified=True,
                is_active=True,
            )
            logger.info("seed_user_created", email=u['email'], role=u['role'])
        else:
            existing.hashed_password = hash_password(u["password"])
            existing.is_active = True
            existing.email_verified = True
            db.commit()
            logger.info("seed_user_synced", email=u['email'])
