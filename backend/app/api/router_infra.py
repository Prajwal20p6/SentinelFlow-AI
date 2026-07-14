"""
SentinelFlow AI — Infrastructure & Safety API Router
Cluster topology, guarded command execution, audit trail management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..middleware.auth import get_current_user, require_role
from ..models.models import User, AuditTrail
from ..schemas.schemas import (
    CommandExecuteRequest, CommandExecuteResponse,
    AuditTrailResponse, ClusterTopologyResponse,
)
from ..services.safety_service import execute_guarded_command, validate_audit_chain
from ..services.simulator_service import get_cluster_topology

router = APIRouter(prefix="/infra", tags=["Infrastructure"])


@router.get("/topology", response_model=ClusterTopologyResponse)
def get_topology(current_user: User = Depends(get_current_user)):
    """Get the simulated Kubernetes cluster topology."""
    return get_cluster_topology()


@router.post("/execute-command", response_model=CommandExecuteResponse)
async def execute_command(
    body: CommandExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """
    Execute a guarded infrastructure command.
    Evaluates safety via Enkrypt AI, writes tamper-evident audit log.
    """
    from ..core.config import get_settings
    settings = get_settings()

    if settings.ENKRYPTAI_ENABLED:
        from ..services.enkrypt_service import EnkryptSafetyService
        enkrypt = EnkryptSafetyService(
            api_key=settings.ENKRYPTAI_API_KEY,
            base_url=settings.ENKRYPTAI_BASE_URL
        )
        try:
            validation = await enkrypt.validate_command(
                command=body.command,
                context={
                    "incident_id": body.incident_id,
                }
            )
            if not validation.get("is_safe", True):
                import json
                raise HTTPException(
                    status_code=403,
                    detail=json.dumps({
                        "message": "Command blocked by Enkrypt AI guardrails",
                        "risk_score": validation.get("risk_score", 0.99),
                        "violations": validation.get("violations", [])
                    })
                )
        except HTTPException:
            raise
        except Exception as e:
            # Fallback to keep cluster resilient when safety API is down
            from ..core.observability import logger
            logger.warning(f"Enkrypt API unreachable during command execution check: {str(e)}")

    result = execute_guarded_command(
        db=db,
        command=body.command,
        incident_id=body.incident_id,
        performed_by=current_user.email,
    )
    return CommandExecuteResponse(**result)


@router.get("/audit-trail")
def get_audit_trail(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the tamper-evident audit trail."""
    audits = (
        db.query(AuditTrail)
        .order_by(AuditTrail.timestamp.desc())
        .limit(limit)
        .all()
    )
    return {
        "audit_entries": [AuditTrailResponse.model_validate(a) for a in audits],
        "count": len(audits),
    }


@router.get("/audit-trail/verify")
def verify_audit_chain(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Verify the cryptographic integrity of the audit chain."""
    result = validate_audit_chain(db)
    return result


@router.post("/audit-trail/archive")
def archive_audit_trail(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Archive the audit trail to simulated S3 storage."""
    import json
    from datetime import datetime, timezone

    audits = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
    if not audits:
        return {"message": "No audit entries to archive."}

    archive_data = [
        {
            "id": a.id,
            "command": a.command_checked,
            "status": a.status,
            "risk_score": a.risk_score,
            "hash": a.hash,
            "prev_hash": a.prev_hash,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        }
        for a in audits
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    s3_uri = f"s3://sentinelflow-audit-ledger/archive_{timestamp}.json"

    return {
        "message": f"Archived {len(archive_data)} audit entries.",
        "s3_uri": s3_uri,
        "entry_count": len(archive_data),
        "serialized_bytes": len(json.dumps(archive_data)),
    }


@router.post("/remediations/{execution_id}/rollback")
def rollback_remediation(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Roll back a previous remediation execution. Restricted to Admin."""
    from ..services.cloud_service import remediation_manager
    res = remediation_manager.rollback_execution(db, execution_id, performed_by=current_user.email)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
