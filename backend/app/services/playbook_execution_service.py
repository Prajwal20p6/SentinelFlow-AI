"""
SentinelFlow AI — Phase 58: Playbook Execution Tracking Service
Tracks step-by-step progress, live status (Running/Complete/Pending/Failed),
and ETA estimation for playbook execution in the incident response flow.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Literal, Optional

from ..core.observability import logger

# ── Execution Store (in-memory; keyed by execution_id) ──────────────────────
_executions: Dict[str, Dict[str, Any]] = {}

# ── Step status literals ─────────────────────────────────────────────────────
StepStatus = Literal["PENDING", "RUNNING", "COMPLETE", "FAILED", "SKIPPED"]

# ── Default playbook step templates ─────────────────────────────────────────
_DEFAULT_STEPS = [
    "Validate playbook prerequisites",
    "Identify affected pod / service",
    "Drain traffic from unhealthy node",
    "Execute primary remediation action",
    "Verify service health post-action",
    "Update incident status and timeline",
    "Notify on-call team via Slack",
    "Generate post-incident summary",
]


class PlaybookExecutionService:
    """
    Tracks real-time progress of playbook execution against an incident.
    Each execution has a unique UUID, a list of sequential steps, and
    progress metadata (current step, % done, ETA, log lines).

    Integrates with the WebSocket broadcast so the frontend receives
    PlaybookProgress events every time a step changes.
    """

    # ── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def start_execution(
        cls,
        incident_id: int,
        playbook_name: str,
        steps: Optional[List[str]] = None,
        actor: str = "system",
    ) -> Dict[str, Any]:
        """
        Start tracking a new playbook execution for an incident.
        Returns the execution record.
        """
        execution_id = str(uuid.uuid4())
        step_list = steps or _DEFAULT_STEPS

        step_records = [
            {
                "index": i,
                "name": s,
                "status": "PENDING",
                "started_at": None,
                "completed_at": None,
                "log_lines": [],
                "duration_sec": None,
            }
            for i, s in enumerate(step_list)
        ]

        # Mark first step as RUNNING immediately
        if step_records:
            step_records[0]["status"] = "RUNNING"
            step_records[0]["started_at"] = datetime.now(timezone.utc).isoformat()

        record: Dict[str, Any] = {
            "execution_id": execution_id,
            "incident_id": incident_id,
            "playbook_name": playbook_name,
            "actor": actor,
            "status": "RUNNING",
            "current_step": 0,
            "total_steps": len(step_list),
            "progress_pct": 0,
            "steps": step_records,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "estimated_completion": cls._estimate_completion(0, len(step_list)),
            "log": [f"[{datetime.now(timezone.utc).isoformat()}] Playbook '{playbook_name}' started by {actor}."],
        }

        _executions[execution_id] = record
        logger.info(
            "playbook_execution_started",
            execution_id=execution_id,
            incident_id=incident_id,
            playbook_name=playbook_name,
            actor=actor,
        )
        cls._broadcast(record)
        return record

    @classmethod
    def advance_step(
        cls,
        execution_id: str,
        success: bool = True,
        log_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Complete the current step and advance to the next.
        If all steps are done, marks the execution as COMPLETE or FAILED.
        Returns the updated execution record, or None if not found.
        """
        record = _executions.get(execution_id)
        if not record:
            return None

        if record["status"] in ("COMPLETE", "FAILED"):
            return record  # Already terminal

        current_idx = record["current_step"]
        steps = record["steps"]

        # Close the current step
        now = datetime.now(timezone.utc)
        steps[current_idx]["status"] = "COMPLETE" if success else "FAILED"
        steps[current_idx]["completed_at"] = now.isoformat()

        if log_message:
            steps[current_idx]["log_lines"].append(
                f"[{now.isoformat()}] {log_message}"
            )

        ts_str = now.isoformat()
        record["log"].append(
            f"[{ts_str}] Step {current_idx + 1}/{record['total_steps']} "
            f"'{steps[current_idx]['name']}': {'COMPLETE' if success else 'FAILED'}."
        )

        if not success:
            # Abort the execution
            record["status"] = "FAILED"
            record["completed_at"] = now.isoformat()
            for remaining in steps[current_idx + 1:]:
                remaining["status"] = "SKIPPED"
            logger.warning(
                "playbook_execution_failed",
                execution_id=execution_id,
                failed_step=steps[current_idx]["name"],
            )
            cls._broadcast(record)
            return record

        # Advance to next step
        next_idx = current_idx + 1
        if next_idx >= record["total_steps"]:
            # All steps complete
            record["status"] = "COMPLETE"
            record["completed_at"] = now.isoformat()
            record["progress_pct"] = 100
            record["current_step"] = record["total_steps"]
            record["estimated_completion"] = now.isoformat()
            record["log"].append(
                f"[{now.isoformat()}] Playbook '{record['playbook_name']}' completed successfully."
            )
            logger.info(
                "playbook_execution_complete",
                execution_id=execution_id,
                incident_id=record["incident_id"],
            )
        else:
            record["current_step"] = next_idx
            steps[next_idx]["status"] = "RUNNING"
            steps[next_idx]["started_at"] = now.isoformat()
            record["progress_pct"] = round(next_idx / record["total_steps"] * 100, 1)
            record["estimated_completion"] = cls._estimate_completion(
                next_idx, record["total_steps"]
            )
            record["log"].append(
                f"[{now.isoformat()}] Starting step {next_idx + 1}: '{steps[next_idx]['name']}'."
            )

        cls._broadcast(record)
        return record

    @classmethod
    def append_log(
        cls, execution_id: str, message: str
    ) -> Optional[Dict[str, Any]]:
        """Append a free-form log line to the current step and the execution log."""
        record = _executions.get(execution_id)
        if not record:
            return None
        ts = datetime.now(timezone.utc).isoformat()
        current_idx = record["current_step"]
        steps = record["steps"]
        if 0 <= current_idx < len(steps):
            steps[current_idx]["log_lines"].append(f"[{ts}] {message}")
        record["log"].append(f"[{ts}] {message}")
        cls._broadcast(record)
        return record

    @classmethod
    def get_execution(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """Return a single execution by ID."""
        return _executions.get(execution_id)

    @classmethod
    def get_executions_for_incident(cls, incident_id: int) -> List[Dict[str, Any]]:
        """Return all executions associated with a specific incident."""
        return [
            e for e in _executions.values() if e["incident_id"] == incident_id
        ]

    @classmethod
    def get_all_executions(cls) -> List[Dict[str, Any]]:
        """Return all tracked executions (newest first)."""
        return sorted(
            _executions.values(),
            key=lambda e: e["started_at"],
            reverse=True,
        )

    @classmethod
    def cancel_execution(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """Cancel a running execution."""
        record = _executions.get(execution_id)
        if not record or record["status"] not in ("RUNNING", "PENDING"):
            return record
        now = datetime.now(timezone.utc).isoformat()
        record["status"] = "FAILED"
        record["completed_at"] = now
        record["log"].append(f"[{now}] Execution cancelled by operator.")
        # Mark remaining steps as SKIPPED
        for step in record["steps"]:
            if step["status"] in ("PENDING", "RUNNING"):
                step["status"] = "SKIPPED"
        cls._broadcast(record)
        return record

    # ── Private Helpers ──────────────────────────────────────────────────────

    @classmethod
    def _estimate_completion(cls, current_step: int, total_steps: int) -> str:
        """Estimate UTC completion timestamp assuming ~15s per remaining step."""
        seconds_remaining = (total_steps - current_step) * 15
        eta = datetime.now(timezone.utc) + timedelta(seconds=seconds_remaining)
        return eta.isoformat()

    @classmethod
    def _broadcast(cls, record: Dict[str, Any]) -> None:
        try:
            from .websocket_service import broadcast_playbook_progress
            broadcast_playbook_progress(record)
        except Exception as ws_err:
            logger.warning("playbook_broadcast_failed", error=str(ws_err))

