import pytest
import json
from datetime import datetime, timezone, timedelta
from app.models.models import Incident, TimelineEvent
from app.services.mitre_service import (
    lookup_mitre_technique,
    map_incident_to_mitre,
    build_causal_timeline,
    build_kill_chain_timeline,
    analyze_timeline_forensics,
    seed_phishing_scenario
)

def test_mitre_mappings():
    # Verify technique details lookup
    tech = lookup_mitre_technique("T1566")
    assert tech is not None
    assert tech["tactic"] == "Initial Access"
    assert "Phishing" in tech["name"]

    # Verify incident mappings
    assert map_incident_to_mitre("UNAUTHORIZED_ACCESS") == "T1078"
    assert map_incident_to_mitre("CPU_SPIKE") == "T1059.001"


def test_causal_timeline_sorting():
    # 1. Create unsorted events where causal order disagrees with chronological timestamps
    base_time = datetime.now(timezone.utc)
    
    e1 = TimelineEvent(id=1, incident_id=1, event_type="DETECTED", title="E1", timestamp=base_time + timedelta(seconds=10), parent_event_id=None)
    e2 = TimelineEvent(id=2, incident_id=1, event_type="DETECTED", title="E2", timestamp=base_time + timedelta(seconds=5), parent_event_id=1) # Causal order: 1 -> 2
    e3 = TimelineEvent(id=3, incident_id=1, event_type="DETECTED", title="E3", timestamp=base_time + timedelta(seconds=20), parent_event_id=2) # Causal order: 2 -> 3
    
    unsorted = [e3, e1, e2]
    sorted_events = build_causal_timeline(unsorted)
    
    assert [e.id for e in sorted_events] == [1, 2, 3]


def test_timeline_forensics_dwell_time():
    base_time = datetime.now(timezone.utc)
    e1 = TimelineEvent(id=1, incident_id=1, event_type="DETECTED", title="Start", timestamp=base_time, mitre_technique="T1566")
    e2 = TimelineEvent(id=2, incident_id=1, event_type="DETECTED", title="Stop", timestamp=base_time + timedelta(seconds=120), mitre_technique="T1048")
    
    analysis = analyze_timeline_forensics([e1, e2])
    assert analysis["dwell_time_seconds"] == 120.0
    assert len(analysis["transitions"]) == 1
    assert analysis["transitions"][0]["from_tactic"] == "Initial Access"
    assert analysis["transitions"][0]["to_tactic"] == "Exfiltration"
    assert "Execution" in "".join(analysis["missing_suggestions"])


def test_phishing_scenario_seeding(db_session):
    incident = Incident(
        correlation_id="phish-seed-test-correlation",
        source="Gateway Scanner",
        metric_type="EMAIL_GATEWAY",
        severity="HIGH",
        title="Spam mailbox indicators detected",
        description="Multiple suspicious outbound email requests detected."
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    events = seed_phishing_scenario(db_session, incident.id)
    assert len(events) == 7
    assert events[0].mitre_technique == "T1566.001"
    assert events[-1].mitre_technique == "T1048"


def test_router_mitre_timeline_formatting(client, db_session):
    # Setup test user authentication headers
    from app.core.security import hash_password
    from app.models.models import User
    
    user = db_session.query(User).filter(User.email == "mitre-auditor@sentinelflow.ai").first()
    if not user:
        user = User(
            email="mitre-auditor@sentinelflow.ai",
            hashed_password=hash_password("auditorpass"),
            full_name="Forensic Auditor",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    resp = client.post("/api/v1/auth/login", json={
        "email": "mitre-auditor@sentinelflow.ai",
        "password": "auditorpass"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup simulated phishing incident
    incident = Incident(
        correlation_id="phish-router-test-correlation",
        source="Gateway Scanner",
        metric_type="EMAIL_GATEWAY",
        severity="HIGH",
        title="Phishing test alerts",
        description="Outbound command execution detected."
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # Trigger seeding via POST
    res_seed = client.post(f"/api/v1/incidents/{incident.id}/timeline/simulate-phishing", headers=headers)
    assert res_seed.status_code == 201
    assert res_seed.json()["status"] == "seeded"

    # 1. Fetch chronological format (default)
    res_default = client.get(f"/api/v1/incidents/{incident.id}/timeline", headers=headers)
    assert res_default.status_code == 200
    timeline = res_default.json()
    assert len(timeline) == 7
    assert timeline[0]["mitre_technique"] == "T1566.001"

    # 2. Fetch causal format
    res_causal = client.get(f"/api/v1/incidents/{incident.id}/timeline?format=causal", headers=headers)
    assert res_causal.status_code == 200
    assert len(res_causal.json()) == 7

    # 3. Fetch kill chain format
    res_kc = client.get(f"/api/v1/incidents/{incident.id}/timeline?format=kill_chain", headers=headers)
    assert res_kc.status_code == 200
    kc_groups = res_kc.json()
    assert len(kc_groups) > 0
    assert "tactic" in kc_groups[0]

    # 4. Fetch full analysis format
    res_full = client.get(f"/api/v1/incidents/{incident.id}/timeline?format=full", headers=headers)
    assert res_full.status_code == 200
    full_data = res_full.json()
    assert "chronological" in full_data
    assert "causal" in full_data
    assert "kill_chain" in full_data
    assert "forensics" in full_data
    assert full_data["forensics"]["dwell_time_seconds"] == 900.0
