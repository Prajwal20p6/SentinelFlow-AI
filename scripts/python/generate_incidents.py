"""
SentinelFlow AI — Incident Generator Seeding Helper Script
Generates a set of realistic historical incidents in the database for demo modes.
"""

import os
import sys
import random
from datetime import datetime, timedelta, timezone

# Ensure backend directory is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, backend_path)

try:
    from app.core.database import SessionLocal
    from app.models.models import Incident, IncidentLog, TimelineEvent
except ImportError as e:
    print(f"[-] Import error: {e}")
    print("[-] Please run this script using the backend virtual environment python.")
    sys.exit(1)

ANOMALIES = [
    ("CPU_SPIKE", "High compute utilization detected on payment-gateway pod", "CRITICAL"),
    ("MEMORY_EXHAUSTION", "OOM conditions imminent on authentication service", "CRITICAL"),
    ("DISK_FULL", "Stale logs volume filling up database primary persistent volume", "WARNING"),
    ("HIGH_LATENCY", "CoreDNS delays causing downstream payment timeouts", "WARNING"),
    ("ERROR_RATE_SPIKE", "API gateway error rate spiked to 12.5%", "CRITICAL"),
]

def generate_historical_data(db):
    print("[*] Generating historical mock incidents...")
    now = datetime.now(timezone.utc)
    
    for i in range(1, 11):
        anomaly_type, base_desc, severity = random.choice(ANOMALIES)
        timestamp = now - timedelta(days=random.randint(1, 7), hours=random.randint(1, 23))
        
        status = random.choice(["EXECUTED", "BYPASSED", "REJECTED"])
        confidence = random.uniform(0.65, 0.95)
        
        incident = Incident(
            correlation_id=f"sf-trace-seed{i:03d}",
            source="Historical Ingest",
            metric_type=anomaly_type,
            severity=severity,
            title=f"{anomaly_type.replace('_', ' ').title()} on simulated-node-{i:02d}",
            description=f"{base_desc}. Historical simulation incident sample #{i}.",
            status=status,
            confidence_score=confidence,
            suggested_action="kubectl rollout restart deployment/mock-service",
            created_at=timestamp,
            updated_at=timestamp + timedelta(minutes=5)
        )
        db.add(incident)
        db.flush() # Populate incident.id
        
        # Add a timeline event
        timeline = TimelineEvent(
            incident_id=incident.id,
            event_type="DETECTION",
            title="Anomaly Identified",
            description=f"Automated diagnostic flag raised for {anomaly_type}",
            actor="heuristics-engine",
            timestamp=timestamp
        )
        db.add(timeline)
        
        # Add logs
        log1 = IncidentLog(
            incident_id=incident.id,
            stage="DETECTION",
            message=f"Created incident #{incident.id} from historical record.",
            timestamp=timestamp
        )
        log2 = IncidentLog(
            incident_id=incident.id,
            stage="EXECUTION",
            message=f"Remediation action completed. State set to {status}.",
            timestamp=timestamp + timedelta(minutes=5)
        )
        db.add(log1)
        db.add(log2)

    db.commit()
    print("[+] Seeding of 10 historical incidents completed.")

def main():
    print("="*60)
    print("      SENTINELFLOW AI - HISTORICAL INCIDENT DATA GENERATOR")
    print("="*60)
    
    db = SessionLocal()
    try:
        generate_historical_data(db)
    except Exception as e:
        print(f"[-] Data generation failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
