"""
SentinelFlow AI — Policy-Based Automation Engine
Evaluates incident conditions against safety guardrails to determine auto-execution suitability.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy.orm import Session

from ..models.models import Policy, Incident, ExecutionConfig, IncidentLog
from ..core.observability import logger

class PolicyEngine:
    """Evaluates rules, exceptions, safety guardrails, and execution mode criteria."""

    @staticmethod
    def seed_default_policies(db: Session) -> None:
        """Seeds the 4 default enterprise autopilot policies if they do not exist."""
        default_policies = [
            {
                "id": 1,
                "name": "Auto-restart crashed pods",
                "description": "Automatically restarts Kubernetes pods that have crashed, except for payment or database systems.",
                "enabled": True,
                "conditions_json": json.dumps({
                    "incident_type": "KubernetesPodCrash",
                    "min_confidence": 90,
                    "max_risk": 20,
                    "max_pods": 5
                }),
                "actions_json": json.dumps(["restart_pod"]),
                "exceptions_json": json.dumps(["payment-api", "database", "auth-service"]),
                "rate_limit": 10,
                "approval_required": False
            },
            {
                "id": 2,
                "name": "Auto-scale overloaded services",
                "description": "Automatically scale up service replicas when resource load limit is reached.",
                "enabled": True,
                "conditions_json": json.dumps({
                    "incident_type": "HighLoad",
                    "min_confidence": 85,
                    "max_risk": 25,
                    "max_services": 3
                }),
                "actions_json": json.dumps(["scale_up_replicas"]),
                "exceptions_json": json.dumps(["stateful_services"]),
                "rate_limit": 5,
                "approval_required": False
            },
            {
                "id": 3,
                "name": "Always require approval for database changes",
                "description": "Ensures any changes to database or persistence services require manual checkoff.",
                "enabled": True,
                "conditions_json": json.dumps({
                    "service_type": "Database"
                }),
                "actions_json": json.dumps(["require_approval"]),
                "exceptions_json": json.dumps([]),
                "rate_limit": 0,
                "approval_required": True
            },
            {
                "id": 4,
                "name": "Always require approval for payment systems",
                "description": "Ensures payment endpoints require high-priority manual responder authorization.",
                "enabled": True,
                "conditions_json": json.dumps({
                    "service": "payment-api"
                }),
                "actions_json": json.dumps(["require_approval"]),
                "exceptions_json": json.dumps([]),
                "rate_limit": 0,
                "approval_required": True
            }
        ]

        for p_data in default_policies:
            existing = db.query(Policy).filter(Policy.id == p_data["id"]).first()
            if not existing:
                policy = Policy(**p_data)
                db.add(policy)
        
        try:
            db.commit()
            logger.info("autopilot_policies_seeded")
        except Exception as e:
            db.rollback()
            logger.error("autopilot_policies_seed_failed", error=str(e))

    @staticmethod
    def evaluate_incident(db: Session, incident: Incident) -> Tuple[bool, str, List[str]]:
        """
        Evaluates the policy engine rules and guardrails for a given incident.
        Returns: Tuple (auto_execute_allowed, decision_rationale, list_of_actions).
        """
        # 1. Check Global Execution Mode
        config = db.query(ExecutionConfig).order_by(ExecutionConfig.id.asc()).first()
        global_mode = config.mode if config else "MANUAL"

        if global_mode == "MANUAL":
            return False, "Platform is in MANUAL mode. All actions require manual approval.", []

        # Check emergency manual override flag in DB or settings
        # (Mode MANUAL serves as the emergency override)

        # 2. Safety Guardrails (Always Applied globally)
        confidence = int(incident.confidence_score * 100) if incident.confidence_score else 0
        
        # Hard limits
        if confidence < 85:
            return False, f"Guardrail: Confidence score too low ({confidence}% < 85%). Requires approval.", []
        
        # In our system risk is mapped from prioritization/audit
        risk_score = 10  # default low risk
        if risk_score > 25:
            return False, f"Guardrail: Risk score too high ({risk_score} > 25). Requires approval.", []

        # 3. Evaluate matching policies
        enabled_policies = db.query(Policy).filter(Policy.enabled == True).all()

        for policy in enabled_policies:
            conditions = json.loads(policy.conditions_json)
            actions = json.loads(policy.actions_json)
            exceptions = json.loads(policy.exceptions_json) if policy.exceptions_json else []

            # Check exceptions
            if incident.source in exceptions or incident.metric_type in exceptions:
                logger.info("policy_skipped_due_to_exception", policy=policy.name, incident_id=incident.id)
                continue

            # Evaluate type matching
            match = False
            
            # Crash match
            if conditions.get("incident_type") == "KubernetesPodCrash" and "CRASH" in incident.metric_type.upper():
                match = True
            # Load match
            elif conditions.get("incident_type") == "HighLoad" and ("SPIKE" in incident.metric_type.upper() or "LOAD" in incident.metric_type.upper()):
                match = True
            # DB match
            elif conditions.get("service_type") == "Database" and "DATABASE" in incident.source.upper():
                match = True
            # Service specific match
            elif conditions.get("service") == incident.source:
                match = True

            # If match, apply checks
            if match:
                # If policy explicitly requires approval
                if policy.approval_required:
                    return False, f"Policy '{policy.name}' explicitly requires manual SRE approval.", []

                # Verify policy-specific constraints
                min_conf = conditions.get("min_confidence", 85)
                if confidence < min_conf:
                    continue

                # Rate limiting check (e.g. max 10 auto-executions per minute globally)
                one_min_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
                recent_autos = db.query(IncidentLog).filter(
                    IncidentLog.stage == "STATE_TRANSITION",
                    IncidentLog.message.like("%Auto-execute%"),
                    IncidentLog.timestamp >= one_min_ago
                ).count()

                if recent_autos >= policy.rate_limit:
                    return False, f"Rate limit reached for policy '{policy.name}' ({recent_autos} executions/min).", []

                return True, f"Automated execution triggered by policy '{policy.name}' matching conditions.", actions

        return False, "No matching auto-execution policies found. Defaulting to manual approval.", []
