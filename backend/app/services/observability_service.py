"""
SentinelFlow AI — Observability Service
OpenTelemetry tracing, Prometheus metrics, and structured logging.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.models import AIObservabilityTrace


def get_observability_summary(db: Session) -> dict:
    """Get aggregated observability metrics."""
    total = db.query(func.count(AIObservabilityTrace.id)).scalar() or 0
    avg_latency = db.query(func.avg(AIObservabilityTrace.latency_ms)).scalar() or 0.0
    total_input = db.query(func.sum(AIObservabilityTrace.input_tokens)).scalar() or 0
    total_output = db.query(func.sum(AIObservabilityTrace.output_tokens)).scalar() or 0
    error_count = (
        db.query(func.count(AIObservabilityTrace.id))
        .filter(AIObservabilityTrace.status == "error")
        .scalar() or 0
    )

    # Traces by step
    step_counts = (
        db.query(AIObservabilityTrace.step_name, func.count(AIObservabilityTrace.id))
        .group_by(AIObservabilityTrace.step_name)
        .all()
    )

    return {
        "total_traces": total,
        "avg_latency_ms": round(float(avg_latency), 2),
        "total_input_tokens": int(total_input),
        "total_output_tokens": int(total_output),
        "error_count": error_count,
        "traces_by_step": {name: count for name, count in step_counts},
    }


def get_recent_traces(db: Session, limit: int = 50, correlation_id: str = None) -> list:
    """Get recent observability traces."""
    query = db.query(AIObservabilityTrace)
    if correlation_id:
        query = query.filter(AIObservabilityTrace.correlation_id == correlation_id)
    return query.order_by(AIObservabilityTrace.timestamp.desc()).limit(limit).all()
