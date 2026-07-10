from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from ..core.config import get_settings
from ..services.enkrypt_service import EnkryptSafetyService

router = APIRouter(prefix="/security", tags=["Security"])
settings = get_settings()

class ValidateCommandRequest(BaseModel):
    command: str
    context: Optional[Dict] = None

@router.post("/validate-command")
async def validate_command_endpoint(body: ValidateCommandRequest):
    """
    Endpoint for Mastra workflow to validate command safety via Enkrypt AI.
    """
    if not settings.ENKRYPTAI_ENABLED:
        return {
            "is_safe": True,
            "risk_score": 0.0,
            "violations": [],
            "message": "Enkrypt AI is disabled"
        }
        
    try:
        enkrypt = EnkryptSafetyService(
            api_key=settings.ENKRYPTAI_API_KEY,
            base_url=settings.ENKRYPTAI_BASE_URL
        )
        
        result = await enkrypt.validate_command(
            command=body.command,
            context=body.context
        )
        return result
    except Exception as e:
        # Graceful fallback: allow with log if API is unreachable
        return {
            "is_safe": True,
            "risk_score": 0.3,
            "violations": [],
            "message": f"Validation system connection warning: {str(e)}"
        }
