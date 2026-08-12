import requests
import uuid

BASE_URL = "https://sentinelflow-backend-sjrb.onrender.com/api/v1"

def test_endpoints():
    # 1. Login
    payload = {
        "email": "judge@sentinelflow.ai",
        "password": "JudgeDemo123!"
    }
    resp = requests.post(f"{BASE_URL}/auth/login", json=payload)
    token = resp.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Idempotency-Key": str(uuid.uuid4())
    }

    endpoints = [
        ("/incidents", "GET", {}),
        ("/incidents/nonexistent-id", "GET", {}),
        ("/demo/trigger", "POST", {"scenario": "CPU_SPIKE"}),
        ("/infra/execute-command", "POST", {"command": "kubectl get pods"}),
        ("/infra/topology", "GET", {}),
        ("/knowledge/documents", "GET", {})
    ]

    print("=== LIVE ENDPOINT AUDIT ===")
    for path, method, body in endpoints:
        url = f"{BASE_URL}{path}"
        headers["Idempotency-Key"] = str(uuid.uuid4())
        try:
            if method == "GET":
                r = requests.get(url, headers=headers)
            else:
                r = requests.post(url, json=body, headers=headers)
            print(f"Testing {method} {path} -> HTTP {r.status_code}")
        except Exception as e:
            print(f"Testing {method} {path} -> FAILED: {e}")

if __name__ == "__main__":
    test_endpoints()
