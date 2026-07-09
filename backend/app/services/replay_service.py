"""
SentinelFlow AI — Incident Replay Engine
Records and streams step-by-step incident resolution history.
"""

from typing import List, Dict, Any
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from ..models.models import ReplayEvent, Incident

class IncidentReplayEngine:
    """Orchestrates chronological replay streams for review auditing and hackathon demonstrations."""

    @staticmethod
    def get_replay_stream(db: Session, incident_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all ReplayEvent logs for an incident.
        If empty, initializes default demonstration events to make it immediately replayable.
        """
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return []

        events = db.query(ReplayEvent).filter(
            ReplayEvent.incident_id == incident_id
        ).order_by(ReplayEvent.event_timestamp.asc()).all()

        if not events:
            # Seed default demonstration events for this incident
            seeding = IncidentReplayEngine.create_default_replay_events(incident)
            for s in seeding:
                db_event = ReplayEvent(
                    incident_id=incident_id,
                    event_timestamp=s["event_timestamp"],
                    event_type=s["event_type"],
                    event_data=json.dumps(s["event_data"]),
                    agent_name=s["agent_name"],
                    decision=s["decision"],
                    reasoning=s["reasoning"]
                )
                db.add(db_event)
            db.commit()
            
            # Fetch again
            events = db.query(ReplayEvent).filter(
                ReplayEvent.incident_id == incident_id
            ).order_by(ReplayEvent.event_timestamp.asc()).all()

        return [
            {
                "id": e.id,
                "timestamp": e.event_timestamp.isoformat(),
                "event_type": e.event_type,
                "event_data": json.loads(e.event_data) if e.event_data else {},
                "agent_name": e.agent_name,
                "decision": e.decision,
                "reasoning": e.reasoning
            }
            for e in events
        ]

    @staticmethod
    def create_default_replay_events(incident: Incident) -> List[Dict[str, Any]]:
        """
        Builds default chronological events matching Phase 38 specifications.
        """
        now = incident.created_at or datetime.now()
        
        events = [
            {
                "event_timestamp": now,
                "event_type": "ALERT_RECEIVED",
                "event_data": {
                    "metric_type": incident.metric_type,
                    "source": incident.source,
                    "value": "92.4% utilization threshold trigger"
                },
                "agent_name": "system",
                "decision": "Alert Ingested",
                "reasoning": f"Telemetry listener captured metric warning: {incident.metric_type} on pod service."
            },
            {
                "event_timestamp": now + timedelta(seconds=5),
                "event_type": "INCIDENT_CREATED",
                "event_data": {
                    "incident_id": incident.id,
                    "title": incident.title,
                    "severity": incident.severity
                },
                "agent_name": "system",
                "decision": "Incident Declared",
                "reasoning": f"Correlated metric warning into active Incident #{incident.id}."
            },
            {
                "event_timestamp": now + timedelta(seconds=10),
                "event_type": "WORKFLOW_STARTED",
                "event_data": {
                    "workflow_id": f"wf-{incident.correlation_id}",
                    "stages": ["DETECTION", "RCA", "THREAT_INTEL", "REMEDIATION", "HITL_GATE", "EXECUTION"]
                },
                "agent_name": "MastraOrchestrator",
                "decision": "Workflow Triggered",
                "reasoning": "Started Mastra state machine to run investigation and safe rollback checks."
            },
            {
                "event_timestamp": now + timedelta(seconds=15),
                "event_type": "RCA_ANALYSIS",
                "event_data": {
                    "primary_cause": "OOM memory heap leak" if incident.metric_type == "MEMORY_EXHAUSTION" else "CPU processing spike",
                    "confidence": 92.0
                },
                "agent_name": "RootCauseAnalysisAgent",
                "decision": "Root cause identified",
                "reasoning": f"Identified primary cause: {incident.metric_type} pattern matched recent deploy changes."
            },
            {
                "event_timestamp": now + timedelta(seconds=30),
                "event_type": "THREAT_ENRICHMENT",
                "event_data": {
                    "overall_threat": "CLEAN",
                    "findings": []
                },
                "agent_name": "ThreatIntelAgent",
                "decision": "Threat Assessment Completed",
                "reasoning": "Scanned container network addresses against VirusTotal. All reputations are normal."
            },
            {
                "event_timestamp": now + timedelta(seconds=45),
                "event_type": "REMEDIATION_RANKED",
                "event_data": {
                    "recommended_action": incident.suggested_action or f"Restart pod {incident.source}",
                    "confidence": 85.0
                },
                "agent_name": "RemediationAgent",
                "decision": "Remediation plan generated",
                "reasoning": f"Recommended action ranked as highest safety score: {incident.suggested_action}."
            },
            {
                "event_timestamp": now + timedelta(seconds=60),
                "event_type": "APPROVAL_REQUESTED",
                "event_data": {
                    "channel": "Slack: #alerts-sentinelflow",
                    "status": "PENDING"
                },
                "agent_name": "system",
                "decision": "HITL Sign-off Requested",
                "reasoning": "Safety policy requires human approval for command modifications on cluster namespaces."
            },
            {
                "event_timestamp": now + timedelta(seconds=75),
                "event_type": "APPROVAL_GRANTED",
                "event_data": {
                    "actor": "admin@sentinelflow.ai",
                    "status": "APPROVED"
                },
                "agent_name": "system",
                "decision": "Remediation Approved",
                "reasoning": "Operator authorized execution of recommended autopilot repairs."
            },
            {
                "event_timestamp": now + timedelta(seconds=90),
                "event_type": "REMEDIATION_EXECUTING",
                "event_data": {
                    "command": incident.suggested_action or "kubectl rollout restart ...",
                    "target": incident.source
                },
                "agent_name": "system",
                "decision": "Executing Containment",
                "reasoning": "Passing command parameters through Enkrypt AI safety guardrails and running on API server."
            },
            {
                "event_timestamp": now + timedelta(seconds=120),
                "event_type": "INCIDENT_RESOLVED",
                "event_data": {
                    "status": "RESOLVED",
                    "duration_sec": 120
                },
                "agent_name": "system",
                "decision": "Incident Closed",
                "reasoning": "Telemetry metrics returned to baseline targets. Service declared healthy."
            },
            {
                "event_timestamp": now + timedelta(seconds=150),
                "event_type": "POSTMORTEM_GENERATED",
                "event_data": {
                    "compliance_violations": 0,
                    "estimated_downtime_mins": 1
                },
                "agent_name": "system",
                "decision": "Audit Sealed",
                "reasoning": "Generated executive and technical summaries. Sealed hash chain in blockchain ledger."
            }
        ]
        return events
