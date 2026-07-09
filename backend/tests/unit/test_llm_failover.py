import pytest
from app.services.llm_service import llm_manager, LLMReasoningResponse

def test_simulation_fallback():
    # Call the simulation provider directly
    resp = llm_manager._call_simulation(
        "CPU_SPIKE", 
        "Mock CPU spike description", 
        "CRISPE prompt text", 
        "RAG history text"
    )
    assert isinstance(resp, LLMReasoningResponse)
    assert resp.provider == "simulation"
    assert resp.action == "kubectl scale deployment/mock-service --replicas=3"
    assert resp.confidence >= 0.70
    assert resp.confidence <= 0.79
    assert resp.cost_usd >= 0.0

def test_manager_failover_cascade():
    # Calling generate_suggestion should fall back to simulation provider
    # even when api keys are not supplied
    resp = llm_manager.generate_suggestion(
        "CPU_SPIKE", 
        "Mock CPU spike description", 
        "CRISPE prompt text", 
        "RAG history text"
    )
    assert isinstance(resp, LLMReasoningResponse)
    assert resp.provider in ("simulation", "openai", "anthropic", "gemini")
    assert resp.action == "kubectl scale deployment/mock-service --replicas=3"
