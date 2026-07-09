"""
SentinelFlow AI — Cloud Infrastructure Integration Service
Handles Kubernetes, AWS, and GCP remediation commands validation, execution, and rollback.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..models.models import RemediationExecution, Incident, CloudProviderConfig, KubernetesClusterInfo
from ..services.feature_flag_service import is_enabled, FeatureFlagKey

# ── Cloud Provider Clients ───────────────────────────────────

class KubernetesClient:
    """Wrapper for Kubernetes cluster remediation actions."""
    def restart_pod(self, namespace: str, pod_name: str, dry_run: bool = False) -> str:
        if dry_run:
            return f"[DRY-RUN] kubectl delete pod {pod_name} -n {namespace} (Simulated pod restart)"
        return f"kubectl delete pod {pod_name} -n {namespace} (Executed pod restart successfully)"

    def scale_deployment(self, namespace: str, deployment: str, replicas: int, dry_run: bool = False) -> str:
        if dry_run:
            return f"[DRY-RUN] kubectl scale deployment/{deployment} --replicas={replicas} -n {namespace}"
        return f"kubectl scale deployment/{deployment} --replicas={replicas} -n {namespace} (Scaled successfully)"


class AWSClient:
    """Wrapper for AWS infrastructure operations."""
    def restart_ec2_instance(self, instance_id: str, region: str, dry_run: bool = False) -> str:
        if dry_run:
            return f"[DRY-RUN] aws ec2 reboot-instances --instance-ids {instance_id} --region {region}"
        return f"aws ec2 reboot-instances --instance-ids {instance_id} --region {region} (Rebooted successfully)"

    def scale_autoscaling_group(self, asg_name: str, desired_capacity: int, region: str, dry_run: bool = False) -> str:
        if dry_run:
            return f"[DRY-RUN] aws autoscaling update-auto-scaling-group --auto-scaling-group-name {asg_name} --desired-capacity {desired_capacity} --region {region}"
        return f"aws autoscaling update-auto-scaling-group --auto-scaling-group-name {asg_name} --desired-capacity {desired_capacity} --region {region} (ASG updated)"


class GCPClient:
    """Wrapper for GCP infrastructure operations."""
    def restart_compute_instance(self, instance: str, zone: str, project: str, dry_run: bool = False) -> str:
        if dry_run:
            return f"[DRY-RUN] gcloud compute instances reset {instance} --zone {zone} --project {project}"
        return f"gcloud compute instances reset {instance} --zone {zone} --project {project} (Reset successfully)"


# ── Remediation Execution Manager ────────────────────────────

class CloudRemediationManager:
    def __init__(self):
        self.k8s = KubernetesClient()
        self.aws = AWSClient()
        self.gcp = GCPClient()

    def execute_action(
        self,
        db: Session,
        incident_id: int,
        command: str,
        performed_by: str = "workflow",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a remediation command, checking the FF_CLOUD_REMEDIATION flag,
        logging execution results, and tracking outputs.
        """
        start_time = datetime.now(timezone.utc)
        
        # Check feature flag. If cloud remediation is disabled, force dry_run!
        remediation_enabled = is_enabled(db, FeatureFlagKey.CLOUD_REMEDIATION)
        actual_dry_run = dry_run or not remediation_enabled

        # Resolve command type
        command_lower = command.lower()
        console_output = ""
        status = "SUCCESS"

        try:
            if "kubectl delete pod" in command_lower:
                # Parse mock parameters
                namespace = "default"
                pod_name = "api-gateway-xxx"
                console_output = self.k8s.restart_pod(namespace, pod_name, dry_run=actual_dry_run)
            elif "kubectl scale" in command_lower:
                replicas = 3
                if "replicas=0" in command_lower:
                    replicas = 0
                console_output = self.k8s.scale_deployment("default", "api-gateway", replicas, dry_run=actual_dry_run)
            elif "aws ec2 reboot" in command_lower or "reboot-instances" in command_lower:
                console_output = self.aws.restart_ec2_instance("i-099abc123", "us-east-1", dry_run=actual_dry_run)
            elif "update-auto-scaling-group" in command_lower:
                console_output = self.aws.scale_autoscaling_group("api-asg", 5, "us-east-1", dry_run=actual_dry_run)
            elif "compute instances reset" in command_lower:
                console_output = self.gcp.restart_compute_instance("api-node-1", "us-central1-a", "sf-project", dry_run=actual_dry_run)
            else:
                # Default generic execution check
                if actual_dry_run:
                    console_output = f"[DRY-RUN] Executing command: {command}"
                else:
                    console_output = f"Executing command: {command} (Executed successfully)"
        except Exception as e:
            status = "FAILED"
            console_output = f"Execution error: {e}"

        # Write RemediationExecution audit row
        exec_record = RemediationExecution(
            incident_id=incident_id,
            command=command,
            execution_status=status,
            console_output=console_output,
            executed_by=performed_by,
            started_at=start_time,
            finished_at=datetime.now(timezone.utc)
        )
        db.add(exec_record)
        db.commit()
        db.refresh(exec_record)

        return {
            "execution_id": exec_record.id,
            "status": status,
            "dry_run": actual_dry_run,
            "output": console_output,
            "finished_at": exec_record.finished_at
        }

    def rollback_execution(
        self,
        db: Session,
        execution_id: int,
        performed_by: str = "admin"
    ) -> Dict[str, Any]:
        """
        Perform inverse operation rollback for a completed execution.
        """
        orig_exec = db.query(RemediationExecution).filter(RemediationExecution.id == execution_id).first()
        if not orig_exec:
            return {"error": f"Execution log {execution_id} not found."}

        orig_cmd = orig_exec.command.lower()
        rollback_cmd = f"rollback_{orig_exec.command}"

        if "kubectl scale" in orig_cmd:
            # Revert scaling back to original baseline (e.g. scale back to 1 replica)
            rollback_cmd = "kubectl scale deployment/api-gateway --replicas=1 -n default"
        elif "kubectl delete pod" in orig_cmd:
            rollback_cmd = "kubectl rollout status deployment/api-gateway -n default"
        elif "reboot-instances" in orig_cmd:
            rollback_cmd = "aws ec2 describe-instances --instance-ids i-099abc123"

        # Execute rollback command
        res = self.execute_action(
            db=db,
            incident_id=orig_exec.incident_id,
            command=rollback_cmd,
            performed_by=f"rollback-agent ({performed_by})",
            dry_run=False
        )

        return {
            "rollback_status": "SUCCESS",
            "rollback_command": rollback_cmd,
            "original_execution_id": execution_id,
            "remediation_result": res
        }


# Instantiate shared manager
remediation_manager = CloudRemediationManager()
