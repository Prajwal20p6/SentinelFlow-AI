"""
SentinelFlow AI — Threat Intelligence Agent (Mastra-Inspired)
Dedicated security intelligence agent that extracts and processes compromise metrics.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .rca_service import MastraAgent, MastraTool
from .threat_intel_service import (
    extract_iocs_from_text,
    query_threat_intel,
    VirusTotalWrapper,
    AbuseIPDBWrapper
)
from ..core.config import get_settings

settings = get_settings()


# ── Agentic Enrichment Tools ─────────────────────────────────

class VTEnrichmentTool(MastraTool):
    """Mastra Tool for VirusTotal IOC enrichment queries."""
    def __init__(self):
        super().__init__(
            name="VTEnrichmentTool",
            description="Queries VirusTotal backend wrappers for IP addresses, domains, and file hash threat info."
        )

    def execute(self, db: Session, ioc_type: str, ioc_value: str) -> Dict[str, Any]:
        vt = VirusTotalWrapper(settings.VIRUSTOTAL_API_KEY)
        if ioc_type == "ip":
            return vt.check_ip(ioc_value)
        elif ioc_type == "domain":
            return vt.check_domain(ioc_value)
        elif ioc_type == "hash":
            return vt.check_hash(ioc_value)
        elif ioc_type == "url":
            return vt.check_url(ioc_value)
        return {"details": "Unsupported IOC type."}


class AbuseIPDBTool(MastraTool):
    """Mastra Tool for AbuseIPDB IP reputation queries."""
    def __init__(self):
        super().__init__(
            name="AbuseIPDBTool",
            description="Queries AbuseIPDB backend wrappers for IP address abuse score and reports tally."
        )

    def execute(self, ip_address: str) -> Dict[str, Any]:
        abuse = AbuseIPDBWrapper(settings.ABUSEIPDB_API_KEY)
        return abuse.check_ip(ip_address)


class IOCExtractionTool(MastraTool):
    """Mastra Tool for parsing indicators of compromise from messages."""
    def __init__(self):
        super().__init__(
            name="IOCExtractionTool",
            description="Extracts IP addresses, domains, MD5/SHA256 hashes, URLs, and emails from unstructured incident logs."
        )

    def execute(self, text: str) -> List[Dict[str, str]]:
        return extract_iocs_from_text(text)


# ── Threat Intelligence Agent ────────────────────────────────

class ThreatIntelAgent(MastraAgent):
    """Mastra Agent specialized in security threat assessment and indicator enrichment."""
    def __init__(self):
        super().__init__(
            name="ThreatIntelAgent",
            instructions=(
                "Parse active incident logs, extract suspicious indicator metrics (IOCs), "
                "query VirusTotal and AbuseIPDB tools, evaluate overall incident threat levels, "
                "and generate structured security playbooks and quarantine rules."
            ),
            tools=[
                VTEnrichmentTool(),
                AbuseIPDBTool(),
                IOCExtractionTool()
            ]
        )

    def assess_security_risk(self, db: Session, text_payload: str, incident_id: Optional[int] = None) -> Dict[str, Any]:
        """Runs the agent assessment flow over unstructured text, reading and writing to shared memory."""
        import json

        # 1. Retrieve prior SRE context from shared memory
        shared_rca_context = ""
        if incident_id:
            try:
                from .memory_service import retrieve_memory
                memories = retrieve_memory("shared_memory", "rca_diagnostics", incident_id, limit=1)
                if memories:
                    rca_data = json.loads(memories[0]["value"])
                    shared_rca_context = f"\n[RCA Agent Context] Primary cause: {rca_data.get('primary_cause')}. Evidence: {', '.join(rca_data.get('evidence', []))}"
                    text_payload = f"{text_payload}\n{shared_rca_context}"
            except Exception:
                pass

        # 2. Extract IOCs
        iocs = self.tools["IOCExtractionTool"].execute(text_payload)
        if not iocs:
            result = {
                "overall_threat_level": "CLEAN",
                "risk_score": 0,
                "findings": [],
                "recommendations": "No suspicious indicators of compromise detected in incident details."
            }
            if incident_id:
                try:
                    from .memory_service import store_memory
                    store_memory("shared_memory", "threat_intel", json.dumps(result), incident_id, "threat_intel_agent")
                except Exception:
                    pass
            return result

        # 3. Query wrappers and score threats
        findings = []
        high_threat_count = 0
        remediation_playbook = []

        for ioc in iocs:
            vt_info = self.tools["VTEnrichmentTool"].execute(db, ioc["type"], ioc["value"])
            threat_level, _ = query_threat_intel(db, ioc["type"], ioc["value"])
            
            reputation = 0
            if ioc["type"] == "ip":
                abuse_info = self.tools["AbuseIPDBTool"].execute(ioc["value"])
                reputation = abuse_info.get("abuseConfidenceScore", 0)
                if reputation >= 80:
                    threat_level = "HIGH"
            else:
                reputation = vt_info.get("attributes", {}).get("reputation", 0)

            findings.append({
                "type": ioc["type"],
                "value": ioc["value"],
                "threat_level": threat_level,
                "reputation_score": reputation
            })

            if threat_level == "HIGH":
                high_threat_count += 1
                if ioc["type"] == "ip":
                    remediation_playbook.append(f"Block IP traffic from {ioc['value']} via gateway firewall rules.")
                elif ioc["type"] == "domain":
                    remediation_playbook.append(f"Blacklist domain address {ioc['value']} on DNS host routes.")
                elif ioc["type"] == "hash":
                    remediation_playbook.append(f"Isolate host container and quarantine binary hash: {ioc['value']}.")

        overall_threat = "CLEAN"
        risk_score = 0
        if high_threat_count > 0:
            overall_threat = "HIGH"
            risk_score = min(100, 70 + (high_threat_count * 10))
        elif len(iocs) > 0:
            overall_threat = "MEDIUM"
            risk_score = 45

        recommendations = " ".join(remediation_playbook) if remediation_playbook else "Monitor indicators for traffic behavior changes."

        from .explainability_service import ExplainabilityService
        exp_details = ExplainabilityService.get_threat_intel_explanation(overall_threat, findings)

        result = {
            "overall_threat_level": overall_threat,
            "risk_score": risk_score,
            "findings": findings,
            "recommendations": recommendations,
            "confidence_score": 0.95,
            "explainability": exp_details
        }

        # 4. Write findings to shared and personal memories
        if incident_id:
            try:
                from .memory_service import store_memory
                store_memory(
                    collection_name="shared_memory",
                    key="threat_intel",
                    value=json.dumps(result),
                    incident_id=incident_id,
                    agent_id="threat_intel_agent"
                )
                store_memory(
                    collection_name="agent_memory_threat_intel_agent",
                    key=f"assessment_run_{incident_id}",
                    value=f"Overall threat assessed: {overall_threat} (Risk score: {risk_score})",
                    incident_id=incident_id,
                    agent_id="threat_intel_agent"
                )
            except Exception:
                pass

        return result
