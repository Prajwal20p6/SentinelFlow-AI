"""
SentinelFlow AI — Slack Notification Service
Manages webhook communications, Block Kit formatting, and HITL interactive loops.
"""

import requests as req_lib
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.observability import logger
from ..models.models import Incident, NotificationLog
from ..services.feature_flag_service import is_enabled, FeatureFlagKey

settings = get_settings()

# ── Message Block Kit Formatters ─────────────────────────────

def format_incident_slack_block(incident: Incident) -> Dict[str, Any]:
    """Format a premium Slack Block Kit message with interactive action buttons."""
    return {
        "text": f"🚨 New Incident #{incident.id} [{incident.severity.upper()}] - {incident.title}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚨 New Incident Detected: #{incident.id}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Type:* `{incident.metric_type}`"},
                    {"type": "mrkdwn", "text": f"*Severity:* `{incident.severity.upper()}`"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:* {incident.description}\n*Suggested Action:* `{incident.suggested_action}`"
                }
            },
            {
                "type": "actions",
                "block_id": f"approval_block_{incident.id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve ✅"},
                        "style": "primary",
                        "action_id": "approve",
                        "value": str(incident.id)
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject ❌"},
                        "style": "danger",
                        "action_id": "reject",
                        "value": str(incident.id)
                    }
                ]
            }
        ]
    }


# ── Slack Communications Wrapper ──────────────────────────────

def post_slack_notification(
    db: Session,
    incident: Incident,
    message: str,
    channel: str = "#sentinelflow-alerts"
) -> bool:
    """
    Send Slack notification. Respects feature flags and settings.
    Falls back gracefully if disabled, logging payload parameters locally.
    """
    # Check feature flag configuration
    slack_active = settings.SLACK_ENABLED or is_enabled(db, FeatureFlagKey.SLACK_NOTIFICATIONS)

    if not slack_active:
        logger.info(
            "Slack Integration disabled. Logging notification trace locally.",
            incident_id=incident.id,
            channel=channel,
            message=message
        )
        
        # Log to DB locally as 'bypassed'
        log = NotificationLog(
            incident_id=incident.id,
            channel="slack",
            recipient=channel,
            message=message,
            status="bypassed"
        )
        db.add(log)
        db.commit()
        return True

    # Assemble block payloads
    payload = format_incident_slack_block(incident)
    payload["channel"] = channel

    status = "failed"
    try:
        if settings.SLACK_WEBHOOK_URL:
            resp = req_lib.post(
                settings.SLACK_WEBHOOK_URL,
                json={
                    "text": message,
                    "channel": channel,
                    "incident_id": incident.id,
                    "action": None
                },
                timeout=5
            )
            if resp.status_code == 200:
                status = "delivered"
    except Exception as e:
        logger.error("Slack post request failed:", error=str(e))

    log = NotificationLog(
        incident_id=incident.id,
        channel="slack",
        recipient=channel,
        message=message,
        status=status
    )
    db.add(log)
    db.commit()
    return status == "delivered"
