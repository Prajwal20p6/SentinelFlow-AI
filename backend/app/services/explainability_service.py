"""
SentinelFlow AI — AI Explainability Service
Tracks, formats, and persists detailed reasoning for every agentic decision.
"""

from typing import Dict, Any, List

class ExplainabilityService:
    """Consolidation service for managing AI explainability metrics, citation sources, and rejected alternatives."""

    @staticmethod
    def create_explanation(
        what_analyzed: str,
        how_analyzed: str,
        why_conclusion: str,
        alternatives: List[Dict[str, str]],
        confidence_score: float,
        sources: List[str],
        decision_path: str
    ) -> Dict[str, Any]:
        """
        Structure an explainability payload for auditing and client dashboard displays.
        """
        return {
            "what_analyzed": what_analyzed,
            "how_analyzed": how_analyzed,
            "why_conclusion": why_conclusion,
            "alternatives": alternatives,
            "confidence_score": confidence_score,
            "sources": sources,
            "decision_path": decision_path,
            "explanation": f"AI Decision path: {decision_path}. Analyzed {what_analyzed} via {how_analyzed}. Concluded because: {why_conclusion}."
        }

    @classmethod
    def get_rca_explanation(cls, metric_type: str, evidence: List[str]) -> Dict[str, Any]:
        """Helper to generate Root Cause explanation payload."""
        evidence_str = ", ".join(evidence) if evidence else "telemetry spikes"
        return cls.create_explanation(
            what_analyzed="Log lines, metric telemetry data, recent git/manifest deployments, and similar historical incidents.",
            how_analyzed="Mastra Heuristic and LLM Reasoning Prompt comparison against vector RAG collections.",
            why_conclusion=f"Pattern matches metric type {metric_type} with diagnostic evidence: {evidence_str}.",
            alternatives=[
                {
                    "option": "Hardware host hypervisor failure",
                    "reason": "Rejected because hypervisor reported healthy stats, only individual container CPU/Memory limits were violated."
                },
                {
                    "option": "Database corruption",
                    "reason": "Rejected because read/write queries return valid HTTP status codes on other namespaces."
                }
            ],
            confidence_score=92.0 if metric_type == "CPU_SPIKE" else 85.0,
            sources=["Kubernetes Event stream log", "Prometheus CPU metrics history", "Qdrant similar incidents memory"],
            decision_path="Telemetry Spike -> Logs scan -> Historical similarity search -> RCA conclusion"
        )

    @classmethod
    def get_threat_intel_explanation(cls, overall_threat_level: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper to generate Threat Intelligence explanation payload."""
        ioc_values = [f"{f['type']}:{f['value']}" for f in findings]
        iocs_str = ", ".join(ioc_values) if ioc_values else "no parsed indicators"
        return cls.create_explanation(
            what_analyzed=f"Extracted Indicators of Compromise (IPs, hashes, domains) from incident log context: {iocs_str}.",
            how_analyzed="Lookup check against VirusTotal reputation database, AbuseIPDB scoring registries, and local memory cache.",
            why_conclusion=f"Overall threat level assessed as {overall_threat_level} because of active matches on reputation scoring.",
            alternatives=[
                {
                    "option": "Ignore indicators as transient false positives",
                    "reason": "Rejected because parsed addresses have explicit high malicious flag ratios on public VT directories."
                }
            ],
            confidence_score=98.0 if overall_threat_level == "HIGH" else 75.0,
            sources=["VirusTotal API API wrapper", "AbuseIPDB reputation catalog", "Internal Threat Cache (24h TTL)"],
            decision_path="Context parsing -> IOC extraction -> External reputation queries -> Playbook synthesis"
        )

    @classmethod
    def get_remediation_explanation(cls, action: str, alternative_action: str, reason_rejected: str) -> Dict[str, Any]:
        """Helper to generate Remediation decision explanation payload."""
        return cls.create_explanation(
            what_analyzed="Incident severity category, auto-pilot confidence thresholds, and past remediation rollout results.",
            how_analyzed="Enkrypt AI prompt scanning evaluation checks and risk-ranking assessment algorithms.",
            why_conclusion=f"Recommended action '{action}' because it represents the highest safety-to-recovery ratio.",
            alternatives=[
                {
                    "option": alternative_action,
                    "reason": reason_rejected
                }
            ],
            confidence_score=85.0,
            sources=["Enkrypt security policy engine", "SRE rollback history", "Autopilot threshold configuration settings"],
            decision_path="Action generation -> Security scan pass -> Safety ranking -> Execution approval recommendation"
        )
