import sys
import numpy as np

# Add backend directory to path
sys.path.insert(0, "backend")

from app.core.vector_db import (
    _embedding_model,
    get_embedding_model,
    get_text_embedding,
    _get_fallback_embedding,
    reset_embedding_model
)

def cosine_sim(v1, v2):
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

print("=== 1. LAZY LOADING CHECK ===")
print("Model before call:", _embedding_model)
assert _embedding_model is None, "Model should be None before first call"

print("\n=== 2. REAL MODEL EMOTION & DIMENSION CHECK ===")
vec1 = get_text_embedding("high CPU utilization on server")
model_after = get_embedding_model()
print("Model loaded after call:", type(model_after).__name__)
print("Embedding dimension:", len(vec1))
assert len(vec1) == 384, f"Expected 384 dimensions, got {len(vec1)}"
assert model_after is not None, "Real SentenceTransformer model should be loaded"

print("\n=== 3. SEMANTIC SIMILARITY TEST ===")
vec_synonym = get_text_embedding("processor usage is extremely elevated on host")
vec_unrelated = get_text_embedding("database disk volume persistent storage full")

sim_synonym = cosine_sim(vec1, vec_synonym)
sim_unrelated = cosine_sim(vec1, vec_unrelated)

print(f"Similarity (CPU vs Processor elevated): {sim_synonym:.4f}")
print(f"Similarity (CPU vs Disk storage full):   {sim_unrelated:.4f}")

assert sim_synonym > sim_unrelated, (
    f"Synonymous sentences should score higher than unrelated! ({sim_synonym} <= {sim_unrelated})"
)
print("Semantic similarity verification PASSED!")

print("\n=== 4. FALLBACK ANAGRAM COLLISION FIX CHECK ===")
fb_listen = _get_fallback_embedding("listen")
fb_silent = _get_fallback_embedding("silent")
sim_anagram = cosine_sim(fb_listen, fb_silent)

print(f"Fallback Similarity ('listen' vs 'silent'): {sim_anagram:.4f}")
assert sim_anagram < 0.99, f"Anagram collision detected! Similarity is {sim_anagram}"
print("Anagram collision fix verification PASSED!")

print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")
