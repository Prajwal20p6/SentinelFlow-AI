from enkryptai import EnkryptAI
from enkryptai.models import GuardRailRequest, GuardRailType
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class EnkryptSafetyService:
    """Official Enkrypt AI SDK integration"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.enkryptai.com"):
        # Initialize official Enkrypt AI client
        self.client = EnkryptAI(
            api_key=api_key,
            base_url=base_url
        )
    
    async def validate_prompt(self, prompt: str, context: Optional[Dict] = None) -> Dict:
        """Validate AI prompt using official Enkrypt AI guardrails"""
        try:
            request = GuardRailRequest(
                content=prompt,
                guard_rail_type=GuardRailType.PROMPT_INJECTION,
                context=context or {}
            )
            
            result = await self.client.validate(request)
            
            return {
                "is_safe": result.is_safe,
                "risk_score": result.risk_score,
                "violations": result.violations or [],
                "message": result.message
            }
        except Exception as e:
            logger.error(f"Enkrypt prompt validation failed: {e}")
            raise
    
    async def validate_command(self, command: str, context: Optional[Dict] = None) -> Dict:
        """Validate execution command using official Enkrypt AI guardrails"""
        try:
            request = GuardRailRequest(
                content=command,
                guard_rail_type=GuardRailType.COMMAND_INJECTION,
                context=context or {}
            )
            
            result = await self.client.validate(request)
            
            return {
                "is_safe": result.is_safe,
                "risk_score": result.risk_score,
                "violations": result.violations or [],
                "message": result.message
            }
        except Exception as e:
            logger.error(f"Enkrypt command validation failed: {e}")
            raise
    
    async def validate_output(self, output: str, context: Optional[Dict] = None) -> Dict:
        """Validate AI output using official Enkrypt AI guardrails"""
        try:
            request = GuardRailRequest(
                content=output,
                guard_rail_type=GuardRailType.SENSITIVE_DATA,
                context=context or {}
            )
            
            result = await self.client.validate(request)
            
            return {
                "is_safe": result.is_safe,
                "risk_score": result.risk_score,
                "violations": result.violations or [],
                "redacted_content": result.redacted_content or output,
                "message": result.message
            }
        except Exception as e:
            logger.error(f"Enkrypt output validation failed: {e}")
            raise
