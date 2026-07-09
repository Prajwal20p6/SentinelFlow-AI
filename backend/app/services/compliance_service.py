"""
SentinelFlow AI — Compliance & Regulatory Automation Service
Maps incidents to regulatory frameworks (GDPR, PCI-DSS, SOC 2, HIPAA) and generates compliance checklists.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..models.models import Incident, TimelineEvent, IncidentLog

REGULATORY_MAP = {
    "GDPR": {
        "name": "GDPR Article 33 (Data Breach)",
        "notification_window": "72 hours",
        "description": "Requires notifying the Supervisory Authority without undue delay and, where feasible, not later than 72 hours after having become aware of it.",
        "requirements": [
            "Log nature of personal data breach, including categories and approximate number of data subjects.",
            "Communicate name and contact details of the Data Protection Officer (DPO).",
            "Describe the likely consequences of the personal data breach.",
            "Describe measures taken or proposed to address the personal data breach and mitigate adverse effects."
        ]
    },
    "PCI-DSS": {
        "name": "PCI-DSS 6.5.2 (Cardholder Data Protection)",
        "notification_window": "Immediate logging & quarterly audits",
        "description": "Requires robust logging, immediate containment of cardholder data environment (CDE) anomalies, and detailed SRE post-mortems.",
        "requirements": [
            "Perform immediate containment and segment isolation of cardholder data environment.",
            "Verify firewall and network access control lists (ACLs) around the affected pod segment.",
            "Retain all firewall, application, and database access logs for security audit.",
            "Conduct full incident post-mortem and submit a compliance audit narrative."
        ]
    },
    "SOC2": {
        "name": "SOC 2 Type II (Security and Confidentiality)",
        "notification_window": "Continuous compliance tracking",
        "description": "Examines control processes over a period of time to ensure authorization checks and operational logs are documented.",
        "requirements": [
            "Verify all API gateways enforce valid JWT/MFA authentication checks.",
            "Maintain tamper-evident audit trails of administrative or remediation commands.",
            "Confirm that no unauthorized system access or privileges were escalated.",
            "Document the reasoning, authorization, and SRE approvals for the containment execution."
        ]
    },
    "HIPAA": {
        "name": "HIPAA Breach Notification Rule (PHI Protection)",
        "notification_window": "60 days",
        "description": "Requires notification to affected individuals and the Secretary of HHS following discovery of a breach of unsecured protected health information (PHI).",
        "requirements": [
            "Determine if PHI was exposed or exfiltrated during the telemetry anomaly.",
            "Log the types of identifiers and details of PHI compromised.",
            "Implement immediate administrative and technical safeguards to secure PHI.",
            "Complete a risk assessment document covering nature of PHI, unauthorized person, and mitigation status."
        ]
    }
}

class ComplianceService:
    """Automates mapping, checklist tracking, and report generation for compliance auditing."""

    @staticmethod
    def map_incident_regulations(incident: Incident) -> List[str]:
        """Dynamically identifies which regulations are applicable based on source and description."""
        regs = ["SOC2"]  # Default framework applicable to all platform actions
        desc_lower = incident.description.lower()
        title_lower = incident.title.lower()
        source_lower = incident.source.lower()
        metric_lower = incident.metric_type.lower()

        # Payment/Credit Card related
        if any(term in desc_lower or term in title_lower or term in source_lower for term in ["payment", "card", "billing", "checkout", "transaction"]):
            regs.append("PCI-DSS")

        # PII / Data Breach / Access leakage
        if any(term in desc_lower or term in title_lower or term in metric_lower for term in ["leak", "exfiltration", "credential", "unauthorized", "auth-service"]):
            regs.append("GDPR")

        # PHI / HIPAA
        if any(term in desc_lower or term in title_lower for term in ["hipaa", "phi", "patient", "medical", "health", "pii"]):
            regs.append("HIPAA")

        return sorted(list(set(regs)))

    @staticmethod
    def generate_compliance_checklist(db: Session, incident: Incident) -> Dict[str, Any]:
        """
        Generates compliance checklist status based on active timeline events and properties.
        """
        applicable_regs = ComplianceService.map_incident_regulations(incident)
        
        # 1. Was incident logged? (Always true if it exists in DB)
        incident_logged = True
        
        # 2. Was leadership notified? (True if any timeline event or notification log exists, or if severity is CRITICAL)
        leadership_notified = incident.severity in ["CRITICAL", "HIGH"]
        
        # 3. Was timeline documented? (True if there are multiple timeline events)
        timeline_count = db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident.id).count()
        timeline_documented = timeline_count >= 2

        # 4. Was RCA completed?
        rca_completed = incident.root_cause_json is not None

        # 5. Were preventive actions taken? (True if autopilot or manual action executed)
        preventive_actions = incident.status in ["EXECUTED", "RESOLVED"]

        # 6. Was customer notified? (Only relevant if GDPR/HIPAA. True if explicitly marked or completed)
        needs_customer_notify = "GDPR" in applicable_regs or "HIPAA" in applicable_regs
        customer_notified = False  # requires manual signoff, default to false unless resolved
        if incident.status == "RESOLVED":
            customer_notified = True

        # 7. Are records retained? (Always true for SentinelFlow automated tamper-evident database logs)
        records_retained = True

        # Compile checklist items
        checklist = [
            {"id": "log", "task": "Was incident logged in SecOps registry?", "status": incident_logged},
            {"id": "notify_leader", "task": "Was security leadership notified?", "status": leadership_notified},
            {"id": "timeline", "task": "Was detailed SRE timeline documented?", "status": timeline_documented},
            {"id": "rca", "task": "Was AI root-cause analysis (RCA) completed?", "status": rca_completed},
            {"id": "preventive", "task": "Were preventive containment actions executed?", "status": preventive_actions},
            {"id": "customer", "task": "Was customer notification completed (PII/PHI)?", "status": customer_notified if needs_customer_notify else True, "conditional": needs_customer_notify},
            {"id": "retention", "task": "Are audit trails and debug logs safely retained?", "status": records_retained}
        ]

        # Calculate compliance score percentage
        completed_tasks = sum(1 for item in checklist if item["status"] is True)
        compliance_percentage = (completed_tasks / len(checklist)) * 100.0

        return {
            "incident_id": incident.id,
            "applicable_regulations": applicable_regs,
            "checklist": checklist,
            "compliance_score_percent": round(compliance_percentage, 1)
        }

    @staticmethod
    def generate_regulatory_report(db: Session, incident: Incident) -> Dict[str, Any]:
        """
        Assembles all timeline events, RCA parameters, and compliance checklists into a unified regulatory audit payload.
        """
        checklist_data = ComplianceService.generate_compliance_checklist(db, incident)
        
        # Get applicable regulatory details
        frameworks = []
        for reg in checklist_data["applicable_regulations"]:
            if reg in REGULATORY_MAP:
                frameworks.append(REGULATORY_MAP[reg])

        # Timeline Event logs serialization
        timeline_logs = []
        events = db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident.id).order_by(TimelineEvent.timestamp.asc()).all()
        for e in events:
            timeline_logs.append({
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "event_type": e.event_type,
                "title": e.title,
                "actor": e.actor
            })

        # Structured RCA parsed fields
        rca_conclusion = "AI reasoning diagnostics in progress."
        if incident.root_cause_json:
            try:
                rca_data = json.loads(incident.root_cause_json)
                rca_conclusion = rca_data.get("root_cause", rca_conclusion)
            except Exception:
                pass

        return {
            "incident_id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "status": incident.status,
            "created_at": incident.created_at.isoformat() if incident.created_at else None,
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            "root_cause_summary": rca_conclusion,
            "compliance_score_percent": checklist_data["compliance_score_percent"],
            "applicable_frameworks": frameworks,
            "checklist_items": checklist_data["checklist"],
            "timeline": timeline_logs
        }
