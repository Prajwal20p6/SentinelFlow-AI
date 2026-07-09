import pytest
import numpy as np
from app.core.vector_db import (
    get_text_embedding,
    search_similar_runbooks,
    add_resolution_to_qdrant,
    InMemoryVectorStore,
)

def test_pseudo_embedding_generation():
    emb = get_text_embedding("CPU usage spike on deployment")
    assert len(emb) == 384
    norm = np.linalg.norm(emb)
    assert pytest.approx(norm, 0.01) == 1.0

def test_in_memory_search_fallback():
    store = InMemoryVectorStore()
    payload1 = {"title": "CPU issue", "content": "Limit CPU usage", "category": "performance"}
    payload2 = {"title": "Disk full", "content": "Clean storage", "category": "storage"}
    
    vec1 = [1.0] + [0.0]*383
    vec2 = [0.0] * 384
    vec2[1] = 1.0
    
    store.upsert(1, vec1, payload1)
    store.upsert(2, vec2, payload2)
    
    # Search close to vec1
    hits = store.search(vec1, limit=1)
    assert len(hits) == 1
    assert hits[0]["title"] == "CPU issue"
    
    # Search close to vec2 with category filter
    hits_filter = store.search(vec2, limit=1, category_filter="storage")
    assert len(hits_filter) == 1
    assert hits_filter[0]["title"] == "Disk full"

def test_search_cascade():
    results = search_similar_runbooks("CPU Exhaustion", limit=1)
    assert len(results) >= 1
    assert results[0]["title"] == "CPU Exhaustion Remediation"
