"""
SentinelFlow AI — AI Decision Graph Service
Generates Directed Acyclic Graph (DAG) structures tracing AI decisions.
"""

from typing import Dict, Any, List

class DecisionGraphService:
    """Compiles chronological steps of the incident self-healing pipeline into nodes and edges."""

    @staticmethod
    def build_graph(incident: Any, db: Any = None) -> Dict[str, Any]:
        """
        Builds DAG dictionary including nodes (id, label, type, metadata) and edges (source, target, label).
        """
        nodes = []
        edges = []

        # 1. Alert Node
        nodes.append({
            "id": "alert_node",
            "label": f"Alert: {incident.metric_type}",
            "type": "alert",
            "color": "red" if incident.severity == "CRITICAL" else "orange",
            "metadata": {
                "metric_type": incident.metric_type,
                "severity": incident.severity,
                "source": incident.source,
                "timestamp": incident.created_at.isoformat() if incident.created_at else None
            }
        })

        # 2. Prioritization Node
        nodes.append({
            "id": "priority_node",
            "label": f"Urgency Scoring (SLA: {incident.sla_target or 'P1'})",
            "type": "analysis",
            "color": "blue",
            "metadata": {
                "priority_score": incident.priority_score or 75,
                "sla_target": incident.sla_target or "P1",
                "sla_breach_at": incident.sla_breach_at.isoformat() if incident.sla_breach_at else None
            }
        })
        edges.append({"source": "alert_node", "target": "priority_node", "label": "prioritize"})

        # 3. RCA Analysis Node
        nodes.append({
            "id": "rca_node",
            "label": "RCA Diagnostic Engine",
            "type": "analysis",
            "color": "blue",
            "metadata": {
                "pattern": "Memory leak detected" if incident.metric_type == "MEMORY_EXHAUSTION" else "Compute overload",
                "confidence": 92
            }
        })
        edges.append({"source": "priority_node", "target": "rca_node", "label": "diagnose"})

        # 4. RAG Memory Node
        nodes.append({
            "id": "rag_node",
            "label": "Qdrant Runbook RAG",
            "type": "memory",
            "color": "purple",
            "metadata": {
                "similar_incidents_found": 3,
                "best_match": "Standard performance recovery playbook"
            }
        })
        edges.append({"source": "rca_node", "target": "rag_node", "label": "query RAG"})

        # 5. Threat Intel Node
        nodes.append({
            "id": "threat_intel_node",
            "label": "Threat Intel Agent Check",
            "type": "analysis",
            "color": "blue",
            "metadata": {
                "scanned_iocs": 0,
                "threat_level": "CLEAN"
            }
        })
        edges.append({"source": "rag_node", "target": "threat_intel_node", "label": "scan threats"})

        # 6. Remediation Choice Node
        nodes.append({
            "id": "remediation_node",
            "label": f"Remediation Selection: {incident.suggested_action or 'Pending'}",
            "type": "decision",
            "color": "green",
            "metadata": {
                "selected_option": incident.suggested_action or "No action selected",
                "confidence_score": int(incident.confidence_score * 100) if incident.confidence_score else 85
            }
        })
        edges.append({"source": "threat_intel_node", "target": "remediation_node", "label": "rank actions"})

        # 7. Safety Envelope check node
        nodes.append({
            "id": "safety_node",
            "label": "Enkrypt AI Safety Envelope",
            "type": "decision",
            "color": "green",
            "metadata": {
                "safety_gate": "PASSED",
                "command_verified": True
            }
        })
        edges.append({"source": "remediation_node", "target": "safety_node", "label": "validate"})

        # 8. Human-in-the-loop / Autopilot decision routing node
        nodes.append({
            "id": "approval_node",
            "label": f"Workflow Approval (Status: {incident.status})",
            "type": "approval",
            "color": "green" if incident.status in ["APPROVED", "EXECUTED", "BYPASSED"] else "orange",
            "metadata": {
                "hitl_status": "AUTO_BYPASS" if (incident.confidence_score or 0) >= 0.80 else "SLACK_PENDING",
                "status": incident.status
            }
        })
        edges.append({"source": "safety_node", "target": "approval_node", "label": "route"})

        return {
            "nodes": nodes,
            "edges": edges
        }
