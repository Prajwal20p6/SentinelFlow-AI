"""
SentinelFlow AI — Resource Quota Enforcement Service
Sets resource constraints, tracks usage metrics, alerts on threshold breaches, and rejects over-limit commands.
"""

import os
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from ..core.observability import logger

class QuotaExceededException(Exception):
    """Raised when an operation is blocked because resource limits are exceeded."""
    pass

class ResourceQuotaService:
    """Monitors resource constraints (Connections, LLM budgets, Vectors size, Storage metrics)."""

    # Static in-memory trackers for LLM consumption
    _llm_monthly_cost_usd: float = 0.0
    _llm_concurrent_calls: int = 0

    @classmethod
    def get_quota_status(cls, db: Session) -> Dict[str, Any]:
        """Calculates current resource utilization percentages and returns stats."""
        # 1. Database connection count check
        db_connections = 5  # mock default or read from active engine pool
        
        # 2. Storage checks (directory sizes)
        audit_log_size_gb = 0.1
        incident_db_size_gb = 0.05
        db_path = "./sentinelflow.db"
        if os.path.exists(db_path):
            incident_db_size_gb = os.path.getsize(db_path) / (1024 * 1024 * 1024)

        # 3. Qdrant / vector database
        qdrant_vectors = 500  # mock collections count
        qdrant_size_gb = 0.01

        # 4. Redis cache memory
        redis_mem_gb = 0.05

        status = {
            "database": {
                "max_connections": 50,
                "current_connections": db_connections,
                "percent": (db_connections / 50.0) * 100
            },
            "llm_api": {
                "monthly_budget_usd": 1000.0,
                "current_spend_usd": cls._llm_monthly_cost_usd,
                "percent": (cls._llm_monthly_cost_usd / 1000.0) * 100
            },
            "qdrant_vector": {
                "max_vectors": 1000000,
                "current_vectors": qdrant_vectors,
                "percent": (qdrant_vectors / 1000000.0) * 100
            },
            "audit_storage": {
                "max_storage_gb": 5.0,
                "current_storage_gb": audit_log_size_gb,
                "percent": (audit_log_size_gb / 5.0) * 100
            },
            "redis_cache": {
                "max_memory_gb": 2.0,
                "current_memory_gb": redis_mem_gb,
                "percent": (redis_mem_gb / 2.0) * 100
            }
        }
        return status

    @classmethod
    def check_and_enforce_llm_quota(cls, input_tokens: int, output_tokens: int, estimated_cost: float) -> None:
        """Enforces limits on tokens per request and total monthly LLM budget."""
        # 1. Request limits
        if input_tokens > 4000:
            raise QuotaExceededException(f"Input token limit exceeded: {input_tokens} > 4000 max.")
        if output_tokens > 2000:
            raise QuotaExceededException(f"Output token limit exceeded: {output_tokens} > 2000 max.")

        # 2. Concurrent requests limit
        if cls._llm_concurrent_calls >= 10:
            raise QuotaExceededException("Max concurrent LLM requests limit (10) reached.")

        # 3. Spend budget check
        cls._llm_monthly_cost_usd += estimated_cost
        if cls._llm_monthly_cost_usd >= 1000.0:
            raise QuotaExceededException(f"Monthly LLM spend limit ($1000) reached. Spend: ${cls._llm_monthly_cost_usd:.2f}")
        
        # 4. Check thresholds and alert
        pct = (cls._llm_monthly_cost_usd / 1000.0) * 100
        if pct >= 95.0:
            logger.error("llm_budget_critical_limit_reached", spend=cls._llm_monthly_cost_usd, threshold="95%")
        elif pct >= 80.0:
            logger.warning("llm_budget_warning_limit_reached", spend=cls._llm_monthly_cost_usd, threshold="80%")

    @classmethod
    def track_llm_call_start(cls):
        """Increments concurrency counter."""
        cls._llm_concurrent_calls += 1

    @classmethod
    def track_llm_call_end(cls):
        """Decrements concurrency counter."""
        cls._llm_concurrent_calls = max(0, cls._llm_concurrent_calls - 1)
