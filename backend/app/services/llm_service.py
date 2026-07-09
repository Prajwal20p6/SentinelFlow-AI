"""
SentinelFlow AI — Multi-Provider LLM Abstraction & Failover Layer
Supports OpenAI, Anthropic, Gemini, and high-fidelity Simulation fallbacks.
"""

import os
import json
import random
import time
from typing import Optional, Any
from pydantic import BaseModel, Field

from ..core.config import get_settings
from ..core.observability import logger

settings = get_settings()

# ── Dynamic Imports ──────────────────────────────────────────
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# ── Response Schema Definition ───────────────────────────────
class LLMReasoningResponse(BaseModel):
    analysis: str = Field(..., description="Root cause analysis of the anomaly")
    action: str = Field(..., description="Recommended remediation action (kubectl command)")
    rationale: str = Field(..., description="Explanation of why this action resolves the issue")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    provider: str = Field("simulation", description="Name of the LLM provider that generated the response")
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_tier: Optional[str] = None
    routed_model: Optional[str] = None


# ── LLM Service Manager ──────────────────────────────────────
class LLMServiceManager:
    """Manages LLM providers with automatic cascading failover."""

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize clients if available
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning("llm_openai_init_failed", error=str(e))
                
        if ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            except Exception as e:
                logger.warning("llm_anthropic_init_failed", error=str(e))
                
        if GEMINI_AVAILABLE and settings.ENKRYPT_API_KEY:  # Gemini configuration
            try:
                genai.configure(api_key=settings.ENKRYPT_API_KEY)
            except Exception as e:
                logger.warning("llm_gemini_init_failed", error=str(e))

    def generate_suggestion(
        self,
        anomaly_type: str,
        description: str,
        prompt_context: str,
        rag_context: str,
        severity: str = "MEDIUM",
        latency_critical: bool = False,
        cost_sensitive: bool = False
    ) -> LLMReasoningResponse:
        """Generate remediation recommendations routing dynamically to the optimal model."""
        from .llm_router_service import select_optimal_model
        input_len = len(prompt_context) + len(description) + len(rag_context)
        routing = select_optimal_model(
            anomaly_type=anomaly_type,
            severity=severity,
            input_text_length=input_len,
            latency_critical=latency_critical,
            cost_sensitive=cost_sensitive
        )
        
        tier = routing["tier"]
        model_name = routing["model_name"]

        logger.info(
            "llm_routing_decision",
            anomaly_type=anomaly_type,
            severity=severity,
            selected_tier=tier,
            selected_model=model_name,
            reason=routing["reason"]
        )

        provider_preference = settings.LLM_PROVIDER.lower()
        cascade = [provider_preference, "openai", "anthropic", "gemini", "simulation"]
        seen = set()
        cascade = [x for x in cascade if not (x in seen or seen.add(x))]

        for p in cascade:
            start_time = time.time()
            try:
                res = None
                original_provider = settings.LLM_PROVIDER
                settings.LLM_PROVIDER = p
                try:
                    p_routing = select_optimal_model(
                        anomaly_type=anomaly_type,
                        severity=severity,
                        input_text_length=input_len,
                        latency_critical=latency_critical,
                        cost_sensitive=cost_sensitive
                    )
                    p_model_name = p_routing["model_name"]
                finally:
                    settings.LLM_PROVIDER = original_provider

                from .circuit_breaker_service import CircuitBreakerService
                if p == "openai" and self.openai_client:
                    res = CircuitBreakerService.call(
                        "openai",
                        self._call_openai,
                        anomaly_type, description, prompt_context, rag_context, p_model_name, tier
                    )
                elif p == "anthropic" and self.anthropic_client:
                    res = CircuitBreakerService.call(
                        "anthropic",
                        self._call_anthropic,
                        anomaly_type, description, prompt_context, rag_context, p_model_name, tier
                    )
                elif p == "gemini" and GEMINI_AVAILABLE:
                    res = CircuitBreakerService.call(
                        "gemini",
                        self._call_gemini,
                        anomaly_type, description, prompt_context, rag_context, p_model_name, tier
                    )
                elif p == "simulation":
                    res = self._call_simulation(anomaly_type, description, prompt_context, rag_context, p_model_name, tier)
                
                if res is not None:
                    try:
                        from ..core.observability import track_llm_request
                        track_llm_request(p, "success", time.time() - start_time)
                    except Exception:
                        pass
                    return res
            except Exception as e:
                try:
                    from ..core.observability import track_llm_request
                    track_llm_request(p, "failed", time.time() - start_time)
                except Exception:
                    pass
                logger.warning("llm_cascade_fallback", provider=p, error=str(e))

        start_time = time.time()
        res = self._call_simulation(anomaly_type, description, prompt_context, rag_context, "simulation-standard", "standard")
        try:
            from ..core.observability import track_llm_request
            track_llm_request("simulation", "success", time.time() - start_time)
        except Exception:
            pass
        return res

    def _call_openai(self, anomaly_type: str, description: str, prompt: str, rag: str, model_name: str = "gpt-4o", tier: str = "standard") -> LLMReasoningResponse:
        """Call OpenAI chat completions API using dynamic model routing."""
        from .quota_service import ResourceQuotaService
        ResourceQuotaService.track_llm_call_start()
        try:
            # Estimate token sizes
            system_instruction = f"{prompt}\n\nHistorical Context:\n{rag}"
            user_message = f"Anomaly: {anomaly_type}. Details: {description}"
            input_est = (len(system_instruction) + len(user_message)) // 4
            
            # Enforce limits (will raise QuotaExceededException if budget or size is over capacity)
            ResourceQuotaService.check_and_enforce_llm_quota(
                input_tokens=input_est,
                output_tokens=1000,
                estimated_cost=0.02
            )

            completion = self.openai_client.chat.completions.create(
                model=model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1
            )
            raw_res = completion.choices[0].message.content
            data = json.loads(raw_res)
            
            input_tokens = completion.usage.prompt_tokens
            output_tokens = completion.usage.completion_tokens
            
            if tier == "fast_cheap":
                cost = (input_tokens * 0.15 / 1e6) + (output_tokens * 0.60 / 1e6)
            elif tier == "full_power":
                cost = (input_tokens * 10.00 / 1e6) + (output_tokens * 30.00 / 1e6)
            else:
                cost = (input_tokens * 5.00 / 1e6) + (output_tokens * 15.00 / 1e6)
            
            return LLMReasoningResponse(
                analysis=data.get("analysis", f"Analyzed {anomaly_type}"),
                action=data.get("action", "kubectl get pods"),
                rationale=data.get("rationale", "Standard status check query"),
                confidence=float(data.get("confidence", 0.85)),
                provider="openai",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                model_tier=tier,
                routed_model=model_name
            )
        finally:
            ResourceQuotaService.track_llm_call_end()

    def _call_anthropic(self, anomaly_type: str, description: str, prompt: str, rag: str, model_name: str = "claude-3-5-sonnet-20240620", tier: str = "standard") -> LLMReasoningResponse:
        """Call Anthropic API using dynamic model routing."""
        system_instruction = f"{prompt}\n\nHistorical Context:\n{rag}"
        user_message = f"Anomaly: {anomaly_type}. Details: {description}\nReturn JSON format matching the schema."
        
        message = self.anthropic_client.messages.create(
            model=model_name,
            max_tokens=1000,
            temperature=0.1,
            system=system_instruction,
            messages=[{"role": "user", "content": user_message}]
        )
        
        raw_res = message.content[0].text
        data = json.loads(raw_res)
        
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        
        if tier == "fast_cheap":
            cost = (input_tokens * 0.25 / 1e6) + (output_tokens * 1.25 / 1e6)
        elif tier == "full_power":
            cost = (input_tokens * 15.00 / 1e6) + (output_tokens * 75.00 / 1e6)
        else:
            cost = (input_tokens * 3.00 / 1e6) + (output_tokens * 15.00 / 1e6)
        
        return LLMReasoningResponse(
            analysis=data.get("analysis", f"Analyzed {anomaly_type}"),
            action=data.get("action", "kubectl get pods"),
            rationale=data.get("rationale", "Standard status check query"),
            confidence=float(data.get("confidence", 0.85)),
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            model_tier=tier,
            routed_model=model_name
        )

    def _call_gemini(self, anomaly_type: str, description: str, prompt: str, rag: str, model_name: str = "gemini-1.5-pro", tier: str = "standard") -> LLMReasoningResponse:
        """Call Google Gemini API using dynamic model routing."""
        model = genai.GenerativeModel(model_name)
        prompt_composed = f"{prompt}\n\nHistorical Context:\n{rag}\n\nAnomaly: {anomaly_type}. Details: {description}\nReturn JSON response."
        
        response = model.generate_content(prompt_composed)
        raw_res = response.text
        if raw_res.startswith("```json"):
            raw_res = raw_res.split("```json")[1].split("```")[0].strip()
        elif raw_res.startswith("```"):
            raw_res = raw_res.split("```")[1].split("```")[0].strip()
            
        data = json.loads(raw_res)
        
        input_tokens = len(prompt_composed) // 4
        output_tokens = len(raw_res) // 4
        
        if tier == "fast_cheap":
            cost = (input_tokens * 0.075 / 1e6) + (output_tokens * 0.30 / 1e6)
        else:
            cost = (input_tokens * 1.25 / 1e6) + (output_tokens * 5.00 / 1e6)
        
        return LLMReasoningResponse(
            analysis=data.get("analysis", f"Analyzed {anomaly_type}"),
            action=data.get("action", "kubectl get pods"),
            rationale=data.get("rationale", "Standard status check query"),
            confidence=float(data.get("confidence", 0.85)),
            provider="gemini",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            model_tier=tier,
            routed_model=model_name
        )

    def _call_simulation(self, anomaly_type: str, description: str, prompt: str, rag: str, model_name: str = "simulation-standard", tier: str = "standard") -> LLMReasoningResponse:
        """Simulate dynamic model responses with realistic costs and latencies based on selected model tier."""
        if tier == "fast_cheap":
            time.sleep(0.1 + random.uniform(0.05, 0.15))
        elif tier == "full_power":
            time.sleep(1.2 + random.uniform(0.8, 1.8))
        else:
            time.sleep(0.4 + random.uniform(0.2, 0.5))

        responses = {
            "CPU_SPIKE": {
                "analysis": "Severe CPU spikes on Kubernetes nodes. Target pod simulated-app-service is thrashing due to elevated client connections.",
                "action": "kubectl scale deployment/mock-service --replicas=3",
                "rationale": "Scaling deployment replica count shares the requests load and reduces average node CPU utilization.",
                "confidence": random.uniform(0.70, 0.79),
            },
            "MEMORY_EXHAUSTION": {
                "analysis": "Memory usage approached limit. Potential memory leak identified on node processes.",
                "action": "kubectl rollout restart deployment/mock-service",
                "rationale": "Restarting the deployment frees accumulated heap and memory context leaks.",
                "confidence": random.uniform(0.85, 0.95),
            },
            "UNAUTHORIZED_ACCESS": {
                "analysis": "Repeated failed unauthorized login events detected from host namespace.",
                "action": "kubectl delete pod -l app=malicious-scanner -n security",
                "rationale": "Evicting the container terminates network scans on the internal cluster network.",
                "confidence": random.uniform(0.90, 0.98),
            },
            "DISK_FULL": {
                "analysis": "PVC size exceeded 85%. Accumulation of historical error logs inside container root filesystems.",
                "action": "kubectl exec -it mock-service -- rm -rf /var/log/app-old.log",
                "rationale": "Removing old diagnostic files immediately frees storage namespace space.",
                "confidence": random.uniform(0.80, 0.90),
            },
            "HIGH_LATENCY": {
                "analysis": "HTTP latency spike above warning limits. CoreDNS queries experiencing connection timeouts.",
                "action": "kubectl rollout restart deployment/coredns -n kube-system",
                "rationale": "Restarting CoreDNS clears potential memory cache corruptions causing query delays.",
                "confidence": random.uniform(0.70, 0.85),
            },
            "ERROR_RATE_SPIKE": {
                "analysis": "Application error rate spiked. Regression error on latest deployment rollout version.",
                "action": "kubectl rollout undo deployment/mock-service",
                "rationale": "Reverting deployment revision reverts code blocks to last stable release version.",
                "confidence": random.uniform(0.80, 0.95),
            },
        }

        default_response = {
            "analysis": f"Simulated analysis of '{anomaly_type}' alert: {description[:100]}.",
            "action": "kubectl get pods",
            "rationale": "Diagnostic status check verification for manual debugging.",
            "confidence": random.uniform(0.60, 0.75),
        }

        res = responses.get(anomaly_type, default_response)
        input_tokens = len(prompt) + len(rag) + len(description)
        output_tokens = len(res["analysis"]) + len(res["action"]) + len(res["rationale"])

        if tier == "fast_cheap":
            cost = (input_tokens * 0.15 / 1e6) + (output_tokens * 0.60 / 1e6)
        elif tier == "full_power":
            cost = (input_tokens * 15.00 / 1e6) + (output_tokens * 75.00 / 1e6)
        else:
            cost = (input_tokens * 5.00 / 1e6) + (output_tokens * 15.00 / 1e6)

        return LLMReasoningResponse(
            analysis=res["analysis"],
            action=res["action"],
            rationale=res["rationale"],
            confidence=res["confidence"],
            provider="simulation",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            model_tier=tier,
            routed_model=model_name
        )


# Global instance
llm_manager = LLMServiceManager()
