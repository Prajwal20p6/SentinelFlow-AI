import pytest
from app.models.models import Incident, User, RemediationExecution
from app.core.security import hash_password

@pytest.fixture
def engineer_headers(client, db_session):
    user = db_session.query(User).filter(User.email == "engineer-demo@sentinelflow.ai").first()
    if not user:
        user = User(
            email="engineer-demo@sentinelflow.ai",
            hashed_password=hash_password("engineerpass"),
            full_name="Engineer User",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
    resp = client.post("/api/v1/auth/login", json={
        "email": "engineer-demo@sentinelflow.ai",
        "password": "engineerpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(client, db_session):
    user = db_session.query(User).filter(User.email == "admin-demo@sentinelflow.ai").first()
    if not user:
        user = User(
            email="admin-demo@sentinelflow.ai",
            hashed_password=hash_password("adminpass"),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin-demo@sentinelflow.ai",
        "password": "adminpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_trigger_demo_scenarios(client, db_session, engineer_headers):
    # 1. Trigger CPU_SPIKE
    resp = client.post("/api/v1/demo/trigger", json={"scenario": "CPU_SPIKE"}, headers=engineer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["scenario"] == "CPU_SPIKE"
    assert "incident_id" in data
    
    # 2. Trigger DISK_FULL
    resp = client.post("/api/v1/demo/trigger", json={"scenario": "DISK_FULL"}, headers=engineer_headers)
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "DISK_FULL"

    # 3. Trigger PHISHING_ATTACK
    resp = client.post("/api/v1/demo/trigger", json={"scenario": "PHISHING_ATTACK"}, headers=engineer_headers)
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "PHISHING_ATTACK"

    # 4. Trigger DDOS_ATTACK
    resp = client.post("/api/v1/demo/trigger", json={"scenario": "DDOS_ATTACK"}, headers=engineer_headers)
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "DDOS_ATTACK"

    # 5. Trigger DATA_BREACH
    resp = client.post("/api/v1/demo/trigger", json={"scenario": "DATA_BREACH"}, headers=engineer_headers)
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "DATA_BREACH"

    # 6. Trigger invalid scenario
    resp = client.post("/api/v1/demo/trigger", json={"scenario": "INVALID_X"}, headers=engineer_headers)
    assert resp.status_code == 400

def test_demo_cleanup(client, db_session, engineer_headers, admin_headers):
    # 1. Create a demo record first
    client.post("/api/v1/demo/trigger", json={"scenario": "CPU_SPIKE"}, headers=engineer_headers)
    incidents_before = db_session.query(Incident).count()
    assert incidents_before > 0

    # 2. Cleanup demo data
    resp = client.post("/api/v1/demo/cleanup", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # 3. Verify database tables are empty
    assert db_session.query(Incident).count() == 0
