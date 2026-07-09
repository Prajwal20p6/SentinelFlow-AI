"""
SentinelFlow AI — MITRE ATT&CK Mapping & Timeline Builder Service
Provides lookup enums, causal sorting, kill chain phase groupings, and transition analytics.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..models.models import TimelineEvent, Incident
from .incident_service import add_timeline_event

# ── MITRE ATT&CK Technique Catalog ────────────────────────────
MITRE_ATTACK_CATALOG = {
    # Initial Access
    "T1566": {"name": "Phishing", "tactic": "Initial Access", "description": "Adversaries may send phishing messages to gain access to system resources."},
    "T1566.001": {"name": "Phishing: Spearphishing Attachment", "tactic": "Initial Access", "description": "Spearphishing with malicious attachments."},
    "T1190": {"name": "Exploit Public-Facing Application", "tactic": "Initial Access", "description": "Exploiting security bugs in internet-facing applications."},
    "T1078": {"name": "Valid Accounts", "tactic": "Initial Access", "description": "Using compromised credentials to gain access."},
    # Execution
    "T1204": {"name": "User Execution", "tactic": "Execution", "description": "User clicks or runs a malicious attachment or link."},
    "T1204.002": {"name": "User Execution: Malicious File", "tactic": "Execution", "description": "User opens a malicious file."},
    "T1059": {"name": "Command and Scripting Interpreter", "tactic": "Execution", "description": "Adversaries may use interpreters to execute commands."},
    "T1059.001": {"name": "PowerShell", "tactic": "Execution", "description": "PowerShell scripts execution."},
    "T1203": {"name": "Exploitation for Client Execution", "tactic": "Execution", "description": "Exploitation of vulnerabilities in client-side software."},
    # Persistence
    "T1543": {"name": "Create or Modify System Process", "tactic": "Persistence", "description": "Creating services or modify system parameters."},
    "T1543.003": {"name": "Windows Service", "tactic": "Persistence", "description": "Create or modify Windows services."},
    "T1098": {"name": "Account Manipulation", "tactic": "Persistence", "description": "Manipulating system accounts to maintain access."},
    # Privilege Escalation
    "T1548": {"name": "Abuse Elevation Control Mechanism", "tactic": "Privilege Escalation", "description": "Bypassing Elevation configurations (UAC/sudo)."},
    "T1068": {"name": "Exploitation for Privilege Escalation", "tactic": "Privilege Escalation", "description": "Exploiting OS bugs to elevate privilege."},
    # Defense Evasion
    "T1562": {"name": "Impair Defenses", "tactic": "Defense Evasion", "description": "Disabling security tools, firewalls, or logging engines."},
    "T1070": {"name": "Indicator Removal", "tactic": "Defense Evasion", "description": "Clearing audit logs, temporary files, or process histories."},
    # Credential Access
    "T1003": {"name": "OS Credential Dumping", "tactic": "Credential Access", "description": "Dumping credentials from host processes memory."},
    "T1110": {"name": "Brute Force", "tactic": "Credential Access", "description": "Brute-force password guessing attempts."},
    # Discovery
    "T1087": {"name": "Account Discovery", "tactic": "Discovery", "description": "Enumerating system accounts and local groups."},
    "T1046": {"name": "Network Service Discovery", "tactic": "Discovery", "description": "Port scanning and network service checks."},
    # Lateral Movement
    "T1021": {"name": "Remote Services", "tactic": "Lateral Movement", "description": "Connecting to remote service endpoints."},
    "T1021.006": {"name": "Windows Remote Management", "tactic": "Lateral Movement", "description": "WinRM administration connections."},
    "T1210": {"name": "Exploitation of Remote Services", "tactic": "Lateral Movement", "description": "Exploitation of remote vulnerabilities to pivot."},
    # Collection
    "T1114": {"name": "Email Collection", "tactic": "Collection", "description": "Accessing local or remote mailboxes to collect sensitive info."},
    "T1005": {"name": "Data from Local System", "tactic": "Collection", "description": "Collecting files from system directories."},
    # Exfiltration
    "T1048": {"name": "Exfiltration Over Alternative Protocol", "tactic": "Exfiltration", "description": "Exfiltrating files over DNS, HTTP, or custom connection channels."},
    # Impact
    "T1485": {"name": "Data Destruction", "tactic": "Impact", "description": "Deleting data files from storage disks."},
    "T1486": {"name": "Data Encrypted for Impact", "tactic": "Impact", "description": "Ransomware encryption loops."}
}

KILL_CHAIN_ORDER = [
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Defense Evasion",
    "Credential Access",
    "Discovery",
    "Lateral Movement",
    "Collection",
    "Exfiltration",
    "Impact"
]


# ── Mappings Helpers ──────────────────────────────────────────

def lookup_mitre_technique(technique_id: str) -> Optional[Dict[str, str]]:
    """Retrieve details (name, tactic, description) for a MITRE technique ID."""
    return MITRE_ATTACK_CATALOG.get(technique_id)


def map_incident_to_mitre(metric_type: str) -> Optional[str]:
    """Map a telemetry alert anomaly to a standard MITRE technique ID."""
    mappings = {
        "UNAUTHORIZED_ACCESS": "T1078",     # Valid Accounts
        "CPU_SPIKE": "T1059.001",           # PowerShell / Command Execution
        "MEMORY_EXHAUSTION": "T1562",       # Impair Defenses / Resource exhaustion
        "DISK_FULL": "T1485",               # Data Destruction / Storage fill
        "HIGH_LATENCY": "T1210",            # Exploitation of Remote Services
        "ERROR_RATE_SPIKE": "T1021",        # Remote Services connection delay
    }
    return mappings.get(metric_type)


# ── Advanced Timeline Builders ────────────────────────────────

def get_mitre_tactic_index(tactic: str) -> int:
    """Returns the position index of a MITRE tactic in the standard kill chain."""
    try:
        return KILL_CHAIN_ORDER.index(tactic)
    except ValueError:
        return 99


def build_causal_timeline(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """
    Sorts timeline events based on the parent-child causal chain.
    If no causal link exists, falls back to chronological order (timestamp).
    """
    if not events:
        return []

    # Map events by ID
    event_map = {e.id: e for e in events}
    
    # Track children for each parent
    children_map = {}
    for e in events:
        if e.parent_event_id:
            children_map.setdefault(e.parent_event_id, []).append(e)

    # Sort siblings by timestamp
    for pid in children_map:
        children_map[pid].sort(key=lambda x: x.timestamp or datetime.min)

    # Find root events (events with no parent or parent not in current list)
    roots = []
    for e in events:
        if not e.parent_event_id or e.parent_event_id not in event_map:
            roots.append(e)
    roots.sort(key=lambda x: x.timestamp or datetime.min)

    ordered = []

    def traverse(node: TimelineEvent):
        ordered.append(node)
        children = children_map.get(node.id, [])
        for child in children:
            traverse(child)

    for r in roots:
        traverse(r)

    # Any orphaned events that somehow weren't added
    added_ids = {e.id for e in ordered}
    for e in events:
        if e.id not in added_ids:
            ordered.append(e)

    return ordered


def build_kill_chain_timeline(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
    """Groups timeline events by their MITRE ATT&CK kill chain tactic."""
    grouped = {tactic: [] for tactic in KILL_CHAIN_ORDER}
    grouped["Other Processes / Logs"] = []

    for e in events:
        tactic = None
        if e.mitre_technique:
            tech = lookup_mitre_technique(e.mitre_technique)
            if tech:
                tactic = tech["tactic"]
        
        if tactic in grouped:
            grouped[tactic].append(e)
        else:
            grouped["Other Processes / Logs"].append(e)

    result = []
    for tactic, evts in grouped.items():
        if evts:
            evts_data = []
            for ev in evts:
                tech = lookup_mitre_technique(ev.mitre_technique) if ev.mitre_technique else None
                evts_data.append({
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "title": ev.title,
                    "description": ev.description,
                    "actor": ev.actor,
                    "severity": ev.event_severity,
                    "mitre_technique": ev.mitre_technique,
                    "mitre_details": tech,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None
                })
            result.append({
                "tactic": tactic,
                "events": evts_data
            })
    return result


def analyze_timeline_forensics(events: List[TimelineEvent]) -> Dict[str, Any]:
    """Computes dwell time, phase transitions, and suggests missing links."""
    if not events:
        return {"dwell_time_seconds": 0.0, "transitions": [], "missing_suggestions": []}

    # Clean sorting by timestamp to find chronological sequence
    sorted_events = sorted(events, key=lambda x: x.timestamp or datetime.min)
    first_event = sorted_events[0]
    last_event = sorted_events[-1]

    # Dwell Time
    dwell_time = 0.0
    if first_event.timestamp and last_event.timestamp:
        dwell_time = (last_event.timestamp - first_event.timestamp).total_seconds()

    # Track phase transitions
    transitions = []
    active_phases = []
    for e in sorted_events:
        if e.mitre_technique:
            tech = lookup_mitre_technique(e.mitre_technique)
            if tech:
                tactic = tech["tactic"]
                if not active_phases or active_phases[-1]["tactic"] != tactic:
                    active_phases.append({
                        "tactic": tactic,
                        "timestamp": e.timestamp
                    })

    for i in range(len(active_phases) - 1):
        p1 = active_phases[i]
        p2 = active_phases[i+1]
        elapsed = 0.0
        if p1["timestamp"] and p2["timestamp"]:
            elapsed = (p2["timestamp"] - p1["timestamp"]).total_seconds()
        transitions.append({
            "from_tactic": p1["tactic"],
            "to_tactic": p2["tactic"],
            "elapsed_seconds": elapsed
        })

    # Missing Phase Suggestions
    detected_tactics = {p["tactic"] for p in active_phases}
    suggestions = []
    
    if "Initial Access" not in detected_tactics:
        suggestions.append("Initial Access vectors not identified. Review ingress router and firewall logs.")
    if "Execution" not in detected_tactics:
        suggestions.append("Execution stage logs are missing. Check auditd/command interpreter records.")
    if "Credential Access" not in detected_tactics:
        suggestions.append("No credential dump indicator. Verify PAM or active directory account locks.")
    if "Exfiltration" not in detected_tactics:
        suggestions.append("Exfiltration tracking is offline. Enable network flow alerts.")

    return {
        "dwell_time_seconds": dwell_time,
        "transitions": transitions,
        "missing_suggestions": suggestions
    }


# ── Phishing Scenario Simulation ──────────────────────────────

def seed_phishing_scenario(db: Session, incident_id: int) -> List[TimelineEvent]:
    """Generates a complete E2E MITRE ATT&CK mapped timeline simulation representing email phishing escalation."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return []

    # Clean old timeline
    db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident_id).delete()
    db.commit()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    events_data = [
        {
            "event_type": "DETECTED",
            "title": "Email gateway: Spearphishing attachment flagged",
            "description": "Incoming message containing invoice_details.xlsm received from external relay.",
            "actor": "email-gateway",
            "mitre_technique": "T1566.001",
            "source_system": "EmailGateway",
            "event_severity": "MEDIUM",
            "time_offset": 0
        },
        {
            "event_type": "ANALYZING",
            "title": "User Execution of Malicious Attachment",
            "description": "User opened attachment invoice_details.xlsm triggering macro execution.",
            "actor": "user-agent",
            "mitre_technique": "T1204.002",
            "source_system": "Syslog",
            "event_severity": "HIGH",
            "time_offset": 120
        },
        {
            "event_type": "ANALYZING",
            "title": "PowerShell spawn interpreter command run",
            "description": "PowerShell script spawned by Excel child process trying to connect outbound.",
            "actor": "excel.exe",
            "mitre_technique": "T1059.001",
            "source_system": "Auditd",
            "event_severity": "HIGH",
            "time_offset": 180
        },
        {
            "event_type": "ANALYZING",
            "title": "OS Credential Dumping via LSASS memory",
            "description": "Attempted read access on LSASS memory to extract local admin credentials.",
            "actor": "mimikatz.exe",
            "mitre_technique": "T1003",
            "source_system": "Syslog",
            "event_severity": "CRITICAL",
            "time_offset": 300
        },
        {
            "event_type": "ANALYZING",
            "title": "WinRM connection to application node server",
            "description": "Lateral movement connection established to production-node using dumped credentials.",
            "actor": "admin-account",
            "mitre_technique": "T1021.006",
            "source_system": "ActiveDirectory",
            "event_severity": "CRITICAL",
            "time_offset": 480
        },
        {
            "event_type": "ANALYZING",
            "title": "Database backup collection dump",
            "description": "Database archive compiled under /tmp using system utilities.",
            "actor": "backup-util",
            "mitre_technique": "T1005",
            "source_system": "DatabaseMonitor",
            "event_severity": "HIGH",
            "time_offset": 600
        },
        {
            "event_type": "EXECUTING",
            "title": "Exfiltration over custom HTTPS protocol",
            "description": "Database backup archive transferred to external server 185.220.101.5.",
            "actor": "curl.exe",
            "mitre_technique": "T1048",
            "source_system": "Zeek-IDS",
            "event_severity": "CRITICAL",
            "time_offset": 900
        }
    ]

    timeline_events = []
    parent_id = None

    for data in events_data:
        evt = TimelineEvent(
            incident_id=incident_id,
            event_type=data["event_type"],
            title=data["title"],
            description=data["description"],
            actor=data["actor"],
            mitre_technique=data["mitre_technique"],
            source_system=data["source_system"],
            event_severity=data["event_severity"],
            parent_event_id=parent_id,
            timestamp=base_time + timedelta(seconds=data["time_offset"])
        )
        db.add(evt)
        db.commit()
        db.refresh(evt)
        timeline_events.append(evt)
        parent_id = evt.id

    return timeline_events
