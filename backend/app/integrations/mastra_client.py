import httpx
import json
import logging

logger = logging.getLogger(__name__)

class MastraClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(timeout=60.0)
    
    def execute_incident_workflow(
        self,
        incident_id: str,
        incident_type: str,
        alert_data: dict,
        metrics: dict,
        logs: list
    ) -> dict:
        """Execute Mastra incident response workflow"""
        try:
            response = self.client.post(
                f"{self.base_url}/mastra/workflows/incident-response",
                json={
                    "incident_id": incident_id,
                    "incident_type": incident_type,
                    "alert_data": alert_data,
                    "metrics": metrics,
                    "logs": logs
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Mastra workflow failed: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check Mastra service health"""
        try:
            response = self.client.get(f"{self.base_url}/mastra/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Mastra health check failed: {e}")
            return False
    
    def close(self):
        self.client.close()
