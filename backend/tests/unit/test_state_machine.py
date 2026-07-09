import pytest
from app.services.state_machine_service import StateMachineService
from app.models.models import Incident

def test_state_machine_transitions(db_session):
    # 1. Create a fresh incident
    incident = Incident(
        correlation_id="corr-sm-1",
        source="telemetry",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="CPU Spike on payment-api",
        description="High CPU usage",
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 2. DETECTED -> ANALYZING: should pass
    StateMachineService.transition_status(db_session, incident.id, "ANALYZING", actor="test-runner")
    assert incident.status == "ANALYZING"

    # 3. ANALYZING -> PLANNED without RCA: should raise validation error
    with pytest.raises(ValueError) as exc:
        StateMachineService.transition_status(db_session, incident.id, "PLANNED", actor="test-runner")
    assert "Root Cause Analysis (RCA) must be complete" in str(exc.value)

    # Complete RCA and set root cause json
    incident.root_cause_json = '{"root_cause": "Database pool exhausted"}'
    db_session.commit()

    # ANALYZING -> PLANNED should now succeed
    StateMachineService.transition_status(db_session, incident.id, "PLANNED", actor="test-runner")
    assert incident.status == "PLANNED"

    # 4. PLANNED -> PENDING_APPROVAL without suggested remediation: should raise validation error
    with pytest.raises(ValueError) as exc:
        StateMachineService.transition_status(db_session, incident.id, "PENDING_APPROVAL", actor="test-runner")
    assert "suggested remediation command must be defined" in str(exc.value)

    # Set suggested action
    incident.suggested_action = "kubectl scale deployment/payment-api --replicas=3"
    db_session.commit()

    # PLANNED -> PENDING_APPROVAL should now succeed
    StateMachineService.transition_status(db_session, incident.id, "PENDING_APPROVAL", actor="test-runner")
    assert incident.status == "PENDING_APPROVAL"

    # 5. PENDING_APPROVAL -> APPROVED: should succeed
    StateMachineService.transition_status(db_session, incident.id, "APPROVED", actor="test-runner")
    assert incident.status == "APPROVED"

    # 6. Invalid transition: APPROVED -> RESOLVED directly: should fail
    with pytest.raises(ValueError):
        StateMachineService.transition_status(db_session, incident.id, "RESOLVED", actor="test-runner")

    # 7. Escalation path: APPROVED -> ESCALATED: should succeed
    StateMachineService.transition_status(db_session, incident.id, "ESCALATED", actor="test-runner")
    assert incident.status == "ESCALATED"
