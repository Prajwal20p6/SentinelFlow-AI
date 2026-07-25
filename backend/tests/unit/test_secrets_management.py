import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from app.core.secrets import (
    get_secret,
    get_secret_provider,
    reset_secrets_cache,
    EnvSecretProvider,
    AWSSecretProvider,
)

@pytest.fixture(autouse=True)
def clean_secrets_environment():
    """Reset secret provider state before and after each test."""
    reset_secrets_cache()
    yield
    reset_secrets_cache()


def test_env_secret_provider():
    provider = EnvSecretProvider()
    with patch.dict(os.environ, {"TEST_KEY": "my_env_val"}):
        assert provider.get_secret("TEST_KEY") == "my_env_val"
        assert provider.get_secret("NONEXISTENT_KEY", "default_val") == "default_val"


def test_aws_secret_provider_json_bundle():
    mock_boto_client = MagicMock()
    mock_boto_client.get_secret_value.return_value = {
        "SecretString": json.dumps({
            "OPENAI_API_KEY": "sk-aws-mock-key-12345",
            "DATABASE_URL": "postgresql://aws_user:pass@db:5432/sentinelflow"
        })
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_boto_client

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        provider = AWSSecretProvider(region_name="us-west-2", secret_bundle_name="sentinelflow/prod")
        
        # First call loads bundle and populates cache
        val = provider.get_secret("OPENAI_API_KEY")
        assert val == "sk-aws-mock-key-12345"

        val_db = provider.get_secret("DATABASE_URL")
        assert val_db == "postgresql://aws_user:pass@db:5432/sentinelflow"

        # Verify boto3 client was invoked
        mock_boto3.client.assert_called_with("secretsmanager", region_name="us-west-2")
        assert mock_boto_client.get_secret_value.call_count == 1


def test_aws_secret_provider_single_key_and_fallback():
    mock_boto_client = MagicMock()
    # Bundle fetch fails or returns empty, then single key succeeds
    mock_boto_client.get_secret_value.side_effect = [
        Exception("Bundle not found"),
        {"SecretString": "single_secret_val"}
    ]
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_boto_client

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        provider = AWSSecretProvider(region_name="us-east-1")
        val = provider.get_secret("SINGLE_SECRET_KEY")
        assert val == "single_secret_val"


def test_aws_secret_provider_full_fallback_to_env():
    mock_boto_client = MagicMock()
    mock_boto_client.get_secret_value.side_effect = Exception("AWS unreachable")
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_boto_client

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        with patch.dict(os.environ, {"FALLBACK_KEY": "env_fallback_value"}):
            provider = AWSSecretProvider()
            val = provider.get_secret("FALLBACK_KEY", default="default_fallback")
            assert val == "env_fallback_value"

            val_missing = provider.get_secret("COMPLETELY_MISSING", default="default_fallback")
            assert val_missing == "default_fallback"


def test_get_secret_factory_env_mode():
    with patch.dict(os.environ, {"SECRETS_PROVIDER": "env", "API_TOKEN": "token123"}):
        val = get_secret("API_TOKEN")
        assert val == "token123"
        assert isinstance(get_secret_provider(), EnvSecretProvider)


def test_get_secret_factory_aws_mode():
    mock_boto_client = MagicMock()
    mock_boto_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"AWS_MANAGED_KEY": "secret_from_aws"})
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_boto_client

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        with patch.dict(os.environ, {"SECRETS_PROVIDER": "aws"}):
            assert isinstance(get_secret_provider(), AWSSecretProvider)
            val = get_secret("AWS_MANAGED_KEY")
            assert val == "secret_from_aws"
