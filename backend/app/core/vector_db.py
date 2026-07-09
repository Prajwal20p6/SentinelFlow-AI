"""
SentinelFlow AI — Qdrant Vector Database Client & Fallback Manager
Manages vector similarity search for RAG-based incident resolution retrieval
with automatic cascading fallbacks (ChromaDB, FAISS, and InMemory stores).
"""

import os
import numpy as np
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from .config import get_settings
from .observability import logger

settings = get_settings()

# ── Dynamic Imports for Fallbacks ──────────────────────────
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# ── Model Initializer ────────────────────────────────────────
model = None
if SENTENCE_TRANSFORMERS_AVAILABLE:
    try:
        # Load lightweight sentence embedding model (384 dimensions)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("embeddings_model_loaded", model="all-MiniLM-L6-v2")
    except Exception as e:
        logger.warning("embeddings_model_fallback", error=str(e))


# ── Embedding Generator ─────────────────────────────────────
def get_text_embedding(text: str) -> list[float]:
    """Generate a text embedding vector (384 dimensions)."""
    if model is not None:
        try:
            emb = model.encode(text)
            return emb.tolist()
        except Exception as e:
            logger.warning("embeddings_encode_fallback", error=str(e))
            
    # Deterministic pseudo-embedding backup
    text_hash = sum(ord(c) for c in text)
    rng = np.random.RandomState(text_hash % 10000)
    base_vec = rng.randn(settings.QDRANT_VECTOR_SIZE).astype(np.float32)

    keyword_clusters = {
        "cpu": 1,
        "memory": 2, "oom": 2, "ram": 2,
        "security": 3, "unauthorized": 3, "breach": 3, "kube-system": 3,
        "database": 4, "postgres": 4, "connection": 4,
        "network": 5, "timeout": 5, "latency": 5, "dns": 5,
        "disk": 6, "storage": 6, "volume": 6, "pvc": 6,
        "crash": 7, "restart": 7, "backoff": 7, "crashloop": 7,
    }

    text_lower = text.lower()
    for keyword, cluster_seed in keyword_clusters.items():
        if keyword in text_lower:
            cluster_rng = np.random.RandomState(cluster_seed)
            base_vec += 2.0 * cluster_rng.randn(settings.QDRANT_VECTOR_SIZE).astype(np.float32)

    norm = np.linalg.norm(base_vec)
    if norm > 0:
        base_vec = base_vec / norm

    return base_vec.tolist()


# ── In-Memory Vector Store Fallback ──────────────────────────
class InMemoryVectorStore:
    """Fallback in-memory vector store using numpy-based cosine similarity."""
    def __init__(self):
        self.points = {}

    def upsert(self, point_id: int, vector: list[float], payload: dict):
        self.points[point_id] = {
            "vector": np.array(vector, dtype=np.float32),
            "payload": payload
        }

    def search(self, query_vector: list[float], limit: int = 3, category_filter: Optional[str] = None) -> list[dict]:
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        
        matches = []
        for pid, data in self.points.items():
            payload = data["payload"]
            if category_filter and payload.get("category") != category_filter:
                continue
                
            v_vec = data["vector"]
            v_norm = np.linalg.norm(v_vec)
            
            if q_norm > 0 and v_norm > 0:
                score = float(np.dot(q_vec, v_vec) / (q_norm * v_norm))
            else:
                score = 0.0
                
            matches.append({
                "id": pid,
                "score": score,
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "tags": payload.get("tags", []),
                "severity": payload.get("severity", ""),
                "category": payload.get("category", ""),
            })
            
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]


# ── ChromaDB Fallback Store ──────────────────────────────────
class ChromaFallbackStore:
    """Primary fallback using local SQLite-backed ChromaDB."""
    def __init__(self):
        self.client = None
        self.collection = None
        if CHROMA_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path="./data/chroma")
                self.collection = self.client.get_or_create_collection("runbooks")
            except Exception as e:
                logger.warning("chroma_init_failed", error=str(e))

    def upsert(self, point_id: int, vector: list[float], payload: dict):
        if self.collection:
            try:
                self.collection.add(
                    ids=[str(point_id)],
                    embeddings=[vector],
                    metadatas=[payload],
                    documents=[payload.get("content", "")]
                )
            except Exception as e:
                logger.warning("chroma_upsert_error", error=str(e))

    def search(self, query_vector: list[float], limit: int = 3, category_filter: Optional[str] = None) -> list[dict]:
        if not self.collection:
            return []
        try:
            where = {}
            if category_filter:
                where = {"category": category_filter}
                
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=where
            )
            
            hits = []
            if results and results.get("ids") and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    payload = results["metadatas"][0][i]
                    dist = results["distances"][0][i] if "distances" in results else 0.0
                    score = 1.0 / (1.0 + dist)
                    hits.append({
                        "id": int(results["ids"][0][i]),
                        "score": score,
                        "title": payload.get("title", ""),
                        "content": payload.get("content", ""),
                        "tags": payload.get("tags", []),
                        "severity": payload.get("severity", ""),
                        "category": payload.get("category", ""),
                    })
            return hits
        except Exception as e:
            logger.warning("chroma_query_error", error=str(e))
            return []


# ── FAISS Fallback Store ─────────────────────────────────────
class FAISSFallbackStore:
    """Secondary fallback using FAISS index."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self.id_map = {}
        if FAISS_AVAILABLE:
            try:
                self.index = faiss.IndexFlatIP(dimension)
            except Exception as e:
                logger.warning("faiss_init_failed", error=str(e))

    def upsert(self, point_id: int, vector: list[float], payload: dict):
        if self.index:
            try:
                vec_arr = np.array([vector], dtype=np.float32)
                faiss.normalize_L2(vec_arr)
                self.index.add(vec_arr)
                offset = self.index.ntotal - 1
                self.id_map[offset] = (point_id, payload)
            except Exception as e:
                logger.warning("faiss_upsert_error", error=str(e))

    def search(self, query_vector: list[float], limit: int = 3, category_filter: Optional[str] = None) -> list[dict]:
        if not self.index or self.index.ntotal == 0:
            return []
        try:
            q_vec = np.array([query_vector], dtype=np.float32)
            faiss.normalize_L2(q_vec)
            
            distances, indices = self.index.search(q_vec, min(limit * 2, self.index.ntotal))
            
            hits = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx not in self.id_map:
                    continue
                point_id, payload = self.id_map[idx]
                if category_filter and payload.get("category") != category_filter:
                    continue
                hits.append({
                    "id": point_id,
                    "score": float(dist),
                    "title": payload.get("title", ""),
                    "content": payload.get("content", ""),
                    "tags": payload.get("tags", []),
                    "severity": payload.get("severity", ""),
                    "category": payload.get("category", ""),
                })
                if len(hits) >= limit:
                    break
            return hits
        except Exception as e:
            logger.warning("faiss_search_error", error=str(e))
            return []


# ── Instantiations ───────────────────────────────────────────
in_memory_store = InMemoryVectorStore()
chroma_store = ChromaFallbackStore()
faiss_store = FAISSFallbackStore(settings.QDRANT_VECTOR_SIZE)

# ── Qdrant Client Initialization ─────────────────────────────
os.makedirs(settings.QDRANT_PATH, exist_ok=True)

if settings.QDRANT_MODE == "server":
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=settings.QDRANT_TIMEOUT,
    )
else:
    qdrant_client = QdrantClient(
        path=settings.QDRANT_PATH,
        timeout=settings.QDRANT_TIMEOUT,
    )


# ── Collection Management ────────────────────────────────────
def init_qdrant_collections() -> None:
    """Initialize collections and seed runbooks, including agent memory collections."""
    try:
        collections = qdrant_client.get_collections().collections
        existing_names = {c.name for c in collections}

        # 1. Main Runbooks Collection
        if settings.QDRANT_COLLECTION not in existing_names:
            qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=settings.QDRANT_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            _seed_runbooks()
            logger.info("qdrant_collection_created", collection=settings.QDRANT_COLLECTION)
        else:
            logger.info("qdrant_collection_exists", collection=settings.QDRANT_COLLECTION)
            _seed_runbooks()

        # 2. Agent Memory Collections
        memory_collections = [
            "shared_memory",
            "agent_memory_rca_agent",
            "agent_memory_threat_intel_agent",
            "org_memory"
        ]
        for col in memory_collections:
            if col not in existing_names:
                qdrant_client.create_collection(
                    collection_name=col,
                    vectors_config=VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("qdrant_memory_collection_created", collection=col)
            else:
                logger.info("qdrant_memory_collection_exists", collection=col)

    except Exception as e:
        logger.warning("qdrant_init_error", error=str(e))
        _seed_runbooks()


def _seed_runbooks() -> None:
    """Seed initial runbook entries for RAG retrieval."""
    runbooks = [
        {
            "id": 1,
            "title": "CPU Exhaustion Remediation",
            "content": "When CPU usage exceeds 90% on a node, identify the high-consuming pod. "
                       "If non-critical, scale down replicas by 50% or restart the deployment. "
                       "Run: kubectl scale deployment/<name> --replicas=2. Monitor for 5 minutes after action.",
            "tags": ["cpu", "scale", "kubernetes", "performance"],
            "severity": "CRITICAL",
            "category": "performance",
        },
        {
            "id": 2,
            "title": "Unauthorized Access — Namespace Isolation",
            "content": "For unauthorized access or token abuse in sensitive namespaces (e.g., kube-system), "
                       "immediately isolate pod network policies, revoke active service account tokens, "
                       "and notify the security operations channel. Audit RBAC bindings for privilege escalation.",
            "tags": ["security", "auth", "kube-system", "rbac"],
            "severity": "CRITICAL",
            "category": "security",
        },
        {
            "id": 3,
            "title": "Database OOMKilled Recovery",
            "content": "If PostgreSQL pods report OOMKilled events, verify memory limits in the pod spec, "
                       "clean temp files, run VACUUM FULL if applicable, and restart the pod with "
                       "increased memory limits. Check for query memory leaks.",
            "tags": ["database", "memory", "postgresql", "oom"],
            "severity": "WARNING",
            "category": "database",
        },
        {
            "id": 4,
            "title": "Network Timeout — DNS Resolution Failure",
            "content": "When services report DNS resolution failures or connection timeouts exceeding 30s, "
                       "verify CoreDNS pods are healthy, check NetworkPolicy rules, and restart kube-dns "
                       "if resolution cache is stale. Escalate if cluster-wide.",
            "tags": ["network", "dns", "timeout", "coredns"],
            "severity": "WARNING",
            "category": "network",
        },
        {
            "id": 5,
            "title": "CrashLoopBackOff — Container Recovery",
            "content": "For pods in CrashLoopBackOff state, inspect container logs for the root cause "
                       "(missing config, permission errors, health check failures). Apply fixes and "
                       "delete the pod to trigger fresh scheduling. Check resource quotas.",
            "tags": ["crash", "restart", "crashloop", "container"],
            "severity": "WARNING",
            "category": "reliability",
        },
        {
            "id": 6,
            "title": "Persistent Volume Claim — Storage Exhaustion",
            "content": "When PVC usage exceeds 85%, identify large files for cleanup, expand the PV if "
                       "the storage class supports dynamic provisioning, or migrate data to a larger volume. "
                       "Set up alerts for 70% threshold warnings.",
            "tags": ["disk", "storage", "pvc", "volume"],
            "severity": "WARNING",
            "category": "storage",
        },
    ]

    points = []
    for rb in runbooks:
        vec = get_text_embedding(rb["content"])
        
        # Populate fallbacks
        in_memory_store.upsert(rb["id"], vec, rb)
        chroma_store.upsert(rb["id"], vec, rb)
        faiss_store.upsert(rb["id"], vec, rb)
        
        points.append(
            PointStruct(
                id=rb["id"],
                vector=vec,
                payload=rb,
            )
        )

    try:
        qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points,
        )
    except Exception as e:
        logger.warning("qdrant_seed_failed", error=str(e))


# ── Search & Retrieval ───────────────────────────────────────
def search_similar_runbooks(
    query: str,
    limit: int = 3,
    score_threshold: float = 0.3,
    category_filter: Optional[str] = None,
) -> list[dict]:
    """Search for similar runbooks using vector similarity with automatic fallback cascade."""
    from ..core.tracing import TracingService
    with TracingService.span("vector_db_search", {"query": query, "limit": limit}):
        query_vector = get_text_embedding(query)

        # ── 1. Try Qdrant ────────────────────────────────────────
        try:
            search_filter = None
            if category_filter:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=category_filter),
                        )
                    ]
                )
            from ..services.circuit_breaker_service import CircuitBreakerService
            results = CircuitBreakerService.call(
                "qdrant",
                qdrant_client.query_points,
                collection_name=settings.QDRANT_COLLECTION,
                query=query_vector,
                limit=limit,
                query_filter=search_filter,
                score_threshold=score_threshold,
            )
            if results and results.points:
                return [
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "title": hit.payload.get("title", ""),
                        "content": hit.payload.get("content", ""),
                        "tags": hit.payload.get("tags", []),
                        "severity": hit.payload.get("severity", ""),
                        "category": hit.payload.get("category", ""),
                    }
                    for hit in results.points
                ]
        except Exception as e:
            logger.warning("vdb_qdrant_search_failed", error=str(e))

        # ── 2. Try ChromaDB Fallback ─────────────────────────────
        if CHROMA_AVAILABLE:
            try:
                hits = chroma_store.search(query_vector, limit, category_filter)
                if hits:
                    logger.debug("vdb_chroma_fallback_succeeded")
                    return hits
            except Exception as e:
                logger.warning("vdb_chroma_search_failed", error=str(e))

        # ── 3. Try FAISS Fallback ────────────────────────────────
        if FAISS_AVAILABLE:
            try:
                hits = faiss_store.search(query_vector, limit, category_filter)
                if hits:
                    logger.debug("vdb_faiss_fallback_succeeded")
                    return hits
            except Exception as e:
                logger.warning("vdb_faiss_search_failed", error=str(e))

        # ── 4. Try In-Memory Fallback ────────────────────────────
        try:
            hits = in_memory_store.search(query_vector, limit, category_filter)
            logger.debug("vdb_inmemory_fallback_succeeded")
            return hits
        except Exception as e:
            logger.error("vdb_all_fallbacks_failed", error=str(e))
            return []


def add_resolution_to_qdrant(
    incident_id: int,
    title: str,
    content: str,
    tags: list[str],
    category: str = "resolved",
) -> None:
    """Sync a resolved incident into the vector index and fallbacks."""
    vector = get_text_embedding(content)
    point_id = incident_id + 10000

    payload = {
        "id": point_id,
        "title": title,
        "content": content,
        "tags": tags,
        "severity": "INFO",
        "category": category,
        "source": "auto-resolution",
    }

    # Populate fallbacks
    in_memory_store.upsert(point_id, vector, payload)
    chroma_store.upsert(point_id, vector, payload)
    faiss_store.upsert(point_id, vector, payload)

    try:
        from ..services.circuit_breaker_service import CircuitBreakerService
        CircuitBreakerService.call(
            "qdrant",
            qdrant_client.upsert,
            collection_name=settings.QDRANT_COLLECTION,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        logger.info("qdrant_resolution_synced", incident_id=incident_id)
    except Exception as e:
        logger.warning("qdrant_resolution_sync_failed", incident_id=incident_id, error=str(e))
