"""
SentinelFlow AI — Phase 57 & 58: Unit Tests
Tests for MetricsDashboardService and PlaybookExecutionService.
"""
import pytest
from datetime import datetime, timezone


# ── Phase 57: MetricsDashboardService Tests ──────────────────────────────────

class TestMetricsDashboardService:
    """Tests for the real-time cluster metrics aggregation service."""

    def setup_method(self):
        """Reset module-level state between tests."""
        from app.services.metrics_dashboard_service import (
            MetricsDashboardService,
            _metric_series,
            _annotation_log,
        )
        _metric_series.clear()
        _annotation_log.clear()
        self.svc = MetricsDashboardService

    def test_capture_snapshot_returns_valid_structure(self):
        snapshot = self.svc.capture_snapshot()
        assert "timestamp" in snapshot
        assert "cluster_summary" in snapshot
        assert "service_metrics" in snapshot
        cs = snapshot["cluster_summary"]
        assert "avg_cpu" in cs
        assert "avg_memory" in cs
        assert "avg_latency_ms" in cs
        assert "avg_error_rate" in cs
        assert "health_score" in cs
        assert "degraded_services" in cs

    def test_capture_snapshot_appends_to_history(self):
        from app.services.metrics_dashboard_service import _metric_series
        assert len(_metric_series) == 0
        self.svc.capture_snapshot()
        assert len(_metric_series) == 1
        self.svc.capture_snapshot()
        assert len(_metric_series) == 2

    def test_capture_snapshot_respects_max_history(self):
        from app.services.metrics_dashboard_service import _metric_series, _MAX_HISTORY
        for _ in range(_MAX_HISTORY + 10):
            self.svc.capture_snapshot()
        assert len(_metric_series) <= _MAX_HISTORY

    def test_get_live_metrics_without_history_triggers_capture(self):
        from app.services.metrics_dashboard_service import _metric_series
        assert len(_metric_series) == 0
        result = self.svc.get_live_metrics()
        assert "cluster_summary" in result
        assert "service_metrics" in result
        assert "time_series" in result
        assert len(result["time_series"]) >= 1

    def test_get_live_metrics_contains_time_series_after_snapshots(self):
        self.svc.capture_snapshot()
        self.svc.capture_snapshot()
        result = self.svc.get_live_metrics()
        assert result["history_size"] == 2
        ts = result["time_series"]
        assert len(ts) == 2
        for point in ts:
            assert "cpu" in point
            assert "memory" in point
            assert "latency" in point
            assert "error_rate" in point

    def test_add_annotation_is_stored(self):
        from app.services.metrics_dashboard_service import _annotation_log
        self.svc.add_annotation(
            event_type="INCIDENT_DETECTED",
            label="CPU spike on node-01",
            severity="CRITICAL",
            incident_id=42,
        )
        assert len(_annotation_log) == 1
        ann = list(_annotation_log)[0]
        assert ann["event_type"] == "INCIDENT_DETECTED"
        assert ann["incident_id"] == 42
        assert ann["severity"] == "CRITICAL"

    def test_get_service_detail_without_history_returns_none(self):
        detail = self.svc.get_service_detail("api-gateway")
        assert detail is None

    def test_get_service_detail_with_snapshot(self):
        self.svc.capture_snapshot()
        # api-gateway is in the TRACKED_SERVICES list
        detail = self.svc.get_service_detail("api-gateway")
        assert detail is not None
        assert detail["name"] == "api-gateway"
        assert "cpu_usage" in detail
        assert "memory_usage" in detail

    def test_cluster_summary_health_score_in_range(self):
        for _ in range(5):
            snapshot = self.svc.capture_snapshot()
            score = snapshot["cluster_summary"]["health_score"]
            assert 0 <= score <= 100, f"Health score {score} out of range"

    def test_service_metrics_count_matches_tracked_services(self):
        from app.services.metrics_dashboard_service import _TRACKED_SERVICES
        snapshot = self.svc.capture_snapshot()
        assert len(snapshot["service_metrics"]) == len(_TRACKED_SERVICES)

    def test_service_metrics_have_required_fields(self):
        snapshot = self.svc.capture_snapshot()
        for svc in snapshot["service_metrics"]:
            assert "name" in svc
            assert "cpu_usage" in svc
            assert "memory_usage" in svc
            assert "latency_ms" in svc
            assert "error_rate" in svc
            assert "status" in svc
            assert svc["status"] in ("HEALTHY", "DEGRADED")

    def test_annotations_are_included_in_live_metrics(self):
        self.svc.capture_snapshot()
        self.svc.add_annotation("REMEDIATION_STARTED", "Restarting api-gateway", "INFO", 1)
        result = self.svc.get_live_metrics()
        assert len(result["annotations"]) >= 1


# ── Phase 58: PlaybookExecutionService Tests ─────────────────────────────────

class TestPlaybookExecutionService:
    """Tests for the step-by-step playbook execution tracking service backed by PostgreSQL/Database."""

    def setup_method(self):
        from app.services.playbook_execution_service import PlaybookExecutionService
        from app.core.database import SessionLocal
        from app.models.models import PlaybookExecution

        self.svc = PlaybookExecutionService
        self.db = SessionLocal()
        try:
            self.db.query(PlaybookExecution).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()

    def teardown_method(self):
        from app.models.models import PlaybookExecution
        try:
            self.db.query(PlaybookExecution).delete()
            self.db.commit()
        finally:
            self.db.close()

    def test_start_execution_returns_valid_record(self):
        record = self.svc.start_execution(
            incident_id=1,
            playbook_name="Test Playbook",
            actor="test-user",
            db=self.db,
        )
        assert record["execution_id"]
        assert record["incident_id"] == 1
        assert record["playbook_name"] == "Test Playbook"
        assert record["status"] == "RUNNING"
        assert record["current_step"] == 0
        assert record["total_steps"] > 0
        assert record["progress_pct"] == 0

    def test_start_execution_first_step_is_running(self):
        record = self.svc.start_execution(incident_id=1, playbook_name="Test", db=self.db)
        assert record["steps"][0]["status"] == "RUNNING"
        for step in record["steps"][1:]:
            assert step["status"] == "PENDING"

    def test_start_execution_with_custom_steps(self):
        custom_steps = ["Diagnose", "Patch", "Verify"]
        record = self.svc.start_execution(1, "Custom", steps=custom_steps, db=self.db)
        assert record["total_steps"] == 3
        assert record["steps"][0]["name"] == "Diagnose"

    def test_advance_step_progresses_to_next_step(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B", "C"], db=self.db)
        exec_id = record["execution_id"]
        updated = self.svc.advance_step(exec_id, success=True, db=self.db)
        assert updated["current_step"] == 1
        assert updated["steps"][0]["status"] == "COMPLETE"
        assert updated["steps"][1]["status"] == "RUNNING"

    def test_advance_step_tracks_progress_percentage(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B", "C", "D"], db=self.db)
        exec_id = record["execution_id"]
        self.svc.advance_step(exec_id, db=self.db)
        self.svc.advance_step(exec_id, db=self.db)
        updated = self.svc.advance_step(exec_id, db=self.db)
        assert updated["progress_pct"] == pytest.approx(75.0, abs=1.0)

    def test_advance_step_completes_execution(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B"], db=self.db)
        exec_id = record["execution_id"]
        self.svc.advance_step(exec_id, db=self.db)
        final = self.svc.advance_step(exec_id, db=self.db)
        assert final["status"] == "COMPLETE"
        assert final["progress_pct"] == 100
        assert final["completed_at"] is not None

    def test_advance_step_failure_aborts_execution(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B", "C"], db=self.db)
        exec_id = record["execution_id"]
        failed = self.svc.advance_step(exec_id, success=False, log_message="Network timeout", db=self.db)
        assert failed["status"] == "FAILED"
        assert failed["steps"][0]["status"] == "FAILED"
        for step in failed["steps"][1:]:
            assert step["status"] == "SKIPPED"

    def test_advance_step_on_completed_execution_is_noop(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A"], db=self.db)
        exec_id = record["execution_id"]
        completed = self.svc.advance_step(exec_id, db=self.db)
        assert completed["status"] == "COMPLETE"
        again = self.svc.advance_step(exec_id, db=self.db)
        assert again["status"] == "COMPLETE"

    def test_advance_step_returns_none_for_missing_id(self):
        result = self.svc.advance_step("non-existent-id", db=self.db)
        assert result is None

    def test_append_log_adds_line(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A"], db=self.db)
        exec_id = record["execution_id"]
        updated = self.svc.append_log(exec_id, "Starting health check...", db=self.db)
        assert any("Starting health check" in line for line in updated["log"])

    def test_get_execution_by_id(self):
        record = self.svc.start_execution(1, "Playbook", db=self.db)
        exec_id = record["execution_id"]
        retrieved = self.svc.get_execution(exec_id, db=self.db)
        assert retrieved is not None
        assert retrieved["execution_id"] == exec_id

    def test_get_executions_for_incident(self):
        self.svc.start_execution(99, "Playbook A", db=self.db)
        self.svc.start_execution(99, "Playbook B", db=self.db)
        self.svc.start_execution(100, "Other", db=self.db)
        results = self.svc.get_executions_for_incident(99, db=self.db)
        assert len(results) == 2
        for r in results:
            assert r["incident_id"] == 99

    def test_cancel_execution(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B", "C"], db=self.db)
        exec_id = record["execution_id"]
        cancelled = self.svc.cancel_execution(exec_id, db=self.db)
        assert cancelled["status"] == "FAILED"
        assert any("cancelled" in line.lower() for line in cancelled["log"])
        for step in cancelled["steps"]:
            assert step["status"] in ("SKIPPED", "RUNNING", "PENDING")

    def test_cancel_completed_execution_is_noop(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A"], db=self.db)
        exec_id = record["execution_id"]
        self.svc.advance_step(exec_id, db=self.db)
        already_done = self.svc.cancel_execution(exec_id, db=self.db)
        assert already_done["status"] == "COMPLETE"

    def test_get_all_executions_sorted_newest_first(self):
        r1 = self.svc.start_execution(1, "Alpha", db=self.db)
        r2 = self.svc.start_execution(2, "Beta", db=self.db)
        all_execs = self.svc.get_all_executions(db=self.db)
        assert len(all_execs) == 2
        assert all_execs[0]["started_at"] >= all_execs[1]["started_at"]

    def test_eta_estimate_decreases_as_steps_advance(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B", "C", "D"], db=self.db)
        exec_id = record["execution_id"]
        eta_before = record["estimated_completion"]
        updated = self.svc.advance_step(exec_id, db=self.db)
        eta_after = updated["estimated_completion"]
        assert eta_after <= eta_before or updated["status"] in ("COMPLETE", "FAILED")

    def test_log_message_attached_to_step_on_advance(self):
        record = self.svc.start_execution(1, "Playbook", steps=["A", "B"], db=self.db)
        exec_id = record["execution_id"]
        updated = self.svc.advance_step(exec_id, success=True, log_message="Health check passed", db=self.db)
        step_logs = updated["steps"][0]["log_lines"]
        assert any("Health check passed" in line for line in step_logs)

    def test_playbook_execution_persists_across_service_reinstantiation(self):
        """
        REGRESSION TEST: Simulates backend process restart.
        Verifies that playbook execution records saved by one DB session/service instance
        are fully queryable by a completely new DB session/service instance.
        """
        from app.core.database import SessionLocal

        # 1. Start execution in first DB session
        initial_record = self.svc.start_execution(
            incident_id=505,
            playbook_name="Restart Survival Playbook",
            steps=["Step 1", "Step 2", "Step 3"],
            actor="process-1",
            db=self.db,
        )
        exec_id = initial_record["execution_id"]
        self.svc.advance_step(exec_id, success=True, log_message="Step 1 completed", db=self.db)

        # 2. Close first DB session (simulating backend process termination)
        self.db.close()

        # 3. Open a brand new DB session (simulating new process startup)
        new_db = SessionLocal()
        try:
            # Query execution from brand new DB session
            persisted_record = self.svc.get_execution(exec_id, db=new_db)
            assert persisted_record is not None
            assert persisted_record["execution_id"] == exec_id
            assert persisted_record["incident_id"] == 505
            assert persisted_record["playbook_name"] == "Restart Survival Playbook"
            assert persisted_record["current_step"] == 1
            assert persisted_record["steps"][0]["status"] == "COMPLETE"
            assert persisted_record["steps"][1]["status"] == "RUNNING"
            assert any("Step 1 completed" in line for line in persisted_record["steps"][0]["log_lines"])

            # Further advance in the new session
            advanced = self.svc.advance_step(exec_id, success=True, log_message="Step 2 completed", db=new_db)
            assert advanced["current_step"] == 2
        finally:
            new_db.close()

