import pytest
import json
from app.services.llm_router_service import select_optimal_model, get_llm_router_stats
from app.services.llm_service import llm_manager
from app.models.models import AIObservabilityTrace, Incident

def test_router_scoring_logic():
    # 1. Low complexity + cost-sensitive -> fast_cheap
    decision_cheap = select_optimal_model(
        anomaly_type="CPU_SPIKE",
        severity="LOW",
        input_text_length=500,
        latency_critical=False,
        cost_sensitive=True
    )
    assert decision_cheap["tier"] == "fast_cheap"
    assert "fast" in decision_cheap["model_name"]

    # 2. Critical + unauthorized -> standard or full_power (depends on latency/normal override)
    decision_critical = select_optimal_model(
        anomaly_type="UNAUTHORIZED_ACCESS",
        severity="CRITICAL",
        input_text_length=1000,
        latency_critical=False,
        cost_sensitive=False
    )
    assert decision_critical["tier"] == "full_power"

    # 3. Critical + latency_critical override -> standard (protecting critical severity latency)
    decision_latent_critical = select_optimal_model(
        anomaly_type="UNAUTHORIZED_ACCESS",
        severity="CRITICAL",
        input_text_length=1000,
        latency_critical=True,
        cost_sensitive=False
    )
    assert decision_latent_critical["tier"] == "standard"


def test_llm_service_router_integration():
    # Trigger suggestion generation under cheap bounds
    resp = llm_manager.generate_suggestion(
        anomaly_type="CPU_SPIKE",
        description="Minor threshold warnings.",
        prompt_context="Analyze SRE status",
        rag_context="No matches",
        severity="LOW",
        cost_sensitive=True
    )
    assert resp.model_tier == "fast_cheap"
    assert "fast" in resp.routed_model
    assert resp.cost_usd < 0.0005


def test_observability_routing_traces_and_stats(client, db_session):
    # Setup test user credentials
    from app.core.security import hash_password
    from app.models.models import User
    
    user = db_session.query(User).filter(User.email == "router-auditor@sentinelflow.ai").first()
    if not user:
        user = User(
            email="router-auditor@sentinelflow.ai",
            hashed_password=hash_password("auditorpass"),
            full_name="Router Auditor",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    resp = client.post("/api/v1/auth/login", json={
        "email": "router-auditor@sentinelflow.ai",
        "password": "auditorpass"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Inject mock trace logs
    trace_cheap = AIObservabilityTrace(
        correlation_id="trace-cid-cheap",
        step_name="LLM_REASONING",
        input_tokens=1000,
        output_tokens=200,
        latency_ms=150.0,
        status="success",
        metadata_json=json.dumps({
            "model_tier": "fast_cheap",
            "model_name": "simulation-fast",
            "cost_usd": 0.00027
        })
    )
    trace_complex = AIObservabilityTrace(
        correlation_id="trace-cid-complex",
        step_name="LLM_REASONING",
        input_tokens=2000,
        output_tokens=500,
        latency_ms=2500.0,
        status="success",
        metadata_json=json.dumps({
            "model_tier": "full_power",
            "model_name": "simulation-complex",
            "cost_usd": 0.06750
        })
    )
    db_session.add(trace_cheap)
    db_session.add(trace_complex)
    db_session.commit()

    # Query LLM router statistics endpoint
    res_stats = client.get("/api/v1/agent/observability/llm-router/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_routed_requests"] >= 2
    assert stats["total_actual_cost_usd"] > 0.0
    assert stats["tier_distribution"]["fast_cheap"] >= 1
    assert stats["tier_distribution"]["full_power"] >= 1
