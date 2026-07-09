import pytest
from app.services.alert_fingerprinting_service import AlertFingerprintingService
from app.models.models import AlertFingerprint, Alert, Incident

def test_alert_fingerprinting_and_dedup(db_session):
    source = "Prometheus-Alert"
    alert_type = "CPU_SPIKE"
    service = "payment-api"
    msg1 = "CPU > 80% on payment-api pod-1"
    
    inc_id, is_new, fp1 = AlertFingerprintingService.process_incoming_alert(
        db=db_session,
        source=source,
        alert_type=alert_type,
        service=service,
        message=msg1
    )
    
    assert inc_id is None
    assert is_new is True
    assert fp1.alert_count == 1
    
    # Create mock incident and link
    incident = Incident(
        correlation_id="corr-1",
        source=source,
        metric_type=alert_type,
        severity="CRITICAL",
        title="CPU Spike on payment-api",
        description=msg1,
        status="DETECTED",
        alert_count=1
    )
    db_session.add(incident)
    db_session.commit()
    
    fp1.incident_id = incident.id
    db_session.commit()
    
    # Process identical alert -> should deduplicate
    inc_id_dup, is_new_dup, fp2 = AlertFingerprintingService.process_incoming_alert(
        db=db_session,
        source=source,
        alert_type=alert_type,
        service=service,
        message=msg1
    )
    
    assert inc_id_dup == incident.id
    assert is_new_dup is False
    assert fp2.alert_count == 2
    
    # Process similar alert -> should group by similarity (>85% matching)
    msg2 = "CPU > 80% on payment-api pod-2"
    inc_id_sim, is_new_sim, fp3 = AlertFingerprintingService.process_incoming_alert(
        db=db_session,
        source=source,
        alert_type=alert_type,
        service=service,
        message=msg2
    )
    
    assert inc_id_sim == incident.id
    assert is_new_sim is False
    assert fp3.id == fp1.id
    assert fp3.alert_count == 3
