import pytest
import json
from app.models.models import Incident, Policy, ExecutionConfig
from app.services.policy_engine import PolicyEngine

def test_policy_engine_evaluation(db_session):
    # Seed policies
    PolicyEngine.seed_default_policies(db_session)
    
    # Verify 4 policies were seeded
    policies = db_session.query(Policy).all()
    assert len(policies) >= 4

    # Seed ExecutionConfig if missing
    config = db_session.query(ExecutionConfig).first()
    if not config:
        config = ExecutionConfig(
            id=1,
            mode="MANUAL",
            rate_limit_per_minute=5,
            min_confidence_score=90,
            max_blast_radius=10,
            restricted_services="payment",
            low_risk_actions="restart_pod,scale_service,rollout_restart"
        )
        db_session.add(config)
        db_session.commit()

    # 1. Test MANUAL mode override
    config.mode = "MANUAL"
    db_session.commit()

    incident = Incident(
        correlation_id="corr-pe-1",
        source="telemetry",
        metric_type="KubernetesPodCrash",
        severity="CRITICAL",
        title="Pod Crash on test-service",
        description="Container crashed multiple times",
        confidence_score=0.95,
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    allowed, reason, actions = PolicyEngine.evaluate_incident(db_session, incident)
    assert allowed is False
    assert "MANUAL mode" in reason

    # 2. Test POLICY_BASED mode with crash policy matching
    config.mode = "POLICY_BASED"
    db_session.commit()

    allowed, reason, actions = PolicyEngine.evaluate_incident(db_session, incident)
    assert allowed is True
    assert "Auto-restart crashed pods" in reason
    assert "restart_pod" in actions

    # 3. Test exception matching: payment-api should bypass autopilot execution
    payment_incident = Incident(
        correlation_id="corr-pe-2",
        source="payment-api",
        metric_type="KubernetesPodCrash",
        severity="CRITICAL",
        title="Pod Crash on payment-api",
        description="Container crashed multiple times",
        confidence_score=0.95,
        status="DETECTED"
    )
    db_session.add(payment_incident)
    db_session.commit()
    db_session.refresh(payment_incident)

    allowed_pay, reason_pay, actions_pay = PolicyEngine.evaluate_incident(db_session, payment_incident)
    assert allowed_pay is False
    assert "Always require approval for payment systems" in reason_pay
