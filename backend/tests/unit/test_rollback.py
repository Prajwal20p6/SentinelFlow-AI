import pytest
import time
from app.models.models import Incident, IncidentLog
from app.services.rollback_tracker import RollbackTracker

def test_rollback_degradation_trigger(db_session):
    # 1. Create a simulated executing incident
    incident = Incident(
        correlation_id="corr-rb-1",
        source="telemetry-api",
        metric_type="KubernetesPodCrash",
        severity="CRITICAL",
        title="Pod crash simulation",
        description="Container crashed multiple times",
        status="EXECUTING",
        suggested_action="kubectl scale deployment/payment-api --replicas=3"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # Capture original baseline
    baseline = RollbackTracker.capture_baseline(incident)
    assert baseline["replicas"] == 1

    # Simulate degradation trigger flag on incident
    # We will trigger the monitor thread directly and verify it performs rollback
    # We manually set the flag on the object
    incident._simulate_rollback_trigger = True
    db_session.commit()

    # SessionWrapper to intercept close() calls during tests
    class SessionWrapper:
        def __init__(self, session):
            self.session = session
        def __getattr__(self, name):
            return getattr(self.session, name)
        def close(self):
            pass

    # Call monitor_and_verify synchronously for test assertion
    # Use session factory that returns our SessionWrapper
    def test_session_factory():
        return SessionWrapper(db_session)

    RollbackTracker.monitor_and_verify(incident.id, baseline, test_session_factory)

    # After verification finishes with simulated crash loop,
    # the status should transition to ESCALATED
    db_session.refresh(incident)
    assert incident.status == "ESCALATED"

    # Verify that a ROLLBACK_EXECUTED timeline event or log was created
    logs = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == incident.id,
        IncidentLog.stage == "ROLLBACK"
    ).all()
    assert len(logs) > 0
    assert "Automated rollback executed" in logs[0].message
    assert "replicas=1" in logs[0].message
