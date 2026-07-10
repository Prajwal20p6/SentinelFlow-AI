from typing import Dict, Any, Optional
from enkryptai_sdk.guardrails import GuardrailsClient
from enkryptai_sdk.config import GuardrailsConfig
from .models import GuardRailRequest, GuardRailType

class EnkryptAIResult:
    def __init__(self, is_safe: bool, risk_score: float, violations: list, message: str, redacted_content: str = ""):
        self.is_safe = is_safe
        self.risk_score = risk_score
        self.violations = violations
        self.message = message
        self.redacted_content = redacted_content

class EnkryptAI:
    """Adapter class wrapping the official GuardrailsClient to match target API specification."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.enkryptai.com:443"):
        self.client = GuardrailsClient(
            api_key=api_key,
            base_url=base_url
        )

    async def validate(self, request: GuardRailRequest) -> EnkryptAIResult:
        """Validate request using official Enkrypt AI Guardrails Client"""
        # Determine the appropriate config based on GuardRailType
        if request.guard_rail_type == GuardRailType.PROMPT_INJECTION:
            config = GuardrailsConfig.injection_attack()
        elif request.guard_rail_type == GuardRailType.COMMAND_INJECTION:
            # Check command injection using policy violation
            config = GuardrailsConfig.policy_violation(
                policy_text="Do not allow any command injection attempts, illegal operations, shell escapes or unauthorized scripts."
            )
        elif request.guard_rail_type == GuardRailType.SENSITIVE_DATA:
            config = GuardrailsConfig.pii()
        else:
            config = GuardrailsConfig.injection_attack()

        try:
            # Call the real SDK's detect method
            # Note: The detect call is synchronous in the SDK, so we run it directly or wrap it.
            # Running directly is fine since we are in an async function.
            response = self.client.detect(
                text=request.content,
                config=config
            )
            
            is_safe = response.is_safe()
            violations = response.get_violations()
            
            # Extract highest risk score from summary
            risk_score = 0.0
            if not is_safe:
                summary = response.summary.to_dict()
                for val in summary.values():
                    if isinstance(val, (int, float)) and val > risk_score:
                        risk_score = float(val)
                if risk_score == 0.0:
                    risk_score = 0.99  # Default high score for violations
                    
            message = response.result_message or ("Blocked by Enkrypt AI" if not is_safe else "Passed Enkrypt AI validation")
            
            return EnkryptAIResult(
                is_safe=is_safe,
                risk_score=risk_score,
                violations=violations,
                message=message,
                redacted_content=request.content
            )
        except Exception as e:
            # Re-raise or wrap SDK errors
            raise RuntimeError(f"Enkrypt AI service query error: {str(e)}")
