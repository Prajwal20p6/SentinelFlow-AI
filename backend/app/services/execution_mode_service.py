"""
SentinelFlow AI — Execution Mode Service
Validates governance thresholds (Autonomy level, Restricted Services, Confidence, Rate Limit, Blast Radius).
"""

import datetime
from sqlalchemy.orm import Session
from ..models.models import ExecutionConfig, TimelineEvent, Incident, _utcnow
from ..core.observability import logger

class ExecutionModeService:
    """Evaluates and enforces autonomous remediation compliance rules."""

    @staticmethod
    def get_config(db: Session) -> ExecutionConfig:
        """Fetch the active global execution policy config."""
        cfg = db.query(ExecutionConfig).filter(ExecutionConfig.id == 1).first()
        if not cfg:
            cfg = ExecutionConfig(
                id=1,
                mode="ASSISTED",
                rate_limit_per_minute=5,
                min_confidence_score=90,
                max_blast_radius=10,
                restricted_services="payment",
                low_risk_actions="restart_pod,scale_service,rollout_restart"
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
        return cfg

    @staticmethod
    def update_config(
        db: Session,
        mode: str,
        rate_limit_per_minute: int,
        min_confidence_score: int,
        max_blast_radius: int,
        restricted_services: str,
        low_risk_actions: str
    ) -> ExecutionConfig:
        """Update and commit execution configurations."""
        cfg = ExecutionModeService.get_config(db)
        
        # Normalize operating mode
        upper_mode = mode.strip().upper() if mode else "ASSISTED"
        if upper_mode in ("MANUAL",):
            cfg.mode = "MANUAL"
        elif upper_mode in ("ASSISTED", "POLICY_BASED", "SUPERVISED", "SEMI_AUTONOMOUS"):
            cfg.mode = "ASSISTED"
        elif upper_mode in ("AUTONOMOUS", "FULLY_AUTONOMOUS"):
            cfg.mode = "AUTONOMOUS"
        else:
            cfg.mode = "ASSISTED"

        cfg.rate_limit_per_minute = rate_limit_per_minute
        cfg.min_confidence_score = min_confidence_score
        cfg.max_blast_radius = max_blast_radius
        cfg.restricted_services = restricted_services
        cfg.low_risk_actions = low_risk_actions
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def should_auto_execute(
        db: Session,
        incident_id: int,
        confidence_score: float,
        action_command: str,
        target_service: str,
        affected_services_count: int,
        severity: str = "MEDIUM"
    ) -> tuple[bool, str]:
        """
        Governs whether an action can execute autonomously.
        Enforces operating mode (MANUAL, ASSISTED, AUTONOMOUS), safety validation,
        restricted services list, confidence score, blast radius, and rate limits.
        """
        cfg = ExecutionModeService.get_config(db)
        mode = (cfg.mode or "ASSISTED").upper()
        
        # 1. Check Autonomy Mode
        if mode == "MANUAL":
            return False, "Governance: Mode is set to MANUAL. Operator sign-off required."
            
        if mode in ("ASSISTED", "POLICY_BASED", "SUPERVISED"):
            return False, "Governance: Mode is set to ASSISTED (Safe Enterprise Default). Human approval required before remediation execution."

        if mode not in ("AUTONOMOUS", "FULLY_AUTONOMOUS", "SEMI_AUTONOMOUS"):
            return False, f"Governance: Unknown or restricted mode ({mode}). Operator sign-off required."

        # 2. Check Restricted Services & Hardcoded Service Overrides
        target_lower = target_service.lower()
        if "payment" in target_lower:
            return False, "Governance: Per-Service Override - Payment API always requires manual approval."
        if "database" in target_lower or "db" in target_lower:
            return False, "Governance: Per-Service Override - Database always requires manual approval."

        # 3. Check Restricted Services from DB config
        if cfg.restricted_services:
            restricted = [s.strip().lower() for s in cfg.restricted_services.split(",") if s.strip()]
            if target_lower in restricted:
                return False, f"Governance: Target service '{target_service}' is in restricted list. Manual override required."
            
        # 4. Check Blast Radius
        if affected_services_count > cfg.max_blast_radius:
            return False, f"Governance: Potential blast radius of {affected_services_count} services exceeds maximum ({cfg.max_blast_radius})."

        # 5. Check High-Risk Command Keywords
        action_lower = action_command.lower()
        high_risk_words = ["terminate", "drain", "delete", "destroy", "purge"]
        if any(word in action_lower for word in high_risk_words):
            return False, "Governance: Action contains blocked high-risk keywords."

        # 6. Check Global Minimum Confidence Score Gate
        if confidence_score < cfg.min_confidence_score:
            return False, f"Governance: Confidence score ({confidence_score}%) is below configured threshold ({cfg.min_confidence_score}%)."

        # 7. Check Execution Rate Limiting
        one_min_ago = _utcnow() - datetime.timedelta(seconds=60)
        auto_count = db.query(TimelineEvent).filter(
            TimelineEvent.event_type == "REMEDIATION_EXECUTED",
            TimelineEvent.actor == "sentinelflow-autopilot",
            TimelineEvent.timestamp >= one_min_ago
        ).count()
        if auto_count >= cfg.rate_limit_per_minute:
            return False, f"Governance: Rate limiting breached. {auto_count} actions triggered in the last minute (limit: {cfg.rate_limit_per_minute})."

        # 8. Check Policy Engine Validation
        from .policy_engine import PolicyEngine
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            allowed, reason, _ = PolicyEngine.evaluate_incident(db, incident)
            if not allowed:
                return False, f"Governance Policy Engine: {reason}"

        return True, "Governance: Matches AUTONOMOUS criteria and safety validation. Auto-executing."



