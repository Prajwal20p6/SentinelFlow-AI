"""
SentinelFlow AI — WebSocket Event Schemas
Type definitions and Pydantic models for structured real-time notifications.
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

def _get_utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentUpdateEvent(BaseModel):
    incident_id: int
    service: Optional[str] = None
    status: str
    severity: str
    timestamp: str = Field(default_factory=_get_utc_timestamp)


class WorkflowStepEvent(BaseModel):
    incident_id: int
    step_name: str
    status: str
    duration_seconds: float
    timestamp: str = Field(default_factory=_get_utc_timestamp)


class ApprovalRequestEvent(BaseModel):
    approval_id: int
    incident_id: int
    decision_required_by: str
    timestamp: str = Field(default_factory=_get_utc_timestamp)


class TimelineEventEvent(BaseModel):
    incident_id: int
    event_type: str
    title: str
    timestamp: str = Field(default_factory=_get_utc_timestamp)


class MetricsUpdateEvent(BaseModel):
    active_incidents: int
    avg_resolution_time: float
    resolution_rate: float
    timestamp: str = Field(default_factory=_get_utc_timestamp)


class AgentActivityEvent(BaseModel):
    incident_id: int
    agent_name: str
    status: str
    progress: int
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_get_utc_timestamp)


class WorkflowProgressEvent(BaseModel):
    incident_id: int
    current_step: int
    total_steps: int = 8
    step_name: str
    step_status: str
    estimated_completion: Optional[str] = None
    timestamp: str = Field(default_factory=_get_utc_timestamp)


# ── Phase 57: Live Cluster Metrics Dashboard Event ───────────────────────────

class LiveMetricsUpdateEvent(BaseModel):
    """
    Broadcast every 5 seconds to all connected clients with live cluster metrics.
    Contains cluster-wide summary, per-service breakdown, time-series history,
    and incident/remediation annotations.
    """
    timestamp: str = Field(default_factory=_get_utc_timestamp)
    cluster_summary: Dict[str, Any] = Field(default_factory=dict)
    service_metrics: list = Field(default_factory=list)
    time_series: list = Field(default_factory=list)
    annotations: list = Field(default_factory=list)
    history_size: int = 0


# ── Phase 58: Playbook Execution Progress Event ──────────────────────────────

class PlaybookProgressEvent(BaseModel):
    """
    Emitted whenever a playbook step advances, a log line is appended,
    or the execution reaches a terminal state (COMPLETE / FAILED).
    """
    execution_id: str
    incident_id: int
    playbook_name: str
    status: str                        # RUNNING / COMPLETE / FAILED
    current_step: int
    total_steps: int
    progress_pct: float
    estimated_completion: Optional[str] = None
    steps: list = Field(default_factory=list)
    log: list = Field(default_factory=list)
    timestamp: str = Field(default_factory=_get_utc_timestamp)
