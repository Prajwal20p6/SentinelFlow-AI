"""
SentinelFlow AI — Phase 58: Playbook Execution Tracking Service
Tracks step-by-step progress, live status (Running/Complete/Pending/Failed),
and ETA estimation for playbook execution in the incident response flow.
Persists state in PostgreSQL via SQLAlchemy PlaybookExecution ORM model.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..core.observability import logger
from ..core.database import SessionLocal
from ..models.models import PlaybookExecution

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
    Persists execution records in PostgreSQL database.

    Integrates with the WebSocket broadcast so the frontend receives
    PlaybookProgress events every time a step changes.
    """

    @classmethod
    def _resolve_session(cls, db: Optional[Session]) -> tuple[Session, bool]:
        """Returns (session, should_close). If db is provided, do not close it."""
        if db is not None:
            return db, False
        return SessionLocal(), True

    # ── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def start_execution(
        cls,
        incident_id: int,
        playbook_name: str,
        steps: Optional[List[str]] = None,
        actor: str = "system",
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Start tracking a new playbook execution for an incident in PostgreSQL.
        Returns the execution record dictionary.
        """
        session, should_close = cls._resolve_session(db)
        try:
            execution_id = str(uuid.uuid4())
            step_list = steps or _DEFAULT_STEPS
            now_iso = datetime.now(timezone.utc).isoformat()

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

            if step_records:
                step_records[0]["status"] = "RUNNING"
                step_records[0]["started_at"] = now_iso

            execution_obj = PlaybookExecution(
                execution_id=execution_id,
                incident_id=incident_id,
                playbook_name=playbook_name,
                actor=actor,
                status="RUNNING",
                current_step=0,
                total_steps=len(step_list),
                progress_pct=0.0,
                steps_json=step_records,
                log_json=[f"[{now_iso}] Playbook '{playbook_name}' started by {actor}."],
                started_at=datetime.now(timezone.utc),
                completed_at=None,
                estimated_completion=cls._estimate_completion(0, len(step_list)),
            )

            session.add(execution_obj)
            session.commit()
            session.refresh(execution_obj)

            record = execution_obj.to_dict()
            logger.info(
                "playbook_execution_started",
                execution_id=execution_id,
                incident_id=incident_id,
                playbook_name=playbook_name,
                actor=actor,
            )
            cls._broadcast(record)
            return record
        finally:
            if should_close:
                session.close()

    @classmethod
    def advance_step(
        cls,
        execution_id: str,
        success: bool = True,
        log_message: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Complete the current step and advance to the next.
        If all steps are done, marks the execution as COMPLETE or FAILED.
        Returns the updated execution record, or None if not found.
        """
        session, should_close = cls._resolve_session(db)
        try:
            execution_obj = session.query(PlaybookExecution).filter(
                PlaybookExecution.execution_id == execution_id
            ).first()

            if not execution_obj:
                return None

            if execution_obj.status in ("COMPLETE", "FAILED"):
                return execution_obj.to_dict()

            current_idx = execution_obj.current_step
            steps = list(execution_obj.steps_json or [])
            logs = list(execution_obj.log_json or [])
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()

            steps[current_idx]["status"] = "COMPLETE" if success else "FAILED"
            steps[current_idx]["completed_at"] = now_iso

            if log_message:
                steps[current_idx]["log_lines"].append(f"[{now_iso}] {log_message}")

            logs.append(
                f"[{now_iso}] Step {current_idx + 1}/{execution_obj.total_steps} "
                f"'{steps[current_idx]['name']}': {'COMPLETE' if success else 'FAILED'}."
            )

            if not success:
                execution_obj.status = "FAILED"
                execution_obj.completed_at = now
                for remaining in steps[current_idx + 1:]:
                    remaining["status"] = "SKIPPED"
                execution_obj.steps_json = steps
                execution_obj.log_json = logs
                flag_modified(execution_obj, "steps_json")
                flag_modified(execution_obj, "log_json")
                session.commit()
                session.refresh(execution_obj)

                record = execution_obj.to_dict()
                logger.warning(
                    "playbook_execution_failed",
                    execution_id=execution_id,
                    failed_step=steps[current_idx]["name"],
                )
                cls._broadcast(record)
                return record

            next_idx = current_idx + 1
            if next_idx >= execution_obj.total_steps:
                execution_obj.status = "COMPLETE"
                execution_obj.completed_at = now
                execution_obj.progress_pct = 100.0
                execution_obj.current_step = execution_obj.total_steps
                execution_obj.estimated_completion = now_iso
                logs.append(
                    f"[{now_iso}] Playbook '{execution_obj.playbook_name}' completed successfully."
                )
                logger.info(
                    "playbook_execution_complete",
                    execution_id=execution_id,
                    incident_id=execution_obj.incident_id,
                )
            else:
                execution_obj.current_step = next_idx
                steps[next_idx]["status"] = "RUNNING"
                steps[next_idx]["started_at"] = now_iso
                execution_obj.progress_pct = round(next_idx / execution_obj.total_steps * 100, 1)
                execution_obj.estimated_completion = cls._estimate_completion(
                    next_idx, execution_obj.total_steps
                )
                logs.append(
                    f"[{now_iso}] Starting step {next_idx + 1}: '{steps[next_idx]['name']}'."
                )

            execution_obj.steps_json = steps
            execution_obj.log_json = logs
            flag_modified(execution_obj, "steps_json")
            flag_modified(execution_obj, "log_json")
            session.commit()
            session.refresh(execution_obj)

            record = execution_obj.to_dict()
            cls._broadcast(record)
            return record
        finally:
            if should_close:
                session.close()

    @classmethod
    def append_log(
        cls, execution_id: str, message: str, db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """Append a free-form log line to the current step and the execution log."""
        session, should_close = cls._resolve_session(db)
        try:
            execution_obj = session.query(PlaybookExecution).filter(
                PlaybookExecution.execution_id == execution_id
            ).first()

            if not execution_obj:
                return None

            now_iso = datetime.now(timezone.utc).isoformat()
            current_idx = execution_obj.current_step
            steps = list(execution_obj.steps_json or [])
            logs = list(execution_obj.log_json or [])

            if 0 <= current_idx < len(steps):
                steps[current_idx]["log_lines"].append(f"[{now_iso}] {message}")
            logs.append(f"[{now_iso}] {message}")

            execution_obj.steps_json = steps
            execution_obj.log_json = logs
            flag_modified(execution_obj, "steps_json")
            flag_modified(execution_obj, "log_json")
            session.commit()
            session.refresh(execution_obj)

            record = execution_obj.to_dict()
            cls._broadcast(record)
            return record
        finally:
            if should_close:
                session.close()

    @classmethod
    def get_execution(
        cls, execution_id: str, db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """Return a single execution by ID from database."""
        session, should_close = cls._resolve_session(db)
        try:
            execution_obj = session.query(PlaybookExecution).filter(
                PlaybookExecution.execution_id == execution_id
            ).first()
            return execution_obj.to_dict() if execution_obj else None
        finally:
            if should_close:
                session.close()

    @classmethod
    def get_executions_for_incident(
        cls, incident_id: int, db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """Return all executions associated with a specific incident from database."""
        session, should_close = cls._resolve_session(db)
        try:
            records = (
                session.query(PlaybookExecution)
                .filter(PlaybookExecution.incident_id == incident_id)
                .order_by(PlaybookExecution.started_at.desc())
                .all()
            )
            return [r.to_dict() for r in records]
        finally:
            if should_close:
                session.close()

    @classmethod
    def get_all_executions(
        cls, db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """Return all tracked executions (newest first) from database."""
        session, should_close = cls._resolve_session(db)
        try:
            records = (
                session.query(PlaybookExecution)
                .order_by(PlaybookExecution.started_at.desc())
                .all()
            )
            return [r.to_dict() for r in records]
        finally:
            if should_close:
                session.close()

    @classmethod
    def cancel_execution(
        cls, execution_id: str, db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """Cancel a running execution in database."""
        session, should_close = cls._resolve_session(db)
        try:
            execution_obj = session.query(PlaybookExecution).filter(
                PlaybookExecution.execution_id == execution_id
            ).first()

            if not execution_obj or execution_obj.status not in ("RUNNING", "PENDING"):
                return execution_obj.to_dict() if execution_obj else None

            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()
            steps = list(execution_obj.steps_json or [])
            logs = list(execution_obj.log_json or [])

            execution_obj.status = "FAILED"
            execution_obj.completed_at = now
            logs.append(f"[{now_iso}] Execution cancelled by operator.")

            for step in steps:
                if step["status"] in ("PENDING", "RUNNING"):
                    step["status"] = "SKIPPED"

            execution_obj.steps_json = steps
            execution_obj.log_json = logs
            flag_modified(execution_obj, "steps_json")
            flag_modified(execution_obj, "log_json")
            session.commit()
            session.refresh(execution_obj)

            record = execution_obj.to_dict()
            cls._broadcast(record)
            return record
        finally:
            if should_close:
                session.close()

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
