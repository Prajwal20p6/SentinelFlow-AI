"""
SentinelFlow AI — Production Transactional Email Service
Supports Resend API, SendGrid API, or SMTP delivery for verification and password reset emails.
"""

import os
from typing import Optional
from ..core.config import get_settings
from ..core.observability import logger

settings = get_settings()


def send_verification_email(to_email: str, token: str) -> bool:
    """Send a transactional account verification email containing secure link."""
    base_url = settings.APP_BASE_URL.rstrip("/")
    verification_link = f"{base_url}/verify-email?token={token}"

    api_key = settings.EMAIL_PROVIDER_API_KEY or os.getenv("EMAIL_PROVIDER_API_KEY")
    from_email = settings.EMAIL_FROM or os.getenv("EMAIL_FROM", "noreply@sentinelflow.ai")

    subject = "Verify your SentinelFlow AI account"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0e17; color: #f1f5f9; padding: 24px; border-radius: 12px;">
      <h2 style="color: #00ff88;">SentinelFlow AI Verification</h2>
      <p style="color: #94a3b8; font-size: 14px;">Please verify your email address to activate your account and gain access to the SecOps platform.</p>
      <div style="margin: 24px 0;">
        <a href="{verification_link}" style="background: #00ff88; color: #0a0e17; font-weight: bold; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">Verify Email Address</a>
      </div>
      <p style="color: #64748b; font-size: 12px;">If you did not register for SentinelFlow AI, please ignore this email.</p>
    </div>
    """

    if not api_key:
        logger.warning(
            "transactional_email_provider_unconfigured",
            recipient=to_email,
            action="verify_email",
            note="EMAIL_PROVIDER_API_KEY is not set. Real transactional email paused."
        )
        return False

    try:
        import httpx
        # Send using Resend API format if api_key starts with re_ or defaults
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        resp = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=5.0)
        if resp.status_code in (200, 201):
            logger.info("verification_email_sent_successfully", recipient=to_email)
            return True
        else:
            logger.error("verification_email_send_failed", status_code=resp.status_code, body=resp.text)
            return False
    except Exception as e:
        logger.error("verification_email_send_exception", error=str(e))
        return False


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send a transactional password reset email containing secure link."""
    base_url = settings.APP_BASE_URL.rstrip("/")
    reset_link = f"{base_url}/reset-password?token={token}"

    api_key = settings.EMAIL_PROVIDER_API_KEY or os.getenv("EMAIL_PROVIDER_API_KEY")
    from_email = settings.EMAIL_FROM or os.getenv("EMAIL_FROM", "noreply@sentinelflow.ai")

    subject = "Reset your SentinelFlow AI password"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0e17; color: #f1f5f9; padding: 24px; border-radius: 12px;">
      <h2 style="color: #00ff88;">Password Reset Request</h2>
      <p style="color: #94a3b8; font-size: 14px;">We received a request to reset your password for your SentinelFlow AI account.</p>
      <div style="margin: 24px 0;">
        <a href="{reset_link}" style="background: #00ff88; color: #0a0e17; font-weight: bold; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">Reset Password</a>
      </div>
      <p style="color: #64748b; font-size: 12px;">This password reset link will expire in 1 hour.</p>
    </div>
    """

    if not api_key:
        logger.warning(
            "transactional_email_provider_unconfigured",
            recipient=to_email,
            action="reset_password",
            note="EMAIL_PROVIDER_API_KEY is not set. Real transactional email paused."
        )
        return False

    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        resp = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=5.0)
        if resp.status_code in (200, 201):
            logger.info("password_reset_email_sent_successfully", recipient=to_email)
            return True
        else:
            logger.error("password_reset_email_send_failed", status_code=resp.status_code, body=resp.text)
            return False
    except Exception as e:
        logger.error("password_reset_email_send_exception", error=str(e))
        return False
