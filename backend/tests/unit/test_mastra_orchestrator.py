import pytest
from app.services.workflow_service import run_incident_workflow
from app.models.models import MastraWorkflowState, MastraWorkflowStep, Incident

def test_workflow_state_persistence_and_resumption(client, db_session):
    correlation_id = "mastra-test-durable-999"
    
    # 1. Run workflow first time (Detection to Approve Decision)
    incident = run_incident_workflow(
        db=db_session,
        anomaly_type="CPU_SPIKE",
        description="High CPU load test spike description",
        correlation_id=correlation_id
    )
    
    # Verify state row created
    state = db_session.query(MastraWorkflowState).filter(
        MastraWorkflowState.correlation_id == correlation_id
    ).first()
    assert state is not None
    assert state.current_state in ("EXECUTE_REMEDIATION", "RESOLVE")
    
    # Verify steps created
    steps = db_session.query(MastraWorkflowStep).filter(
        MastraWorkflowStep.workflow_state_id == state.id
    ).all()
    assert len(steps) >= 7
    
    # 2. Run workflow a second time with same correlation_id (verifies resumption)
    incident_two = run_incident_workflow(
        db=db_session,
        anomaly_type="CPU_SPIKE",
        description="High CPU load test spike description",
        correlation_id=correlation_id
    )
    assert incident_two.id == incident.id

def test_autopilot_execution(client, db_session):
    correlation_id = "mastra-test-autopilot-oom"
    
    from app.services.execution_mode_service import ExecutionModeService
    ExecutionModeService.update_config(
        db=db_session,
        mode="FULLY_AUTONOMOUS",
        rate_limit_per_minute=5,
        min_confidence_score=50,
        max_blast_radius=10,
        restricted_services="restricted",
        low_risk_actions="restart_pod"
    )

    # MEMORY_EXHAUSTION triggers confidence > 80%, allowing auto-pilot bypass
    incident = run_incident_workflow(
        db=db_session,
        anomaly_type="MEMORY_EXHAUSTION",
        description="Memory exhaustion test description",
        correlation_id=correlation_id
    )
    
    assert incident.status in ("EXECUTED", "BYPASSED")
    
    # Verify execution step completed
    state = db_session.query(MastraWorkflowState).filter(
        MastraWorkflowState.correlation_id == correlation_id
    ).first()
    assert state.is_completed is True
