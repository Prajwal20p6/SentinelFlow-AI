"""
SentinelFlow AI — Performance Tests
Asserts response times and query execution latencies stay within SLA bounds.
"""

import pytest
import time
from app.models.models import Incident
from tests.factories.factories import create_incident_factory


def test_database_query_speed_limits(db_session):
    """Ensure database query latency falls within SLA (< 100ms)."""
    # Seed 20 test incidents
    for _ in range(20):
        create_incident_factory(db_session)

    start_time = time.perf_counter()
    incidents = db_session.query(Incident).all()
    duration_ms = (time.perf_counter() - start_time) * 1000

    assert len(incidents) >= 20
    assert duration_ms < 100.0  # Must complete in under 100ms
