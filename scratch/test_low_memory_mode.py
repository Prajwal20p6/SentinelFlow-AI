import os
import sys

os.environ["LOW_MEMORY_MODE"] = "true"
sys.path.insert(0, "backend")

from app.core.config import get_settings
from app.core.vector_db import get_text_embedding, init_qdrant_collections, search_similar_runbooks

settings = get_settings()
print("LOW_MEMORY_MODE active:", settings.LOW_MEMORY_MODE)
assert settings.LOW_MEMORY_MODE is True

init_qdrant_collections()
print("init_qdrant_collections succeeded in low memory mode!")

results = search_similar_runbooks("CPU spike remediation", limit=3)
print(f"RAG Search returned {len(results)} results in low memory mode:")
for r in results:
    print(f" - [{r.get('id')}] {r.get('title')} (score: {r.get('score'):.4f})")

assert len(results) > 0, "RAG Search should return results in low memory mode!"
print("\n=== ALL LOW MEMORY MODE TESTS PASSED ===")
