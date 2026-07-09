"""
SentinelFlow AI — Test Mocks
Mock providers for Qdrant client, Kubernetes client, AWS client, and GCP compute client wrappers.
"""

from unittest.mock import MagicMock

class MockK8sClient:
    """Mock Kubernetes API client."""
    def __init__(self):
        self.core_v1 = MagicMock()
        self.core_v1.read_namespaced_pod_log = MagicMock(return_value="pod logs stream")
        self.core_v1.delete_namespaced_pod = MagicMock(return_value=MagicMock())


class MockAWSClient:
    """Mock AWS EC2/Boto3 API client."""
    def __init__(self):
        self.client = MagicMock()
        self.client.reboot_instances = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})


class MockGCPClient:
    """Mock GCP Compute Engine API client."""
    def __init__(self):
        self.client = MagicMock()
        self.client.instances().reset = MagicMock(return_value=MagicMock())


class MockQdrantClient:
    """Mock Qdrant Vector database client."""
    def __init__(self):
        self.recreate_collection = MagicMock(return_value=True)
        self.upsert = MagicMock(return_value=MagicMock())
        self.search = MagicMock(return_value=[])
