import pytest
from unittest.mock import patch, MagicMock
from app.core.vector_db import search_similar_runbooks, in_memory_store

@pytest.fixture(autouse=True)
def seed_test_point():
    """Seed a test point in the in-memory fallback store."""
    in_memory_store.points.clear()
    in_memory_store.upsert(
        point_id=999,
        vector=[0.1] * 384,
        payload={
            "title": "Fallback Test Runbook",
            "content": "K8s OOM Killer Remediation Steps",
            "tags": ["k8s", "memory"],
            "severity": "CRITICAL",
            "category": "k8s"
        }
    )
    yield
    in_memory_store.points.clear()

def test_qdrant_cascading_fallback_to_in_memory():
    """Verify that when Qdrant, ChromaDB, and FAISS fail, search_similar_runbooks falls back to In-Memory store."""
    with patch("app.services.circuit_breaker_service.CircuitBreakerService.call", side_effect=RuntimeError("Qdrant Unavailable")), \
         patch("app.core.vector_db.CHROMA_AVAILABLE", False), \
         patch("app.core.vector_db.FAISS_AVAILABLE", False):
        
        results = search_similar_runbooks("K8s OOM memory exhaustion", limit=1)
        
        assert len(results) == 1
        assert results[0]["id"] == 999
        assert results[0]["title"] == "Fallback Test Runbook"

def test_qdrant_cascading_fallback_to_faiss():
    """Verify that when Qdrant and ChromaDB fail, search_similar_runbooks falls back to FAISS store."""
    mock_faiss_hits = [{
        "id": 888,
        "score": 0.95,
        "title": "FAISS Fallback Runbook",
        "content": "FAISS Index Match",
        "tags": ["faiss"],
        "severity": "HIGH",
        "category": "faiss"
    }]
    
    with patch("app.services.circuit_breaker_service.CircuitBreakerService.call", side_effect=RuntimeError("Qdrant Down")), \
         patch("app.core.vector_db.CHROMA_AVAILABLE", False), \
         patch("app.core.vector_db.FAISS_AVAILABLE", True), \
         patch("app.core.vector_db.faiss_store.search", return_value=mock_faiss_hits):
        
        results = search_similar_runbooks("FAISS search query", limit=1)
        
        assert len(results) == 1
        assert results[0]["id"] == 888
        assert results[0]["title"] == "FAISS Fallback Runbook"

def test_qdrant_cascading_fallback_to_chroma():
    """Verify that when Qdrant fails, search_similar_runbooks falls back to ChromaDB store."""
    mock_chroma_hits = [{
        "id": 777,
        "score": 0.98,
        "title": "ChromaDB Fallback Runbook",
        "content": "Chroma Collection Match",
        "tags": ["chroma"],
        "severity": "MEDIUM",
        "category": "chroma"
    }]
    
    with patch("app.services.circuit_breaker_service.CircuitBreakerService.call", side_effect=RuntimeError("Qdrant Outage")), \
         patch("app.core.vector_db.CHROMA_AVAILABLE", True), \
         patch("app.core.vector_db.chroma_store.search", return_value=mock_chroma_hits):
        
        results = search_similar_runbooks("ChromaDB query", limit=1)
        
        assert len(results) == 1
        assert results[0]["id"] == 777
        assert results[0]["title"] == "ChromaDB Fallback Runbook"

def test_vector_cascading_all_fail_returns_empty_list():
    """Counterpart failure test: Verify gracefully returning empty list when all 4 vector backends fail."""
    with patch("app.services.circuit_breaker_service.CircuitBreakerService.call", side_effect=RuntimeError("Qdrant Error")), \
         patch("app.core.vector_db.CHROMA_AVAILABLE", True), \
         patch("app.core.vector_db.chroma_store.search", side_effect=RuntimeError("Chroma Error")), \
         patch("app.core.vector_db.FAISS_AVAILABLE", True), \
         patch("app.core.vector_db.faiss_store.search", side_effect=RuntimeError("FAISS Error")), \
         patch("app.core.vector_db.in_memory_store.search", side_effect=RuntimeError("InMemory Error")):
        
        results = search_similar_runbooks("Total System Failure Query", limit=1)
        assert results == []
