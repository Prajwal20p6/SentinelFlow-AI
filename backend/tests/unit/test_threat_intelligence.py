import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.models import Incident, ThreatIntelEnrichment, TimelineEvent, IncidentLog
from app.services.threat_intel_service import (
    extract_iocs_from_text,
    query_threat_intel,
    auto_enrich_incident_threats,
    save_threat_intel_cache,
    get_threat_intel_cache
)
from app.services.threat_intel_agent import ThreatIntelAgent

settings = get_settings()


def test_ioc_extraction():
    sample_text = (
        "SecOps alert on IP 185.220.101.5 and remote domain malicious-site.ru. "
        "The download md5 was e99a182dd84f3d9cc123456789abcdef. "
        "For details contact phish@hacker-site.org or view https://exploit-db.org/kit."
    )
    extracted = extract_iocs_from_text(sample_text)
    types = [e["type"] for e in extracted]
    values = [e["value"] for e in extracted]

    assert "ip" in types
    assert "185.220.101.5" in values

    assert "domain" in types
    assert "malicious-site.ru" in values

    assert "hash" in types
    assert "e99a182dd84f3d9cc123456789abcdef" in values

    assert "email" in types
    assert "phish@hacker-site.org" in values

    assert "url" in types
    assert "https://exploit-db.org/kit" in values


def test_threat_intel_caching(db_session):
    ioc_type = "ip"
    ioc_val = "185.220.101.5"
    
    # Pre-cache
    save_threat_intel_cache(
        db_session, ioc_type, ioc_val, "Test VT", "HIGH", {"detected": True}
    )

    # Get from cache
    cached = get_threat_intel_cache(db_session, ioc_type, ioc_val)
    assert cached is not None
    assert cached.threat_level == "HIGH"
    
    # Get with expired threshold (mocking old cache)
    cached.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db_session.commit()

    expired = get_threat_intel_cache(db_session, ioc_type, ioc_val)
    assert expired is None  # Should be filtered out due to 24h TTL limit


def test_threat_intel_agent_risk_scoring(db_session):
    agent = ThreatIntelAgent()
    payload = "We observed repeated traffic payload requests to 185.220.101.5."
    assessment = agent.assess_security_risk(db_session, payload)

    assert assessment["overall_threat_level"] == "HIGH"
    assert assessment["risk_score"] >= 80
    assert len(assessment["findings"]) == 1
    assert "Block IP" in assessment["recommendations"]


def test_threat_intel_pipeline_auto_enrichment(db_session):
    # Setup incident with high threat Indicators
    incident = Incident(
        correlation_id="threat-intel-pipeline-test",
        source="External IDS",
        metric_type="MALICIOUS_IP",
        severity="WARNING",
        title="Suspicious connection on internal routes",
        description="Outbound payload connection routed to malicious IP: 185.220.101.5."
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    res = auto_enrich_incident_threats(db_session, incident.id)
    assert res["threat_level"] == "HIGH"
    assert res["iocs_enriched_count"] == 1

    # Verify database updates
    db_session.refresh(incident)
    assert incident.severity == "CRITICAL"
    assert "iptables" in incident.suggested_action

    # Check that a threat enrichment timeline log is saved
    log = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == incident.id,
        IncidentLog.stage == "THREAT_INTEL"
    ).first()
    assert log is not None
    assert "Overall Threat Level: HIGH" in log.message


def test_alert_ingestion_api_endpoints(client, db_session):
    # Setup API endpoint requests
    headers = {"X-API-Key": settings.THREAT_INTEL_API_KEY}
    
    # 1. Invalid API Key
    res_bad_key = client.post(
        "/api/v1/integrations/alerts",
        headers={"X-API-Key": "wrong-key"},
        json={
            "source": "Splunk",
            "alert_type": "BruteForce",
            "severity": "high",
            "iocs": []
        }
    )
    assert res_bad_key.status_code == 401

    # 2. Ingest Normalized Alert with high-risk domain
    payload = {
        "source": "Sentinel",
        "alert_type": "DNS_Blacklist",
        "severity": "warning",
        "iocs": [
            {"type": "domain", "value": "phishing-bank.com"}
        ],
        "raw_data": {"context_metadata": "Sample Sentinel ThreatIntel log"}
    }
    
    res = client.post("/api/v1/integrations/alerts", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "ingested"
    assert data["threat_enrichment"]["threat_level"] == "HIGH"

    # Verify Incident created
    inc = db_session.query(Incident).filter(Incident.id == data["incident_id"]).first()
    assert inc is not None
    assert inc.severity == "CRITICAL"

    # 3. Webhook splunk mapper
    splunk_payload = {
        "search_name": "Splunk Malicious IP Scanner",
        "result": {
            "severity": "critical",
            "src_ip": "45.143.203.14",
            "message": "Outbound scanning attempts registered."
        }
    }
    res_splunk = client.post("/api/v1/integrations/webhooks/splunk", headers=headers, json=splunk_payload)
    assert res_splunk.status_code == 201
    assert res_splunk.json()["threat_enrichment"]["threat_level"] == "HIGH"
