"""
SentinelFlow AI — Incident Prioritization Agent
Calculates dynamic priority scores, SLAs, and routing urgency levels.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

class IncidentPrioritizationAgent:
    """Orchestrates severity scoring and maps incident properties to P0-P4 SLAs."""

    @staticmethod
    def calculate_priority(
        metric_type: str,
        severity: str,
        description: str,
        recurrence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates priority score (0-100) and targets:
        - Criticality (0-30 points)
        - Security Severity (0-20 points)
        - User Impact (0-25 points)
        - Business Impact (0-15 points)
        - Historical Pattern (0-10 points)
        """
        score = 0

        # 1. Criticality (0-30 points)
        criticality_map = {
            "payment-gateway": 30,
            "auth-service": 28,
            "postgres": 25,
            "api-gateway": 20,
            "notification-svc": 10,
        }
        criticality_points = 5
        desc_lower = description.lower()
        for k, v in criticality_map.items():
            if k in desc_lower:
                criticality_points = v
                break
        score += criticality_points

        # 2. Security Severity (0-20 points)
        security_points = 0
        if "credential" in desc_lower or "theft" in desc_lower:
            security_points = 20
        elif "exfiltration" in desc_lower or "leak" in desc_lower:
            security_points = 18
        elif "malware" in desc_lower or "ransomware" in desc_lower:
            security_points = 16
        elif "unauthorized" in desc_lower or "access" in desc_lower:
            security_points = 14
        elif severity == "CRITICAL":
            security_points = 10
        score += security_points

        # 3. User Impact (0-25 points)
        user_points = 1
        if "thousands" in desc_lower or "thousand" in desc_lower or "all users" in desc_lower:
            user_points = 25
        elif "hundreds" in desc_lower or "hundred" in desc_lower:
            user_points = 15
        elif "dozens" in desc_lower or "dozen" in desc_lower:
            user_points = 8
        elif "single" in desc_lower or "individual" in desc_lower:
            user_points = 2
        score += user_points

        # 4. Business Impact (0-15 points)
        business_points = 5
        if "revenue" in desc_lower or "financial" in desc_lower:
            business_points = 15
        elif "compliance" in desc_lower or "gdpr" in desc_lower or "pci" in desc_lower:
            business_points = 14
        elif "sla breach" in desc_lower or "violation" in desc_lower:
            business_points = 12
        elif "reputation" in desc_lower:
            business_points = 10
        score += business_points

        # 5. Historical Pattern (0-10 points)
        history_points = 0
        if recurrence_count >= 5:
            history_points = 8
        elif recurrence_count >= 2:
            history_points = 5
        elif recurrence_count == 1:
            history_points = 3
        score += history_points

        # Cap score at 100
        score = min(100, score)

        # 6. SLA Mapping
        if score >= 90:
            sla_target = "P0"
            duration = timedelta(minutes=15)
        elif score >= 70:
            sla_target = "P1"
            duration = timedelta(hours=1)
        elif score >= 50:
            sla_target = "P2"
            duration = timedelta(hours=4)
        elif score >= 30:
            sla_target = "P3"
            duration = timedelta(hours=24)
        else:
            sla_target = "P4"
            duration = timedelta(days=3)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sla_breach_at = now + duration

        reasoning = (
            f"Calculated priority score {score}/100. Criticality component: {criticality_points}/30, "
            f"Security: {security_points}/20, User impact: {user_points}/25, Business impact: {business_points}/15, "
            f"Recurrence score: {history_points}/10. Mapped to target SLA: {sla_target}."
        )

        return {
            "score": score,
            "sla_target": sla_target,
            "sla_breach_at": sla_breach_at,
            "reasoning": reasoning
        }
