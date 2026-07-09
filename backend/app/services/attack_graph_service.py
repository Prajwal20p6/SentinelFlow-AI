"""
SentinelFlow AI — Attack Graph Service
Generates nodes and edges representing lateral compromises, MITRE technique tags, dwell times, and exposure scope.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

class AttackGraphService:
    """Generates structured DAG representations of lateral compromises across nodes and edges."""

    @staticmethod
    def generate_attack_graph(incident_type: str, severity: str) -> Dict[str, Any]:
        """
        Dynamically synthesize a realistic lateral compromise path graph mapping
        compromised assets (Users, Devices, Services, Data) with MITRE mappings and dwell times.
        """
        base_time = datetime.utcnow() - timedelta(minutes=45)
        
        # We model dynamic paths depending on severity & incident type (e.g., CPU vs OOM vs Security Breach)
        is_breach = "breach" in incident_type.lower() or "security" in incident_type.lower() or severity == "CRITICAL"
        
        # Build Nodes
        nodes = [
            # Initial Access Point
            {
                "id": "node_email",
                "type": "user",
                "label": "Email Gateway",
                "details": {
                    "username": "mail-receiver@company.com",
                    "department": "Sales & Support",
                    "access_level": "Standard User",
                    "status": "compromised",
                    "timestamp": base_time.isoformat() + "Z"
                }
            },
            {
                "id": "node_user_workstation",
                "type": "device",
                "label": "SRE Laptop-X40",
                "details": {
                    "name": "SRE-WORKSTATION-X40",
                    "device_type": "workstation",
                    "status": "compromised",
                    "last_activity": (base_time + timedelta(minutes=5)).isoformat() + "Z"
                }
            }
        ]

        if is_breach:
            nodes.extend([
                {
                    "id": "node_domain_controller",
                    "type": "service",
                    "label": "Active Directory DC",
                    "details": {
                        "name": "Active Directory Controller",
                        "auth_status": "compromised_session",
                        "data_accessed": "Kerberos TGT tickets",
                        "status": "compromised"
                    }
                },
                {
                    "id": "node_production_db",
                    "type": "device",
                    "label": "Prod DB Host",
                    "details": {
                        "name": "prod-postgres-db-primary",
                        "device_type": "server",
                        "status": "compromised",
                        "last_activity": (base_time + timedelta(minutes=25)).isoformat() + "Z"
                    }
                },
                {
                    "id": "node_pii_data",
                    "type": "data",
                    "label": "Customer PII Database",
                    "details": {
                        "name": "customer_pii_production",
                        "sensitivity": "Critical",
                        "access_timestamp": (base_time + timedelta(minutes=32)).isoformat() + "Z",
                        "exfiltration_status": "exfiltrated"
                    }
                }
            ])
        else:
            # Non-breach (e.g. performance issue, normal Kubernetes crash, or warning incident)
            nodes.extend([
                {
                    "id": "node_kubernetes_apiserver",
                    "type": "service",
                    "label": "Kubernetes API Server",
                    "details": {
                        "name": "kube-apiserver",
                        "auth_status": "authenticated_read_only",
                        "data_accessed": "Namespace quota configuration",
                        "status": "suspicious"
                    }
                },
                {
                    "id": "node_k8s_worker_node",
                    "type": "device",
                    "label": "K8s Worker Node 03",
                    "details": {
                        "name": "worker-node-03",
                        "device_type": "server",
                        "status": "suspicious",
                        "last_activity": (base_time + timedelta(minutes=15)).isoformat() + "Z"
                    }
                },
                {
                    "id": "node_logs_data",
                    "type": "data",
                    "label": "Application Logs Store",
                    "details": {
                        "name": "stdout_logs_archive",
                        "sensitivity": "Low",
                        "access_timestamp": (base_time + timedelta(minutes=20)).isoformat() + "Z",
                        "exfiltration_status": "none"
                    }
                }
            ])

        # Build Edges with MITRE labels
        edges = []
        if is_breach:
            edges = [
                {
                    "source": "node_email",
                    "target": "node_user_workstation",
                    "phase": "initial_access",
                    "mitre_technique": "T1566 (Phishing Email)",
                    "dwell_time_mins": 5,
                    "timestamp": (base_time + timedelta(minutes=5)).isoformat() + "Z"
                },
                {
                    "source": "node_user_workstation",
                    "target": "node_domain_controller",
                    "phase": "lateral_movement",
                    "mitre_technique": "T1078 (Valid Accounts)",
                    "dwell_time_mins": 10,
                    "timestamp": (base_time + timedelta(minutes=15)).isoformat() + "Z"
                },
                {
                    "source": "node_domain_controller",
                    "target": "node_production_db",
                    "phase": "lateral_movement",
                    "mitre_technique": "T1570 (Lateral Tool Transfer)",
                    "dwell_time_mins": 10,
                    "timestamp": (base_time + timedelta(minutes=25)).isoformat() + "Z"
                },
                {
                    "source": "node_production_db",
                    "target": "node_pii_data",
                    "phase": "exfiltration",
                    "mitre_technique": "T1020 (Automated Exfiltration)",
                    "dwell_time_mins": 7,
                    "timestamp": (base_time + timedelta(minutes=32)).isoformat() + "Z"
                }
            ]
        else:
            edges = [
                {
                    "source": "node_email",
                    "target": "node_user_workstation",
                    "phase": "initial_access",
                    "mitre_technique": "T1566.002 (Phishing Link)",
                    "dwell_time_mins": 5,
                    "timestamp": (base_time + timedelta(minutes=5)).isoformat() + "Z"
                },
                {
                    "source": "node_user_workstation",
                    "target": "node_kubernetes_apiserver",
                    "phase": "execution",
                    "mitre_technique": "T1059 (Command & Scripting Interpreter)",
                    "dwell_time_mins": 5,
                    "timestamp": (base_time + timedelta(minutes=10)).isoformat() + "Z"
                },
                {
                    "source": "node_kubernetes_apiserver",
                    "target": "node_k8s_worker_node",
                    "phase": "lateral_movement",
                    "mitre_technique": "T1021.002 (SMB/SSH Lateral Services)",
                    "dwell_time_mins": 5,
                    "timestamp": (base_time + timedelta(minutes=15)).isoformat() + "Z"
                },
                {
                    "source": "node_k8s_worker_node",
                    "target": "node_logs_data",
                    "phase": "exfiltration",
                    "mitre_technique": "T1029 (Scheduled Transfer)",
                    "dwell_time_mins": 5,
                    "timestamp": (base_time + timedelta(minutes=20)).isoformat() + "Z"
                }
            ]

        # Calculate exposure summaries
        compromised_users = sum(1 for n in nodes if n["type"] == "user" and n["details"].get("status") == "compromised")
        compromised_devices = sum(1 for n in nodes if n["type"] == "device" and n["details"].get("status") == "compromised")
        compromised_services = sum(1 for n in nodes if n["type"] == "service" and n["details"].get("status") == "compromised")
        data_nodes = [n for n in nodes if n["type"] == "data"]
        data_accessed_count = len(data_nodes)

        # Build final graph payload
        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "compromised_users": compromised_users,
                "compromised_devices": compromised_devices,
                "compromised_services": compromised_services,
                "data_sources_compromised": data_accessed_count,
                "estimated_exposure_scope": "Moderate" if is_breach else "Low",
                "dwell_time_mins": sum(e["dwell_time_mins"] for e in edges),
                "risk_index": 85 if is_breach else 35,
                "critical_path": [e["source"] for e in edges] + [edges[-1]["target"]] if edges else []
            }
        }
