"""
SentinelFlow AI — Intelligent LLM Router Service
Performs score-based model selection, cost tracking, and metrics aggregation.
"""

import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.models import AIObservabilityTrace, Incident

settings = get_settings()

# Tier cost configurations (Cost per 1M tokens)
MODEL_TIER_META = {
    "fast_cheap": {
        "cost_input_1m": 0.15,
        "cost_output_1m": 0.60,
        "average_latency_ms": 250.0,
        "estimated_accuracy": 0.80
    },
    "standard": {
        "cost_input_1m": 5.00,
        "cost_output_1m": 15.00,
        "average_latency_ms": 900.0,
        "estimated_accuracy": 0.92
    },
    "full_power": {
        "cost_input_1m": 15.00,
        "cost_output_1m": 75.00,
        "average_latency_ms": 3000.0,
        "estimated_accuracy": 0.98
    }
}


def select_optimal_model(
    anomaly_type: str,
    severity: str,
    input_text_length: int,
    latency_critical: bool = False,
    cost_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Score incident and select optimal model tier (fast_cheap, standard, full_power)
    based on complexity heuristics, latency criticality, and cost sensitivity.
    """
    # ── 1. Calculate Base Complexity (0-100) ─────────────────
    complexity = 50  # Default standard complexity
    
    if severity == "CRITICAL":
        complexity = 80
    elif severity == "HIGH":
        complexity = 65
    elif severity == "MEDIUM":
        complexity = 40
    elif severity == "LOW":
        complexity = 20

    # Incident type adjusters
    if anomaly_type == "UNAUTHORIZED_ACCESS":
        complexity += 20
    elif anomaly_type in ["CPU_SPIKE", "DISK_FULL"]:
        complexity -= 15

    # Context window length adjuster
    if input_text_length > 4000:
        complexity += 15

    # Clamp complexity between 0 and 100
    complexity = max(0, min(100, complexity))

    # ── 2. Determine Optimal Tier ───────────────────────────
    selected_tier = "standard"
    reason = "Balanced standard model chosen by default."

    # Latency critical override
    if latency_critical or settings.LLM_LATENCY_CRITICAL:
        if severity == "CRITICAL":
            selected_tier = "standard"
            reason = "Selected standard tier for critical severity under latency constraint."
        else:
            selected_tier = "fast_cheap"
            reason = "Forced fast_cheap tier to fulfill latency-critical requirements."
    # Cost sensitive override
    elif cost_sensitive or settings.LLM_COST_SENSITIVE:
        if severity == "CRITICAL":
            selected_tier = "standard"
            reason = "Selected standard tier for critical severity under cost optimization bounds."
        else:
            selected_tier = "fast_cheap"
            reason = "Selected fast_cheap tier due to high cost sensitivity constraints."
    # Normal heuristics-based routing
    else:
        if complexity >= 75:
            selected_tier = "full_power"
            reason = f"Routed to full_power tier due to high complexity score ({complexity})."
        elif complexity >= 40:
            selected_tier = "standard"
            reason = f"Routed to standard tier due to medium complexity score ({complexity})."
        else:
            selected_tier = "fast_cheap"
            reason = f"Routed to fast_cheap tier due to low complexity score ({complexity})."

    # ── 3. Resolve Concrete Model Name ────────────────────────
    provider = settings.LLM_PROVIDER.lower()
    model_name = "simulation-standard"

    if provider == "openai":
        mapping = {
            "fast_cheap": "gpt-4o-mini",
            "standard": "gpt-4o",
            "full_power": "gpt-4-turbo"
        }
        model_name = mapping[selected_tier]
    elif provider == "anthropic":
        mapping = {
            "fast_cheap": "claude-3-haiku-20240307",
            "standard": "claude-3-5-sonnet-20240620",
            "full_power": "claude-3-opus-20240229"
        }
        model_name = mapping[selected_tier]
    elif provider == "gemini":
        mapping = {
            "fast_cheap": "gemini-1.5-flash",
            "standard": "gemini-1.5-pro",
            "full_power": "gemini-1.5-pro"
        }
        model_name = mapping[selected_tier]
    else:  # simulation
        mapping = {
            "fast_cheap": "simulation-fast",
            "standard": "simulation-standard",
            "full_power": "simulation-complex"
        }
        model_name = mapping[selected_tier]

    return {
        "tier": selected_tier,
        "model_name": model_name,
        "complexity_score": complexity,
        "reason": reason,
        "metadata": MODEL_TIER_META[selected_tier]
    }


def get_llm_router_stats(db: Session) -> Dict[str, Any]:
    """Computes cost-benefit metrics, selection logs, and optimization wins from LLM execution traces."""
    traces = db.query(AIObservabilityTrace).filter(
        AIObservabilityTrace.step_name == "LLM_REASONING"
    ).all()

    total_requests = len(traces)
    total_cost = 0.0
    total_latency = 0.0
    tier_counts = {"fast_cheap": 0, "standard": 0, "full_power": 0}
    
    # Calculate savings comparing actual costs with worst-case cost (running always full_power)
    estimated_worst_case_cost = 0.0

    for t in traces:
        # Accumulate latency
        total_latency += t.latency_ms

        # Parse cost details from metadata_json
        cost = 0.0
        tier = "standard"
        if t.metadata_json:
            try:
                meta = json.loads(t.metadata_json)
                cost = meta.get("cost_usd", 0.0)
                tier = meta.get("model_tier", "standard")
            except Exception:
                pass
        
        total_cost += cost
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Worst case scenario: Always run full_power (Claude Opus / GPT-4 Turbo)
        worst_case_cost = (t.input_tokens * 15.00 / 1e6) + (t.output_tokens * 75.00 / 1e6)
        estimated_worst_case_cost += worst_case_cost

    savings = max(0.0, estimated_worst_case_cost - total_cost)
    avg_latency = (total_latency / total_requests) if total_requests > 0 else 0.0

    return {
        "total_routed_requests": total_requests,
        "total_actual_cost_usd": total_cost,
        "estimated_savings_usd": savings,
        "average_latency_ms": avg_latency,
        "tier_distribution": tier_counts,
        "optimization_efficiency_percentage": round((savings / estimated_worst_case_cost * 100) if estimated_worst_case_cost > 0 else 100.0, 2)
    }
