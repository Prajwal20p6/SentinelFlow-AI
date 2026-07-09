"""
SentinelFlow AI — Remediation Simulation Engine
Generates "what-if" impact analysis, downtime estimates, and rollback plans.
"""

from typing import Dict, Any, List

class SimulationEngine:
    """Predicts outcome parameters before actual code/manifest changes execute on cluster."""

    @staticmethod
    def simulate(action: str, anomaly_type: str = "GENERIC") -> Dict[str, Any]:
        """
        Simulate remediation commands and return predicted impact dashboard attributes.
        """
        action_lower = action.lower()
        
        # Default fallback simulation payload
        sim = {
            "action": action,
            "remediation_type": "GENERIC",
            "affected_resources": ["generic-pod"],
            "affected_users": 10,
            "predicted_downtime_sec": 5,
            "predicted_impact": "Minor resource adjustment.",
            "risk_assessment": "LOW",
            "rollback_possible": True,
            "rollback_plan": "Revert telemetry metrics manually or reset the affected configurations.",
            "success_probability": 80.0
        }

        # Case A: Pod Restart (e.g. restart pod, delete pod)
        if "restart pod" in action_lower or "delete pod" in action_lower or "kill pod" in action_lower:
            sim.update({
                "remediation_type": "POD_RESTART",
                "affected_resources": ["payment-gateway-9f7d2e4a1"],
                "affected_users": 150,
                "predicted_downtime_sec": 30,
                "predicted_impact": "Connections to this specific replica will drop. Client clients will auto-reconnect to healthy instances.",
                "risk_assessment": "LOW",
                "rollback_possible": True,
                "rollback_plan": "The Kubernetes replica controller will spawn a fresh instance automatically. To undo, rerun check.",
                "success_probability": 85.0
            })

        # Case B: Deployment Restart (e.g. rollout restart)
        elif "rollout restart" in action_lower or "restart deployment" in action_lower:
            sim.update({
                "remediation_type": "DEPLOYMENT_RESTART",
                "affected_resources": ["api-gateway", "auth-service"],
                "affected_users": 0,  # Zero-downtime rolling update
                "predicted_downtime_sec": 0,
                "predicted_impact": "Zero-downtime rolling update (30% maxUnavailable surge strategy). New pods initialized while old pods drain.",
                "risk_assessment": "MEDIUM",
                "rollback_possible": True,
                "rollback_plan": "Run 'kubectl rollout undo deployment/<name>' to revert immediately to the previous replica version.",
                "success_probability": 95.0
            })

        # Case C: Scale Up (e.g. scale deployment)
        elif "scale" in action_lower or "replicas" in action_lower:
            sim.update({
                "remediation_type": "SCALE_UP",
                "affected_resources": ["payment-gateway", "api-gateway"],
                "affected_users": 0,
                "predicted_downtime_sec": 0,
                "predicted_impact": "Increases replica pool sizes. Enhances memory and request handling. Additional CPU/Mem capacity allocated on worker nodes.",
                "risk_assessment": "LOW",
                "rollback_possible": True,
                "rollback_plan": "Scale back down to previous replica count: 'kubectl scale deployment/<name> --replicas=previous'.",
                "success_probability": 98.0
            })

        # Case D: Kill Service (e.g. terminate, stop, delete service)
        elif "kill service" in action_lower or "delete service" in action_lower or "stop service" in action_lower:
            sim.update({
                "remediation_type": "KILL_SERVICE",
                "affected_resources": ["auth-service", "postgres"],
                "affected_users": 5000,
                "predicted_downtime_sec": 120,
                "predicted_impact": "CRITICAL: Service termination. All active API authentication checks will fail immediately. Downstream services affected.",
                "risk_assessment": "CRITICAL",
                "rollback_possible": True,
                "rollback_plan": "Re-apply service config: 'kubectl apply -f service-manifest.yaml'. High recovery startup delay.",
                "success_probability": 40.0
            })

        return sim
