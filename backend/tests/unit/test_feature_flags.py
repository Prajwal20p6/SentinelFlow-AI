import pytest
from app.services.feature_flag_service import is_enabled, toggle_flag, FeatureFlagKey, _FLAG_CACHE
from app.models.models import User, FeatureFlag
from app.core.security import hash_password

@pytest.fixture(autouse=True)
def clean_flag_cache():
    """Autouse fixture to clear the global feature flag cache before each test case."""
    _FLAG_CACHE.clear()

@pytest.fixture
def admin_headers(client, db_session):
    user = db_session.query(User).filter(User.email == "admin-ff@sentinelflow.ai").first()
    if not user:
        user = User(
            email="admin-ff@sentinelflow.ai",
            hashed_password=hash_password("adminpass"),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db_session.add(user)
    else:
        user.hashed_password = hash_password("adminpass")
    db_session.commit()
    db_session.refresh(user)
    
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin-ff@sentinelflow.ai",
        "password": "adminpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_feature_flag_resolution_and_seeding(db_session):
    # conftest.py overrides settings.FF_DEMO_MODE to False
    val = is_enabled(db_session, FeatureFlagKey.DEMO_MODE)
    assert val is False
    
    # Check that database row got created
    row = db_session.query(FeatureFlag).filter(FeatureFlag.key == FeatureFlagKey.DEMO_MODE.value).first()
    assert row is not None
    assert row.value is False

def test_feature_flag_cache_and_toggle(db_session):
    # Set to False
    toggle_flag(db_session, FeatureFlagKey.DEMO_MODE, False)
    assert is_enabled(db_session, FeatureFlagKey.DEMO_MODE) is False
    
    # Toggle to True
    toggle_flag(db_session, FeatureFlagKey.DEMO_MODE, True)
    assert is_enabled(db_session, FeatureFlagKey.DEMO_MODE) is True

def test_feature_flag_api(client, admin_headers):
    # Get all flags
    resp = client.get("/api/v1/feature-flags", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 5
    
    # Toggle a flag
    resp = client.post(
        f"/api/v1/feature-flags/{FeatureFlagKey.DEMO_MODE.value}/toggle",
        json={"value": False},
        headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["value"] is False
