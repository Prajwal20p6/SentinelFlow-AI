"""
SentinelFlow AI — WebSocket Broadcast Service
Helper methods for broadcasting incident, workflow, metrics, and timeline updates to clients.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..integrations.redis_pubsub import pubsub_manager
from ..websocket.events import (
    IncidentUpdateEvent,
    WorkflowStepEvent,
    ApprovalRequestEvent,
    TimelineEventEvent,
    MetricsUpdateEvent,
    AgentActivityEvent,
    WorkflowProgressEvent,
    LiveMetricsUpdateEvent,
    PlaybookProgressEvent,
)


def broadcast_incident_update(
    incident_id: int,
    status: str,
    severity: str,
    service: Optional[str] = None
) -> None:
    """Publish an IncidentUpdateEvent broadcast."""
    evt = IncidentUpdateEvent(
        incident_id=incident_id,
        status=status,
        severity=severity,
        service=service
    )
    pubsub_manager.publish("IncidentUpdate", evt.model_dump())


def broadcast_workflow_step(
    incident_id: int,
    step_name: str,
    status: str,
    duration_seconds: float
) -> None:
    """Publish a WorkflowStepEvent broadcast."""
    evt = WorkflowStepEvent(
        incident_id=incident_id,
        step_name=step_name,
        status=status,
        duration_seconds=duration_seconds
    )
    pubsub_manager.publish("WorkflowStep", evt.model_dump())


def broadcast_approval_request(
    approval_id: int,
    incident_id: int,
    decision_required_by: str
) -> None:
    """Publish an ApprovalRequestEvent broadcast."""
    evt = ApprovalRequestEvent(
        approval_id=approval_id,
        incident_id=incident_id,
        decision_required_by=decision_required_by
    )
    pubsub_manager.publish("ApprovalRequest", evt.model_dump())


def broadcast_timeline_event(
    incident_id: int,
    event_type: str,
    title: str
) -> None:
    """Publish a TimelineEventEvent broadcast."""
    evt = TimelineEventEvent(
        incident_id=incident_id,
        event_type=event_type,
        title=title
    )
    pubsub_manager.publish("TimelineEvent", evt.model_dump())


def broadcast_metrics_update(
    active_incidents: int,
    avg_resolution_time: float,
    resolution_rate: float
) -> None:
    """Publish a MetricsUpdateEvent broadcast."""
    evt = MetricsUpdateEvent(
        active_incidents=active_incidents,
        avg_resolution_time=avg_resolution_time,
        resolution_rate=resolution_rate
    )
    pubsub_manager.publish("MetricsUpdate", evt.model_dump())


_last_agent_broadcast: Dict[str, float] = {}

def broadcast_agent_activity(
    incident_id: int,
    agent_name: str,
    status: str,
    progress: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Publish an AgentActivityEvent broadcast with throttling (max 1 per second per agent)."""
    import time
    key = f"{incident_id}:{agent_name}"
    now = time.time()
    if key in _last_agent_broadcast and (now - _last_agent_broadcast[key]) < 1.0:
        return
    _last_agent_broadcast[key] = now

    evt = AgentActivityEvent(
        incident_id=incident_id,
        agent_name=agent_name,
        status=status,
        progress=progress,
        message=message,
        details=details or {}
    )
    pubsub_manager.publish("AgentActivity", evt.model_dump())


def broadcast_workflow_progress(
    incident_id: int,
    current_step: int,
    total_steps: int,
    step_name: str,
    step_status: str,
    estimated_completion: Optional[str] = None
) -> None:
    """Publish a WorkflowProgressEvent broadcast."""
    evt = WorkflowProgressEvent(
        incident_id=incident_id,
        current_step=current_step,
        total_steps=total_steps,
        step_name=step_name,
        step_status=step_status,
        estimated_completion=estimated_completion
    )
    pubsub_manager.publish("WorkflowProgress", evt.model_dump())


def broadcast_live_metrics_update(payload: Dict[str, Any]) -> None:
    """Publish a LiveMetricsUpdateEvent broadcast."""
    evt = LiveMetricsUpdateEvent(
        cluster_summary=payload.get("cluster_summary", {}),
        service_metrics=payload.get("service_metrics", []),
        time_series=payload.get("time_series", []),
        annotations=payload.get("annotations", []),
        history_size=payload.get("history_size", 0)
    )
    pubsub_manager.publish("LiveMetricsUpdate", evt.model_dump())


def broadcast_playbook_progress(record: Dict[str, Any]) -> None:
    """Publish a PlaybookProgressEvent broadcast."""
    evt = PlaybookProgressEvent(
        execution_id=record["execution_id"],
        incident_id=record["incident_id"],
        playbook_name=record["playbook_name"],
        status=record["status"],
        current_step=record["current_step"],
        total_steps=record["total_steps"],
        progress_pct=record["progress_pct"],
        estimated_completion=record["estimated_completion"],
        steps=record["steps"],
        log=record["log"]
    )
    pubsub_manager.publish("PlaybookProgress", evt.model_dump())

