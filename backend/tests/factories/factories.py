"""
SentinelFlow AI — Test Factories
Factories for seeding User, Incident, and TimelineEvent mock entities.
"""

import random
from sqlalchemy.orm import Session
from app.models.models import User, Incident, TimelineEvent
from app.core.security import hash_password

def create_user_factory(db: Session, email: str = "test_user_factory@example.com", role: str = "engineer") -> User:
    """Create and persist a User entity."""
    user = User(
        email=email,
        hashed_password=hash_password("SecurePasswordFactory1!"),
        full_name="Factory Test User",
        role=role,
        is_active=True,
        mfa_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_incident_factory(db: Session, source: str = "FactoryMonitor", severity: str = "WARNING", status: str = "DETECTED") -> Incident:
    """Create and persist an Incident entity."""
    rand_val = random.randint(10000, 99999)
    incident = Incident(
        source=source,
        metric_type="CPU_SPIKE",
        severity=severity,
        title=f"Factory CPU Anomaly #{rand_val}",
        description="Dynamic mock description for testing.",
        status=status,
        confidence_score=0.88,
        correlation_id=f"factory-cid-{rand_val}"
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident
