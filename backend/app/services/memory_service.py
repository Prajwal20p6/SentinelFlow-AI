"""
SentinelFlow AI — Agent Memory & Shared Collaboration Memory Service
Implements CRUD vector memory operations on Qdrant with local dynamic cache fallbacks.
"""

import json
import hashlib
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue

from ..core.vector_db import qdrant_client, get_text_embedding
from ..core.config import get_settings
from ..core.observability import logger

settings = get_settings()

# ── Dynamic Local Cache Fallback ──────────────────────────────
# Structure: MEMORY_FALLBACK[collection_name][point_id] = {payload}
MEMORY_FALLBACK = {}


def _get_stable_point_id(collection_name: str, key: str, incident_id: int) -> int:
    """Generates a stable 32-bit unsigned integer ID from unique compound keys."""
    hash_str = f"{collection_name}:{key}:{incident_id}"
    return int(hashlib.md5(hash_str.encode()).hexdigest()[:8], 16)


# ── CRUD Operations ───────────────────────────────────────────

def store_memory(
    collection_name: str,
    key: str,
    value: str,
    incident_id: int,
    agent_id: Optional[str] = None
) -> None:
    """Upserts a record into the specified memory collection."""
    vector = get_text_embedding(f"{key}: {value}")
    point_id = _get_stable_point_id(collection_name, key, incident_id)

    payload = {
        "key": key,
        "value": value,
        "incident_id": incident_id,
        "agent_id": agent_id or "system",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 1. Update Fallback Cache
    MEMORY_FALLBACK.setdefault(collection_name, {})[point_id] = {
        "vector": vector,
        "payload": payload
    }

    # 2. Update Qdrant
    try:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )
        logger.debug("memory_store_qdrant_success", collection=collection_name, key=key)
    except Exception as e:
        logger.warning("memory_store_qdrant_failed", collection=collection_name, key=key, error=str(e))


def update_memory(
    collection_name: str,
    key: str,
    value: str,
    incident_id: int,
    agent_id: Optional[str] = None
) -> None:
    """Wrapper around store_memory since stable hashing allows in-place updates."""
    store_memory(collection_name, key, value, incident_id, agent_id=agent_id)


def retrieve_memory(
    collection_name: str,
    query: str,
    incident_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Retrieves relevant memories using cosine vector similarity filtered by incident_id."""
    query_vector = get_text_embedding(query)

    # ── 1. Try Qdrant ─────────────────────────────────────────
    try:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="incident_id",
                    match=MatchValue(value=incident_id)
                )
            ]
        )
        results = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            query_filter=search_filter
        )
        if results and results.points:
            return [hit.payload for hit in results.points]
    except Exception as e:
        logger.warning("memory_retrieve_qdrant_failed", collection=collection_name, error=str(e))

    # ── 2. Fallback to Local Cosine Scan ──────────────────────
    hits = []
    points = MEMORY_FALLBACK.get(collection_name, {})
    
    for pid, pt in points.items():
        payload = pt["payload"]
        if payload["incident_id"] != incident_id:
            continue
        
        # Calculate cosine similarity
        v1 = np.array(query_vector)
        v2 = np.array(pt["vector"])
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        score = float(dot / (norm1 * norm2)) if (norm1 > 0 and norm2 > 0) else 0.0

        hits.append((score, payload))

    # Sort by score descending
    hits.sort(key=lambda x: x[0], reverse=True)
    return [h[1] for h in hits[:limit]]


def clear_memory(incident_id: int) -> None:
    """Removes all memories associated with an incident across all collections."""
    # 1. Clear Fallback Cache
    for col in MEMORY_FALLBACK:
        MEMORY_FALLBACK[col] = {
            pid: pt for pid, pt in MEMORY_FALLBACK[col].items()
            if pt["payload"]["incident_id"] != incident_id
        }

    # 2. Clear Qdrant
    memory_collections = [
        "shared_memory",
        "agent_memory_rca_agent",
        "agent_memory_threat_intel_agent",
        "org_memory"
    ]
    for col in memory_collections:
        try:
            qdrant_client.delete(
                collection_name=col,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="incident_id",
                            match=MatchValue(value=incident_id)
                        )
                    ]
                )
            )
        except Exception as e:
            logger.warning("memory_clear_qdrant_failed", collection=col, incident_id=incident_id, error=str(e))


def sync_resolved_incident_to_org_memory(db, incident_id: int) -> None:
    """Sync a resolved incident and its context to the org_memory collection."""
    from ..models.models import Incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return
        
    rca_text = ""
    if incident.root_cause_json:
        try:
            rca = json.loads(incident.root_cause_json)
            rca_text = f"Primary Cause: {rca.get('primary_cause')}. Evidence: {', '.join(rca.get('evidence', []))}."
        except Exception:
            pass

    content = (
        f"Incident: {incident.title}\n"
        f"Metric Type: {incident.metric_type}\n"
        f"Severity: {incident.severity}\n"
        f"Description: {incident.description}\n"
        f"RCA Findings: {rca_text}\n"
        f"Remediation Action: {incident.suggested_action}\n"
        f"Outcome Status: {incident.status}"
    )

    vector = get_text_embedding(content)
    point_id = incident.id + 20000

    payload = {
        "incident_id": incident.id,
        "title": incident.title,
        "metric_type": incident.metric_type,
        "severity": incident.severity,
        "rca_findings": rca_text,
        "remediation_action": incident.suggested_action,
        "outcome": incident.status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Store in fallback
    MEMORY_FALLBACK.setdefault("org_memory", {})[point_id] = {
        "vector": vector,
        "payload": payload
    }

    # Store in Qdrant
    try:
        qdrant_client.upsert(
            collection_name="org_memory",
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )
        logger.info("org_memory_incident_synced", incident_id=incident.id)
    except Exception as e:
        logger.warning("org_memory_incident_sync_failed", incident_id=incident.id, error=str(e))


def search_similar_resolved_incidents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Query similarity search in the org_memory collection to find past resolved incidents."""
    query_vector = get_text_embedding(query)
    
    # Try Qdrant
    try:
        results = qdrant_client.query_points(
            collection_name="org_memory",
            query=query_vector,
            limit=limit
        )
        if results and results.points:
            return [hit.payload for hit in results.points]
    except Exception as e:
        logger.warning("org_memory_search_qdrant_failed", error=str(e))

    # Fallback to local scan
    hits = []
    points = MEMORY_FALLBACK.get("org_memory", {})
    for pid, pt in points.items():
        v1 = np.array(query_vector)
        v2 = np.array(pt["vector"])
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        score = float(dot / (norm1 * norm2)) if (norm1 > 0 and norm2 > 0) else 0.0
        hits.append((score, pt["payload"]))

    hits.sort(key=lambda x: x[0], reverse=True)
    return [h[1] for h in hits[:limit]]
