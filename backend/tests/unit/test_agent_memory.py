import pytest
import json
from app.services.memory_service import store_memory, retrieve_memory, update_memory, clear_memory, MEMORY_FALLBACK
from app.services.rca_service import run_root_cause_analysis
from app.services.threat_intel_service import auto_enrich_incident_threats
from app.services.workflow_service import run_incident_workflow
from app.models.models import Incident, TimelineEvent, IncidentLog, MastraWorkflowState

def test_memory_crud_operations():
    # 1. Clear any remnants
    clear_memory(999)

    # 2. Store memory
    store_memory(
        collection_name="shared_memory",
        key="test_key",
        value="Initial diagnostic values",
        incident_id=999,
        agent_id="test_agent"
    )

    # 3. Retrieve memory
    memories = retrieve_memory("shared_memory", "diagnostic", incident_id=999)
    assert len(memories) == 1
    assert memories[0]["key"] == "test_key"
    assert memories[0]["value"] == "Initial diagnostic values"
    assert memories[0]["agent_id"] == "test_agent"

    # 4. Update memory (stable hash update-in-place check)
    update_memory(
        collection_name="shared_memory",
        key="test_key",
        value="Updated diagnostic values",
        incident_id=999,
        agent_id="test_agent"
    )
    
    memories_updated = retrieve_memory("shared_memory", "diagnostic", incident_id=999)
    assert len(memories_updated) == 1
    assert memories_updated[0]["value"] == "Updated diagnostic values"

    # 5. Clear memory
    clear_memory(999)
    memories_cleared = retrieve_memory("shared_memory", "diagnostic", incident_id=999)
    assert len(memories_cleared) == 0


def test_agent_shared_memory_collaboration(db_session):
    # Setup test incident with an IOC inside logs/description
    incident = Incident(
        correlation_id="shared-mem-collab-correlation",
        source="AlertRouter",
        metric_type="UNAUTHORIZED_ACCESS",
        severity="HIGH",
        title="Unauthorized SA pod scanner access",
        description="Outbound scan detected targeting malicious node from external IP 185.220.101.5.",
        status="ANALYZING"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 1. Run RCA Agent -> stores diagnostic report in shared memory
    rca_res = run_root_cause_analysis(db_session, incident.id)
    assert rca_res is not None

    # Check shared memory has RCA diagnostics
    rca_mems = retrieve_memory("shared_memory", "rca_diagnostics", incident_id=incident.id)
    rca_mem = next((m for m in rca_mems if m["key"] == "rca_diagnostics"), None)
    assert rca_mem is not None
    assert rca_mem["agent_id"] == "rca_agent"

    # 2. Run Threat Intel Auto-Enrichment pipeline -> ThreatIntelAgent queries shared memory, enriches, and writes threat findings back to shared memory
    enrich_res = auto_enrich_incident_threats(db_session, incident.id)
    assert enrich_res is not None

    # Check shared memory has Threat Intel diagnostics
    ti_mems = retrieve_memory("shared_memory", "threat_intel", incident_id=incident.id)
    ti_mem = next((m for m in ti_mems if m["key"] == "threat_intel"), None)
    assert ti_mem is not None
    assert ti_mem["agent_id"] == "threat_intel_agent"
    
    ti_data = json.loads(ti_mem["value"])
    assert ti_data["overall_threat_level"] == "HIGH"

    # Seed Mastra workflow state to resume after detection state
    wf_state = MastraWorkflowState(
        workflow_name="incident_response",
        correlation_id=incident.correlation_id,
        current_state="RETRIEVE_CONTEXT",
        context_data_json=json.dumps({"incident_id": incident.id}),
        is_completed=False
    )
    db_session.add(wf_state)
    db_session.commit()

    # 3. Trigger SRE Reasoning Workflow E2E -> Retrieves both memory records and logs AGENT_MEMORY_SYNC to timeline
    run_incident_workflow(
        db=db_session,
        anomaly_type=incident.metric_type,
        description=incident.description,
        severity=incident.severity,
        node_name="node-01",
        pod_name="api-gateway",
        correlation_id=incident.correlation_id
    )

    # Verify timeline event for memory synchronization exists
    sync_event = db_session.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident.id,
        TimelineEvent.event_type == "AGENT_MEMORY_SYNC"
    ).first()
    assert sync_event is not None
    assert "Retrieved" in sync_event.title and "shared team memories" in sync_event.title

