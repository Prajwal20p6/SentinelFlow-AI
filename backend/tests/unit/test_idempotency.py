import pytest
from datetime import datetime, timezone, timedelta
from app.services.idempotency_service import IdempotencyService
from app.models.models import IdempotencyKey

def test_idempotency_registration_and_cache(db_session):
    key = "test-idem-key-1"
    
    # 1. First registration should succeed
    success = IdempotencyService.register_key(db_session, key, incident_id=12, action_type="/approve")
    assert success is True
    
    # 2. Duplicate registration with same key should fail
    dup_success = IdempotencyService.register_key(db_session, key, incident_id=12, action_type="/approve")
    assert dup_success is False
    
    # 3. Retrieve cached response (should return 202 initially because response is still PROCESSING status 202)
    cached = IdempotencyService.get_cached_response(db_session, key)
    assert cached is not None
    status_code, body = cached
    assert status_code == 202
    assert body["message"] == "Request is being processed"
    
    # 4. Save actual completed response
    response_body = {"status": "success", "executed": True}
    IdempotencyService.save_response(db_session, key, status_code=200, body=response_body)
    
    # 5. Retrieve cached response again (should succeed and return actual body)
    cached_again = IdempotencyService.get_cached_response(db_session, key)
    assert cached_again is not None
    status_code_final, body_final = cached_again
    assert status_code_final == 200
    assert body_final["status"] == "success"
    
    # 6. Test expiration (expires_at in past)
    record = db_session.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    record.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db_session.commit()
    
    # Retrieving expired key should clean it up and return None
    expired_cached = IdempotencyService.get_cached_response(db_session, key)
    assert expired_cached is None
    assert db_session.query(IdempotencyKey).filter(IdempotencyKey.key == key).first() is None
