import pytest
import json
from app.services.rca_service import (
    RootCauseAnalysisAgent,
    MetricCorrelationTool,
    LogAnalysisTool,
    DeploymentTool,
    HistoryTool,
    DependencyTool,
    run_root_cause_analysis
)
from app.models.models import Incident, TimelineEvent

def test_rca_diagnostic_tools(db_session):
    # Test MetricCorrelationTool
    metric_tool = MetricCorrelationTool()
    res_cpu = metric_tool.execute(db_session, "node-01", "CPU_SPIKE")
    assert "CPU" in res_cpu
    res_mem = metric_tool.execute(db_session, "node-01", "MEMORY_EXHAUSTION")
    assert "Memory" in res_mem
    res_disk = metric_tool.execute(db_session, "node-01", "DISK_FULL")
    assert "PV" in res_disk

    # Test LogAnalysisTool
    log_tool = LogAnalysisTool()
    res_log_oom = log_tool.execute(db_session, 1, "Got OOM error on system heap")
    assert "OOMKilled" in res_log_oom
    res_log_sec = log_tool.execute(db_session, 1, "unauthorized access failure")
    assert "SecOps" in res_log_sec

    # Test DeploymentTool
    deploy_tool = DeploymentTool()
    res_dep = deploy_tool.execute("ERROR_RATE_SPIKE")
    assert "payment-gateway" in res_dep

    # Test DependencyTool
    dep_tool = DependencyTool()
    res_topo = dep_tool.execute("HIGH_LATENCY")
    assert "api-gateway" in res_topo


def test_rca_agent_analysis(db_session):
    # Setup test incident
    incident = Incident(
        correlation_id="rca-agent-test-corr-id",
        source="Telemetry Monitor",
        metric_type="CPU_SPIKE",
        severity="WARNING",
        title="CPU_SPIKE on node-01",
        description="High CPU consumption detected.",
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    agent = RootCauseAnalysisAgent()
    rca_result = agent.analyze(db_session, incident)

    assert "primary_cause" in rca_result
    assert "primary_confidence" in rca_result
    assert rca_result["primary_confidence"] > 0
    assert "remediation_action" in rca_result
    assert len(rca_result["evidence"]) > 0


def test_run_root_cause_analysis_integration(db_session):
    incident = Incident(
        correlation_id="rca-integration-test-corr-id",
        source="Telemetry Monitor",
        metric_type="MEMORY_EXHAUSTION",
        severity="CRITICAL",
        title="OOM alert on memory-node",
        description="Memory consumption at 99%.",
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    rca_res = run_root_cause_analysis(db_session, incident.id)
    assert rca_res["primary_confidence"] == 90
    assert "heap space memory leak" in rca_res["primary_cause"]

    # Verify incident table update
    db_session.refresh(incident)
    assert incident.root_cause_json is not None
    loaded = json.loads(incident.root_cause_json)
    assert loaded["primary_confidence"] == 90

    # Verify Timeline event was created
    evt = db_session.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident.id,
        TimelineEvent.event_type == "RCA_ANALYSIS"
    ).first()
    assert evt is not None
    assert "Root Cause Analysis Diagnostic Report" in evt.decision_rationale
