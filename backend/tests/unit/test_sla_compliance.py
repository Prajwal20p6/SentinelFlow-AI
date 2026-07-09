import pytest
from datetime import datetime, timezone, timedelta
from app.models.models import Incident, AlertFingerprint
from app.services.sla_service import SLAService
from app.services.compliance_service import ComplianceService

def test_sla_targets_and_calculation(db_session):
    now = datetime.now(timezone.utc)
    
    # 1. P0 critical incident created now (should be active and healthy since it's < 15 min target)
    incident_p0 = Incident(
        correlation_id="corr-sla-p0",
        source="gateway",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="Payment Gateway latency spike",
        description="High CPU on payment-gateway service",
        status="DETECTED",
        sla_target="P0",
        sla_breach_at=now + timedelta(minutes=15),
        created_at=now
    )
    db_session.add(incident_p0)
    db_session.commit()
    db_session.refresh(incident_p0)

    # Calculate SLA
    sla_data = SLAService.calculate_incident_sla(db_session, incident_p0)
    assert sla_data["severity_tier"] == "P0"
    assert sla_data["mttr_status"] == "HEALTHY"
    assert sla_data["seconds_remaining"] > 0
    assert sla_data["percent_elapsed"] < 80.0

    # 2. P1 incident created 2 hours ago and resolved 30 mins ago (should be breached since target is 1 hour)
    incident_p1 = Incident(
        correlation_id="corr-sla-p1",
        source="auth-service",
        metric_type="MEM_SPIKE",
        severity="HIGH",
        title="Auth service memory leak",
        description="Auth service OOM imminent",
        status="RESOLVED",
        sla_target="P1",
        sla_breach_at=now - timedelta(hours=1),
        created_at=now - timedelta(hours=2),
        resolved_at=now - timedelta(minutes=30)
    )
    db_session.add(incident_p1)
    db_session.commit()
    db_session.refresh(incident_p1)

    sla_data_p1 = SLAService.calculate_incident_sla(db_session, incident_p1)
    assert sla_data_p1["severity_tier"] == "P1"
    assert sla_data_p1["mttr_status"] == "BREACHED"
    assert sla_data_p1["is_active"] is False

    # Check SLA summary metrics
    summary = SLAService.get_sla_summary_metrics(db_session)
    assert summary["breached_count"] >= 1
    assert summary["compliance_rate_percent"] >= 0.0


def test_compliance_mapping_and_checklist(db_session):
    now = datetime.now(timezone.utc)
    
    # 1. GDPR Breach (PII access credential breach)
    incident_gdpr = Incident(
        correlation_id="corr-comp-gdpr",
        source="auth-service",
        metric_type="SECURITY_VIOLATION",
        severity="CRITICAL",
        title="Unauthorized credential leak detected",
        description="Leakage of raw API keys and database access credentials in debug logs",
        status="RESOLVED",
        created_at=now - timedelta(minutes=10),
        resolved_at=now
    )
    db_session.add(incident_gdpr)
    db_session.commit()
    db_session.refresh(incident_gdpr)

    regs = ComplianceService.map_incident_regulations(incident_gdpr)
    assert "GDPR" in regs
    assert "SOC2" in regs

    # Generate checklist
    checklist_data = ComplianceService.generate_compliance_checklist(db_session, incident_gdpr)
    assert checklist_data["compliance_score_percent"] >= 50.0
    
    # Generate full report
    report = ComplianceService.generate_regulatory_report(db_session, incident_gdpr)
    assert report["incident_id"] == incident_gdpr.id
    assert report["compliance_score_percent"] == checklist_data["compliance_score_percent"]
    assert any(fw["name"].startswith("GDPR") for fw in report["applicable_frameworks"])
