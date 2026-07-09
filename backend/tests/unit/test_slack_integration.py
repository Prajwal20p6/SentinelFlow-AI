import pytest
from app.services.slack_service import format_incident_slack_block, post_slack_notification
from app.models.models import Incident, NotificationLog, User
from app.core.security import hash_password

def test_slack_block_formatting(db_session):
    incident = Incident(
        id=99,
        title="Test Slack Format Anomaly",
        source="k8s",
        metric_type="DISK_FULL",
        severity="high",
        status="DETECTED",
        description="Kubernetes host node partition full",
        suggested_action="rm -rf /tmp/cache"
    )
    blocks_payload = format_incident_slack_block(incident)
    assert "blocks" in blocks_payload
    assert "actions" in [b["type"] for b in blocks_payload["blocks"]]
    
    actions_block = [b for b in blocks_payload["blocks"] if b["type"] == "actions"][0]
    elements = actions_block["elements"]
    assert len(elements) == 2
    assert elements[0]["action_id"] == "approve"
    assert elements[1]["action_id"] == "reject"

def test_slack_notification_fallback_logging(db_session):
    incident = Incident(
        title="Mock Incident",
        source="test",
        metric_type="CPU_SPIKE",
        severity="medium",
        status="DETECTED",
        description="CPU Spike details",
        correlation_id="slack-fallback-cid-100"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # Trigger post notification (by default settings.SLACK_ENABLED is False or flags disabled)
    res = post_slack_notification(db_session, incident, "Test Notification Message")
    assert res is True
    
    # Check if a NotificationLog got created
    log = db_session.query(NotificationLog).filter(NotificationLog.incident_id == incident.id).first()
    assert log is not None
    assert log.channel == "slack"
    assert log.status == "bypassed" or log.status == "delivered"
    assert "Test Notification" in log.message

def test_slack_interactive_webhook_approve(client, db_session):
    # 1. Create a dummy incident requiring approval
    incident = Incident(
        title="Slack Approval Test",
        source="k8s",
        metric_type="UNAUTHORIZED_ACCESS",
        severity="high",
        status="PENDING_APPROVAL",
        description="Unauthorized namespace check",
        suggested_action="kubectl get namespaces",
        correlation_id="slack-webhook-cid-555"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 2. Trigger webhook callback with action 'approve'
    payload = {
        "text": "Approved via interactive button",
        "channel": "#sentinelflow-alerts",
        "action": "approve",
        "incident_id": incident.id
    }
    resp = client.post("/api/v1/integrations/slack/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
    
    # Verify status changed to EXECUTED
    db_session.refresh(incident)
    assert incident.status == "EXECUTED"

def test_slack_interactive_webhook_reject(client, db_session):
    # 1. Create a dummy incident requiring approval
    incident = Incident(
        title="Slack Rejection Test",
        source="k8s",
        metric_type="UNAUTHORIZED_ACCESS",
        severity="high",
        status="PENDING_APPROVAL",
        description="Unauthorized namespace check",
        suggested_action="kubectl get namespaces",
        correlation_id="slack-webhook-cid-666"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 2. Trigger webhook callback with action 'reject'
    payload = {
        "text": "Rejected via interactive button",
        "channel": "#sentinelflow-alerts",
        "action": "reject",
        "incident_id": incident.id
    }
    resp = client.post("/api/v1/integrations/slack/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
    
    # Verify status changed to REJECTED
    db_session.refresh(incident)
    assert incident.status == "REJECTED"
