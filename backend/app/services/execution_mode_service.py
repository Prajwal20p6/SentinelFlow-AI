"""
SentinelFlow AI — Execution Mode Service
Validates governance thresholds (Autonomy level, Restricted Services, Confidence, Rate Limit, Blast Radius).
"""

import datetime
from sqlalchemy.orm import Session
from ..models.models import ExecutionConfig, TimelineEvent, Incident
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
                mode="MANUAL",
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
        cfg.mode = mode
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
        Validates mode, restricted services lists, confidence score, blast radius, and rate limits.
        """
        cfg = ExecutionModeService.get_config(db)
        
        # 1. Check Autonomy Mode
        if cfg.mode == "MANUAL":
            return False, "Governance: Mode is set to MANUAL. Operator sign-off required."
            
        # 1.5 Evaluate dynamic policies for POLICY_BASED or SUPERVISED modes
        if cfg.mode in ("POLICY_BASED", "SUPERVISED"):
            from .policy_engine import PolicyEngine
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident:
                allowed, reason, actions = PolicyEngine.evaluate_incident(db, incident)
                return allowed, f"Policy Engine ({cfg.mode}): {reason}"
            
        # 2. Check Restricted Services & Example Configuration overrides
        target_lower = target_service.lower()
        if "payment" in target_lower:
            return False, "Governance: Per-Service Override - Payment API always requires manual approval."
        if "database" in target_lower or "db" in target_lower:
            return False, "Governance: Per-Service Override - Database always requires manual approval."

        # Note: Cache service: Can auto-execute low-risk actions.
        # This means if target_service is "cache", we treat it normally, which will check the mode and risk commands below.
        
        # 3. Check Restricted Services from DB config
        restricted = [s.strip().lower() for s in cfg.restricted_services.split(",") if s.strip()]
        if target_lower in restricted:
            return False, f"Governance: Target service '{target_service}' is in restricted list. Manual override required."
            
        # 4. Check Blast Radius
        if affected_services_count > cfg.max_blast_radius:
            return False, f"Governance: Potential blast radius of {affected_services_count} services exceeds maximum ({cfg.max_blast_radius})."

        # 5. Check Rate Limiting and Risk Profiles depending on Mode
        action_lower = action_command.lower()
        
        # Determine if action is low risk
        low_risk_words = [w.strip().lower() for w in cfg.low_risk_actions.split(",") if w.strip()]
        is_low_risk = any(word in action_lower for word in low_risk_words)
        
        # Deny high-risk keywords explicitly
        high_risk_words = ["terminate", "drain", "delete", "destroy", "purge"]
        if any(word in action_lower for word in high_risk_words):
            is_low_risk = False

        if cfg.mode == "SEMI_AUTONOMOUS":
            # P0 (Critical) Severity
            if severity == "CRITICAL":
                # Actions allowed: Restart pod, scale service, restart deployment
                # Check confidence threshold: 85%
                if confidence_score < 85:
                    return False, f"Governance: Confidence score ({confidence_score}%) is below P0 threshold (85%)."
                
                # Check rate limit: 10/min
                one_min_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
                auto_count = db.query(TimelineEvent).filter(
                    TimelineEvent.event_type == "REMEDIATION_EXECUTED",
                    TimelineEvent.actor == "sentinelflow-autopilot",
                    TimelineEvent.timestamp >= one_min_ago
                ).count()
                if auto_count >= 10:
                    return False, f"Governance: Rate limit breached for P0. {auto_count} actions triggered in the last minute (limit: 10/min)."
                
                # Verify action command keywords:
                if any(word in action_lower for word in high_risk_words):
                    return False, f"Governance: Action contains blocked high-risk keywords for P0."
                
                return True, "Governance: Incident P0 severity and low/medium risk actions meet SEMI_AUTONOMOUS criteria."

            # P1 (High) Severity
            elif severity == "HIGH":
                # Actions allowed: Restart pod, scale service
                # Check confidence threshold: 90%
                if confidence_score < 90:
                    return False, f"Governance: Confidence score ({confidence_score}%) is below P1 threshold (90%)."
                
                # Check rate limit: 5/min
                one_min_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
                auto_count = db.query(TimelineEvent).filter(
                    TimelineEvent.event_type == "REMEDIATION_EXECUTED",
                    TimelineEvent.actor == "sentinelflow-autopilot",
                    TimelineEvent.timestamp >= one_min_ago
                ).count()
                if auto_count >= 5:
                    return False, f"Governance: Rate limit breached for P1. {auto_count} actions triggered in the last minute (limit: 5/min)."
                
                # Allowed: restart pod, scale service. Exclude deployment restarts!
                if "deployment" in action_lower or "rollout" in action_lower:
                    return False, f"Governance: Deployment actions are not allowed for P1 under SEMI_AUTONOMOUS mode."
                
                if not is_low_risk:
                    return False, f"Governance: High-risk action proposed for P1 under SEMI_AUTONOMOUS mode."
                
                return True, "Governance: Low-risk action meets SEMI_AUTONOMOUS P1 criteria. Auto-executing."

            # P2 (Medium) & P3 (Low) Severity
            else:
                return False, f"Governance: Auto-execute: NO for P2/P3 ({severity}) severity under SEMI_AUTONOMOUS. Manual approval required."

        if cfg.mode == "FULLY_AUTONOMOUS":
            # Check global min confidence score gate from database config
            if confidence_score < cfg.min_confidence_score:
                return False, f"Governance: Confidence score ({confidence_score}%) is below configured threshold ({cfg.min_confidence_score}%)."
            
            # Check rate limiting from DB config
            one_min_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
            auto_count = db.query(TimelineEvent).filter(
                TimelineEvent.event_type == "REMEDIATION_EXECUTED",
                TimelineEvent.actor == "sentinelflow-autopilot",
                TimelineEvent.timestamp >= one_min_ago
            ).count()
            if auto_count >= cfg.rate_limit_per_minute:
                return False, f"Governance: Rate limiting breached. {auto_count} actions triggered in the last minute (limit: {cfg.rate_limit_per_minute})."

            return True, "Governance: Matches FULLY_AUTONOMOUS criteria. Auto-executing."

        return False, "Governance: Unrecognized execution config state."


