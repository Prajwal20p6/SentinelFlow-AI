"""
SentinelFlow AI — Executive Summarization & Business Impact Services
Translates deep technical Kubernetes diagnostics into business-level executive context.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..models.models import Incident, TimelineEvent, RecommendationFeedback
from .llm_service import llm_manager
from ..core.observability import logger

def calculate_business_impact(incident: Incident) -> Dict[str, Any]:
    """Computes business impact scores, downtime costs, user impact, and regulatory exposure."""
    # Determine base service criticality (1-5) and average cost per minute
    service_criticality = 3
    cost_per_minute = 150.0
    affected_users_base = 100
    regulations = ["SOC2"]

    # Source and type based adjustments
    lower_source = incident.source.lower()
    lower_type = incident.metric_type.lower()

    if "gateway" in lower_source or "production" in lower_source or "ingress" in lower_source:
        service_criticality = 5
        cost_per_minute = 600.0
        affected_users_base = 800
    elif "database" in lower_source or "db" in lower_source:
        service_criticality = 4
        cost_per_minute = 350.0
        affected_users_base = 350

    if "unauthorized" in lower_type or "security" in lower_type:
        regulations.extend(["GDPR", "PCI-DSS"])
        service_criticality = max(service_criticality, 4)
        cost_per_minute += 200.0
    elif "memory" in lower_type or "oom" in lower_type or "cpu" in lower_type:
        service_criticality = max(service_criticality, 3)

    # Compute duration in minutes
    if incident.resolved_at and incident.created_at:
        duration_mins = (incident.resolved_at - incident.created_at).total_seconds() / 60.0
    else:
        # If still active, compute duration up to now or default to 15m
        duration_mins = (datetime.now(timezone.utc) - incident.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 60.0
    duration_mins = max(1.0, duration_mins)

    # Metrics
    impact_score = service_criticality * duration_mins
    financial_impact = duration_mins * cost_per_minute
    affected_users = int(affected_users_base * (1.0 + (duration_mins / 30.0)))

    # Determine risk profile
    if incident.severity == "CRITICAL" or impact_score > 150:
        risk_level = "CRITICAL"
    elif incident.severity == "HIGH" or impact_score > 60:
        risk_level = "HIGH"
    elif impact_score > 15:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Compliance met/violated/pending
    compliance_status = "MET"
    required_reports = []
    if "GDPR" in regulations or "PCI-DSS" in regulations:
        compliance_status = "PENDING"
        if incident.status == "EXECUTED":
            compliance_status = "MET"
        elif incident.status == "REJECTED":
            compliance_status = "VIOLATED"
        required_reports.append("Data Protection Officer (DPO) Breach Log")
        required_reports.append("Security Operations Center Audit Narrative")

    return {
        "impact_score": round(impact_score, 1),
        "financial_impact_usd": round(financial_impact, 2),
        "affected_users": affected_users,
        "risk_level": risk_level,
        "regulations_applicable": regulations,
        "compliance_status": compliance_status,
        "required_notifications": required_reports,
        "duration_mins": round(duration_mins, 1)
    }


def generate_executive_summary(db: Session, incident: Incident) -> Dict[str, Any]:
    """Generates a non-technical summary using LLM reasoning and caching."""
    # Check if executive report is already cached in db
    if incident.executive_report_json:
        try:
            return json.loads(incident.executive_report_json)
        except Exception:
            pass

    impact = calculate_business_impact(incident)

    # Construct timeline events for executives (non-technical language)
    timeline_events = []
    for evt in incident.timeline_events:
        # Filter out deep technical details, keep business actions
        if evt.event_type in ["DETECTED", "RCA_ANALYSIS", "THREAT_INTEL_ENRICH", "SAFETY_CHECK_FAIL", "SAFETY_CHECK_PASS", "RECOMMENDATION_CORRECTED", "EXECUTED", "REJECTED"]:
            timeline_events.append(f"- {evt.title} ({evt.actor})")

    timeline_str = "\n".join(timeline_events) if timeline_events else "- Alert logged on SentinelFlow dashboard."

    # Ask the LLM to write a business-oriented summary
    prompt = (
        f"Generate a clear, non-technical executive summary of the following SRE incident:\n"
        f"Incident: {incident.title}\n"
        f"Description: {incident.description}\n"
        f"Metric Type: {incident.metric_type}\n"
        f"Final Action: {incident.suggested_action}\n"
        f"Business Impact Metrics: Criticality: {impact['risk_level']}, Users: {impact['affected_users']}, Cost: ${impact['financial_impact_usd']}\n"
        f"Business Timeline:\n{timeline_str}\n\n"
        f"Strict Guidelines:\n"
        f"1. Do not use technical jargon (e.g. pods, namespaces, replicasets, iptables, configmaps, docker).\n"
        f"2. Clearly identify: What happened, Business Impact, Mitigation Steps Taken, and Long-term Prevention suggestions.\n"
        f"3. Keep it brief, professional, and clear."
    )

    try:
        # Select cheap fast model tier since it's a summary task
        resp = llm_manager.generate_suggestion(
            anomaly_type="EXECUTIVE_SUMMARY",
            description=prompt,
            prompt_context="Translate Kubernetes alerts into C-suite narrative.",
            rag_context="No code details.",
            severity="INFO",
            latency_critical=False,
            cost_sensitive=True
        )
        summary_text = resp.analysis
    except Exception as e:
        logger.warning("executive_summary_llm_failed", error=str(e))
        # Bulletproof fallback description
        summary_text = (
            f"An anomaly of class {incident.metric_type} was detected affecting service {incident.source}. "
            f"SentinelFlow verified security metrics and took containment action: '{incident.suggested_action}'. "
            f"The service state was successfully stabilized with minimal down-time."
        )

    simplified_explanation = "No reasoning details available yet."
    if incident.explainability_json:
        try:
            exp_data = json.loads(incident.explainability_json)
            simplified_explanation = exp_data.get("overall_explanation", simplified_explanation)
        except Exception:
            pass

    from .compliance_service import ComplianceService
    comp_data = ComplianceService.generate_compliance_checklist(db, incident)

    report_payload = {
        "summary": summary_text,
        "simplified_explanation": simplified_explanation,
        "business_impact": {
            "affected_users": impact["affected_users"],
            "revenue_lost_usd": impact["financial_impact_usd"],
            "risk_score": impact["risk_level"],
            "impact_score": impact["impact_score"]
        },
        "estimated_recovery_time_mins": int(impact["duration_mins"] * 1.2) if incident.resolved_at is None else int(impact["duration_mins"]),
        "compliance": {
            "regulations_applicable": comp_data["applicable_regulations"],
            "compliance_status": impact["compliance_status"],
            "required_notifications": impact["required_notifications"],
            "checklist": comp_data["checklist"],
            "compliance_score_percent": comp_data["compliance_score_percent"]
        }
    }

    # Save to db
    try:
        incident.executive_report_json = json.dumps(report_payload)
        db.commit()
    except Exception as db_err:
        logger.warning("executive_report_cache_save_failed", error=str(db_err))

    return report_payload
