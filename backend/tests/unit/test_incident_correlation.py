import pytest
from datetime import datetime, timezone, timedelta
from app.models.models import Incident
from app.services.incident_correlation_service import IncidentCorrelationService

def test_calculate_correlation_score(db_session):
    # Setup temporal similarity
    now = datetime.now(timezone.utc)
    
    inc1 = Incident(
        correlation_id="corr-p1",
        source="Telemetry",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="CPU Spike on payment-api",
        description="CPU at 95% on payment-api-pod-1",
        status="DETECTED",
        created_at=now
    )
    
    inc2 = Incident(
        correlation_id="corr-p2",
        source="Telemetry",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="CPU Spike on payment-api",
        description="CPU at 95% on payment-api-pod-2",
        status="DETECTED",
        created_at=now + timedelta(seconds=30)
    )
    
    score = IncidentCorrelationService.calculate_correlation_score(inc1, inc2)
    # Temporal: 35
    # Spatial: same metric type = 15, same keyword "payment" in both titles = 15
    # Total = 65
    assert score == 65.0

def test_correlate_incident_linking(db_session):
    now = datetime.now(timezone.utc)
    
    # Root incident (earlier, auth-service)
    root_inc = Incident(
        correlation_id="corr-root",
        source="Telemetry",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="auth-service CPU spike",
        description="Auth service failing requests",
        status="DETECTED",
        created_at=now - timedelta(seconds=30)
    )
    
    # Cascading incident (later, payment-api which depends on auth-service)
    cascading_inc = Incident(
        correlation_id="corr-casc",
        source="Telemetry",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="payment-api latency timeout",
        description="Payment api times out calling auth",
        status="DETECTED",
        created_at=now
    )
    
    db_session.add(root_inc)
    db_session.add(cascading_inc)
    db_session.commit()
    
    # Run correlation on the later incident
    root_id = IncidentCorrelationService.correlate_incident(db_session, cascading_inc.id)
    
    # Temporal: 35 (diff 30s)
    # Same metric type: 15
    # Causal (payment-api depends on auth-service): 30
    # Total score = 80 (>= 70 threshold)
    
    # Verify it linked to root_inc.id
    assert root_id == root_inc.id
    db_session.refresh(cascading_inc)
    assert cascading_inc.parent_incident_id == root_inc.id
