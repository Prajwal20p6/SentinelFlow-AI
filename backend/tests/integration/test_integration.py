"""
SentinelFlow AI — Integration Tests
Verifies multi-service coordination, database queries/transactions, and cloud integrations.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.models.models import User, Incident
from app.integrations.redis_pubsub import pubsub_manager
from app.services.cloud_service import CloudRemediationManager
from app.services.incident_service import create_incident
from tests.factories.factories import create_incident_factory, create_user_factory


def test_database_integration_query(db_session):
    """Verify standard SQLAlchemy transactional queries and rollbacks."""
    user = create_user_factory(db_session, email="integration_db_test@example.com")
    assert user.id is not None
    
    fetched = db_session.query(User).filter(User.email == "integration_db_test@example.com").first()
    assert fetched is not None
    assert fetched.full_name == "Factory Test User"


def test_redis_pubsub_publish():
    """Verify Redis pub/sub serialization and routing logic."""
    with patch("app.integrations.redis_pubsub.REDIS_AVAILABLE", True), \
         patch("app.integrations.redis_pubsub._redis_client") as mock_redis:
        
        pubsub_manager.publish("TestMessage", {"status": "ok"})
        mock_redis.publish.assert_called_once()


@patch("app.core.config.get_settings")
def test_cloud_provider_integration_reboot(mock_settings, db_session):
    """Verify cloud execution routers under simulation/dry-run settings."""
    settings_mock = MagicMock()
    settings_mock.CLOUD_AWS_DRY_RUN = True
    settings_mock.CLOUD_K8S_DRY_RUN = True
    settings_mock.CLOUD_GCP_DRY_RUN = True
    mock_settings.return_value = settings_mock

    manager = CloudRemediationManager()

    # 1. K8s Pod Restart dry-run
    res_k8s = manager.execute_action(
        db=db_session, 
        incident_id=1,
        command="kubectl delete pod auth-api-pod -n default",
        dry_run=True
    )
    assert res_k8s["status"] == "SUCCESS"

    # 2. AWS EC2 reboot dry-run
    res_aws = manager.execute_action(
        db=db_session,
        incident_id=1,
        command="aws ec2 reboot-instances --instance-ids i-094e9f50e --region us-east-1",
        dry_run=True
    )
    assert res_aws["status"] == "SUCCESS"
