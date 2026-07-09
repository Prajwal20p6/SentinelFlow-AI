import pytest
from app.services.quota_service import ResourceQuotaService, QuotaExceededException

def test_quota_monitoring_and_enforcement(db_session):
    # 1. Check status structure
    status = ResourceQuotaService.get_quota_status(db_session)
    assert "database" in status
    assert "llm_api" in status
    assert "qdrant_vector" in status
    
    # 2. Reset spent budget
    ResourceQuotaService._llm_monthly_cost_usd = 0.0
    ResourceQuotaService._llm_concurrent_calls = 0

    # 3. Test token limit checks (too many input tokens)
    with pytest.raises(QuotaExceededException) as exc:
        ResourceQuotaService.check_and_enforce_llm_quota(input_tokens=4500, output_tokens=500, estimated_cost=0.01)
    assert "Input token limit exceeded" in str(exc.value)

    # 4. Test output token limits
    with pytest.raises(QuotaExceededException) as exc:
        ResourceQuotaService.check_and_enforce_llm_quota(input_tokens=2000, output_tokens=2500, estimated_cost=0.01)
    assert "Output token limit exceeded" in str(exc.value)

    # 5. Test concurrency limits
    for _ in range(10):
        ResourceQuotaService.track_llm_call_start()
    
    with pytest.raises(QuotaExceededException) as exc:
        ResourceQuotaService.check_and_enforce_llm_quota(input_tokens=1000, output_tokens=500, estimated_cost=0.01)
    assert "concurrent" in str(exc.value).lower()

    # Reset concurrency
    ResourceQuotaService._llm_concurrent_calls = 0

    # 6. Test budget exhaustion
    # Simulate spending $999.00
    ResourceQuotaService.check_and_enforce_llm_quota(input_tokens=1000, output_tokens=500, estimated_cost=999.00)
    
    # Next call exceeds the $1000 threshold
    with pytest.raises(QuotaExceededException) as exc:
        ResourceQuotaService.check_and_enforce_llm_quota(input_tokens=1000, output_tokens=500, estimated_cost=2.00)
    assert "budget" in str(exc.value).lower() or "limit" in str(exc.value).lower()
