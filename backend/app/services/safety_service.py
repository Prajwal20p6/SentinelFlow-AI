"""
SentinelFlow AI — Enkrypt AI Safety Envelope Service
Input/output guards, command validation, risk assessment, and audit logging.
"""

import os
import re
import time
import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.observability import logger
from ..core.security import compute_chain_hash
from ..models.models import AuditTrail, AIObservabilityTrace


# ── Dangerous Command Patterns (Enkrypt Denylist) ───────────
CRITICAL_PATTERNS = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|)(/|~|\.\.)"), "File deletion traversal — immediate threat of host disk destruction or volume loss"),
    (re.compile(r"\bdd\s+if=.*of=/dev/"), "Direct disk write — risks corrupting block devices"),
    (re.compile(r"\bmkfs\b"), "Filesystem format — will destroy all data on target volume"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"), "System shutdown — will cause immediate service outage"),
    (re.compile(r"\bchmod\s+(-R\s+)?777\b"), "Recursive world-writable permissions — severe security vulnerability"),
    (re.compile(r"\biptables\s+(-F|--flush)"), "Firewall flush — will drop all network security rules"),
]

HIGH_RISK_PATTERNS = [
    (re.compile(r"\bkubectl\s+delete\s+(namespace|ns)\b"), "Namespace deletion — will destroy all resources in namespace"),
    (re.compile(r"\bDROP\s+(TABLE|DATABASE)\b", re.IGNORECASE), "SQL DROP — irreversible data destruction"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "SQL TRUNCATE — bulk data deletion"),
    (re.compile(r"\bFLUSHALL\b", re.IGNORECASE), "Redis FLUSHALL — clears all cached data"),
    (re.compile(r"\bkubectl\s+delete\s+--all\b"), "Mass resource deletion — cluster-wide impact"),
    (re.compile(r"\bcurl\s+.*\|\s*(bash|sh)\b"), "Remote code execution via piped curl — untrusted source"),
]

MODERATE_RISK_PATTERNS = [
    (re.compile(r"\bkubectl\s+scale\b.*--replicas=0\b"), "Scale to zero — will cause service downtime"),
    (re.compile(r"\bkubectl\s+cordon\b"), "Node cordon — prevents new pod scheduling"),
    (re.compile(r"\bkubectl\s+drain\b"), "Node drain — evicts all pods from node"),
]

SAFE_PATTERNS = [
    re.compile(r"\bkubectl\s+(get|describe|logs|top)\b"),
    re.compile(r"\bkubectl\s+rollout\s+(status|history)\b"),
    re.compile(r"\bkubectl\s+rollout\s+restart\b"),
    re.compile(r"\bkubectl\s+scale\b.*--replicas=[1-9]"),
    re.compile(r"\bhelm\s+(list|status|history)\b"),
]


# ── Input Guards (PII Scrubbing & Injection) ─────────────────

def scrub_pii(text: str) -> str:
    """Scrub sensitive credentials, IP addresses, and emails from input telemetry."""
    email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    ip_pattern = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    key_pattern = re.compile(r"\b(api_key|token|password|secret|key)=\S+", re.IGNORECASE)

    scrubbed = email_pattern.sub("[REDACTED_EMAIL]", text)
    scrubbed = ip_pattern.sub("[REDACTED_IP]", scrubbed)
    scrubbed = key_pattern.sub(r"\1=[REDACTED_SECRET]", scrubbed)
    return scrubbed


def detect_prompt_injection(text: str) -> tuple[bool, str]:
    """Check if text contains override patterns indicating prompt injection."""
    injection_patterns = [
        r"\bignore\s+(all\s+)?previous\s+instructions\b",
        r"\bsystem\s+override\b",
        r"\bbypass\s+safety\s+filters\b",
        r"\bnew\s+instruction:\b",
        r"\bforget\s+prior\s+directives\b",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Injection pattern matched: '{pattern}'"
    return False, "Input passes safety gate injection check."


# ── YAML-based Security Policy Engine ───────────────────────

def load_policies_from_yaml(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    policies = []
    current_policy = None
    current_rules = []
    current_rule = None
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
            
        if stripped.startswith("- name:"):
            if current_policy:
                current_policy["rules"] = current_rules
                policies.append(current_policy)
            current_policy = {
                "name": stripped.split("- name:")[1].strip().strip('"').strip("'"),
                "strictness": "medium",
                "rules": []
            }
            current_rules = []
        elif stripped.startswith("strictness:"):
            if current_policy:
                current_policy["strictness"] = stripped.split("strictness:")[1].strip()
        elif stripped.startswith("- pattern:"):
            if current_rule:
                current_rules.append(current_rule)
            pat_val = stripped.split("- pattern:")[1].strip().strip('"').strip("'")
            pat_val = pat_val.replace("\\\\", "\\")
            current_rule = {"pattern": pat_val, "action": "DENY", "reason": ""}
        elif stripped.startswith("action:"):
            if current_rule:
                current_rule["action"] = stripped.split("action:")[1].strip()
        elif stripped.startswith("reason:"):
            if current_rule:
                current_rule["reason"] = stripped.split("reason:")[1].strip().strip('"').strip("'")
                
    if current_rule:
        current_rules.append(current_rule)
    if current_policy:
        current_policy["rules"] = current_rules
        policies.append(current_policy)
        
    return {"policies": policies}


class DynamicPolicyEngine:
    """Hot-reloadable policy engine reading rules from policies.yaml."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.last_modified = 0
        self.rules = []
        self.load_policies()

    def load_policies(self):
        if not os.path.exists(self.filepath):
            return
        
        try:
            mtime = os.path.getmtime(self.filepath)
            if mtime > self.last_modified:
                data = load_policies_from_yaml(self.filepath)
                new_rules = []
                for p in data.get("policies", []):
                    strictness = p.get("strictness", "medium")
                    for r in p.get("rules", []):
                        pattern = r.get("pattern")
                        action = r.get("action", "DENY")
                        reason = r.get("reason", "")
                        try:
                            compiled = re.compile(pattern, re.IGNORECASE)
                            new_rules.append({
                                "pattern": compiled,
                                "action": action,
                                "reason": reason,
                                "strictness": strictness
                            })
                        except Exception as ce:
                            logger.warning("policy_regex_error", pattern=pattern, error=str(ce))
                self.rules = new_rules
                self.last_modified = mtime
                logger.info("policy_engine_loaded", rule_count=len(self.rules), filepath=str(self.filepath))
        except Exception as e:
            logger.error("policy_engine_reload_error", error=str(e))

    def evaluate(self, command: str) -> tuple[str, float, str]:
        self.load_policies()
        cmd_stripped = command.strip()
        
        if self.rules:
            for r in self.rules:
                if r["pattern"].search(cmd_stripped):
                    action = r["action"]
                    reason = r["reason"]
                    strictness = r["strictness"]
                    
                    if action == "DENY":
                        status = "BLOCKED"
                        risk_score = 0.99 if strictness == "high" else 0.85
                        risk_label = "CRITICAL RISK" if strictness == "high" else "HIGH RISK"
                    else:
                        status = "ALLOWED"
                        risk_score = 0.50 if strictness == "medium" else 0.30
                        risk_label = "MODERATE RISK" if strictness == "medium" else "LOW RISK"
                        
                    return (
                        status,
                        risk_score,
                        f"POLICY COMPLIANCE ({risk_label}): {reason}. Action is {status}.",
                    )
                    
        return evaluate_command_safety_static(command)


# Instantiate engine
policy_engine = DynamicPolicyEngine(os.path.join(os.path.dirname(__file__), "..", "core", "policies.yaml"))


def evaluate_command_safety_static(command: str) -> tuple[str, float, str]:
    """Fallback static command check."""
    command_stripped = command.strip()
    for pattern, reason in CRITICAL_PATTERNS:
        if pattern.search(command_stripped):
            return ("BLOCKED", 0.99, f"CRITICAL RISK: {reason}. Command '{command_stripped[:80]}' poses immediate threat.")
    for pattern, reason in HIGH_RISK_PATTERNS:
        if pattern.search(command_stripped):
            return ("BLOCKED", 0.85, f"HIGH RISK: {reason}. Command requires manual review.")
    for pattern, reason in MODERATE_RISK_PATTERNS:
        if pattern.search(command_stripped):
            return ("ALLOWED", 0.50, f"MODERATE RISK: {reason}. Proceed with caution.")
    for pattern in SAFE_PATTERNS:
        if pattern.search(command_stripped):
            return ("ALLOWED", 0.10, "LOW RISK: Command matches known safe patterns. Cleared for execution.")
    return ("ALLOWED", 0.30, "UNCLASSIFIED: Command not in safety database. Default allow with logging.")


def evaluate_command_safety(command: str) -> tuple[str, float, str]:
    """Evaluate a command using the hot-reloadable policies.yaml configuration."""
    return policy_engine.evaluate(command)


def execute_guarded_command(
    db: Session,
    command: str,
    incident_id: Optional[int] = None,
    performed_by: str = "SentinelFlow AI Agent",
) -> dict:
    """
    Full command execution pipeline:
    1. Safety evaluation
    2. Audit trail with chain hashing
    3. Simulated execution (if allowed)
    4. Observability trace
    """
    start = time.time()
    status, risk_score, assessment = evaluate_command_safety(command)

    # ── Chain hash for tamper evidence ───────────────────────
    last_audit = db.query(AuditTrail).order_by(AuditTrail.id.desc()).first()
    prev_hash = last_audit.hash if last_audit else "genesis"
    chain_hash = compute_chain_hash(f"{command}:{status}:{risk_score}", prev_hash)

    # ── Write audit trail ────────────────────────────────────
    audit = AuditTrail(
        incident_id=incident_id,
        command_checked=command,
        status=status,
        risk_score=risk_score,
        risk_assessment=assessment,
        remediation_action=command if status == "ALLOWED" else None,
        performed_by=performed_by,
        hash=chain_hash,
        prev_hash=prev_hash,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # ── Cloud Infrastructure Execution ──────────────────────
    execution_output = None
    if status == "ALLOWED":
        from .cloud_service import remediation_manager
        res = remediation_manager.execute_action(
            db=db,
            incident_id=incident_id or 0,
            command=command,
            performed_by=performed_by,
            dry_run=False
        )
        execution_output = res["output"]

    # ── Record observability trace ───────────────────────────
    elapsed = (time.time() - start) * 1000
    trace = AIObservabilityTrace(
        correlation_id=f"cmd-{audit.id}",
        step_name="ENKRYPT_SAFETY_CHECK",
        latency_ms=elapsed,
        status="success" if status == "ALLOWED" else "blocked",
        metadata_json=json.dumps({
            "command": command[:200],
            "risk_score": risk_score,
            "result": status,
        }),
    )
    db.add(trace)
    db.commit()

    return {
        "command": command,
        "status": status,
        "risk_score": risk_score,
        "risk_assessment": assessment,
        "execution_output": execution_output,
        "audit_id": audit.id,
    }


def validate_audit_chain(db: Session) -> dict:
    """Validate the integrity of the tamper-evident audit chain."""
    audits = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
    if not audits:
        return {"valid": True, "message": "No audit entries to validate.", "count": 0}

    prev_hash = "genesis"
    for audit in audits:
        expected_hash = compute_chain_hash(
            f"{audit.command_checked}:{audit.status}:{audit.risk_score}",
            prev_hash,
        )
        if audit.hash != expected_hash:
            return {
                "valid": False,
                "message": f"Chain broken at audit #{audit.id}. Expected {expected_hash[:16]}... got {(audit.hash or 'null')[:16]}...",
                "count": len(audits),
            }
        prev_hash = audit.hash

    return {
        "valid": True,
        "message": "Blockchain ledger integrity verified successfully.",
        "count": len(audits),
    }


def _simulate_command_execution(command: str) -> str:
    """Simulate command execution for demo/hackathon purposes."""
    cmd_lower = command.lower()

    if "kubectl rollout restart" in cmd_lower:
        deploy = command.split("/")[-1] if "/" in command else "unknown"
        return f"deployment.apps/{deploy} restarted successfully"
    elif "kubectl scale" in cmd_lower:
        return "deployment scaled successfully"
    elif "kubectl get" in cmd_lower:
        return "NAME                    READY   STATUS    RESTARTS   AGE\napi-gateway-7d8f6c5    1/1     Running   0          4h"
    elif "kubectl describe" in cmd_lower:
        return "Name: api-gateway\nNamespace: production\nStatus: Running\nIP: 10.244.0.15"
    elif "kubectl logs" in cmd_lower:
        return "[2024-01-15T10:30:00Z] INFO: Service healthy\n[2024-01-15T10:30:05Z] INFO: Request processed in 45ms"
    elif "helm" in cmd_lower:
        return "NAME\tNAMESPACE\tREVISION\tSTATUS\tCHART\nsentinelflow\tdefault\t3\tdeployed\tsentinelflow-1.2.0"
    else:
        return f"[SIMULATED] Command executed: {command[:100]}"
