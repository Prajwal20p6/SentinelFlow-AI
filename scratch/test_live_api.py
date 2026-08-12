import requests
import json
import uuid

BASE_URL = "https://sentinelflow-backend-sjrb.onrender.com/api/v1"

def test_flow():
    print("=== LIVE PRODUCTION API TEST ===")
    
    # 1. Login
    login_url = f"{BASE_URL}/auth/login"
    payload = {
        "email": "judge@sentinelflow.ai",
        "password": "JudgeDemo123!"
    }
    print(f"1. Attempting login to {login_url}...")
    resp = requests.post(login_url, json=payload)
    if resp.status_code != 200:
        print(f"[FAIL] Login failed! Status: {resp.status_code}, Response: {resp.text}")
        return
    
    data = resp.json()
    token = data.get("access_token")
    print(f"[OK] Login successful! Token: {token[:20]}...")
    
    # Standard headers with Idempotency-Key
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Idempotency-Key": str(uuid.uuid4())
    }
    
    # 2. Get Incidents
    incidents_url = f"{BASE_URL}/incidents"
    print(f"\n2. Fetching incidents from {incidents_url}...")
    resp = requests.get(incidents_url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        incidents_list = data.get("incidents", data) if isinstance(data, dict) else data
        print(f"[OK] Fetched {len(incidents_list)} incidents successfully.")
        if isinstance(incidents_list, list):
            for inc in incidents_list[:5]:
                print(f" - #{inc.get('id')}: {inc.get('title')} [{inc.get('status')}]")
        else:
            print(f"Response: {data}")
    else:
        print(f"[FAIL] Fetching incidents failed! Status: {resp.status_code}")
        
    # 3. Create Demo Incident
    create_url = f"{BASE_URL}/demo/trigger"
    incident_payload = {
        "scenario": "CPU_SPIKE"
    }
    print(f"\n3. Triggering demo scenario via {create_url}...")
    # Refresh idempotency key for this post
    headers["Idempotency-Key"] = str(uuid.uuid4())
    resp = requests.post(create_url, json=incident_payload, headers=headers)
    if resp.status_code in [200, 201]:
        created = resp.json()
        print(f"[OK] Demo incident triggered successfully! ID: {created.get('incident_id')} - {created.get('message')}")
        target_id = created.get("incident_id")
    else:
        print(f"[FAIL] Demo incident trigger failed! Status: {resp.status_code}, Response: {resp.text}")
        target_id = None

    # 4. Security Command Validation
    validate_url = f"{BASE_URL}/infra/execute-command"
    validate_payload = {
        "command": "kubectl scale deployment payment-api --replicas=3",
        "incident_id": target_id or 1
    }
    print(f"\n4. Testing security command validation via {validate_url}...")
    headers["Idempotency-Key"] = str(uuid.uuid4())
    resp = requests.post(validate_url, json=validate_payload, headers=headers)
    if resp.status_code == 200:
        val_result = resp.json()
        print(f"[OK] Validation endpoint returned success!")
        print(f"   Output: {json.dumps(val_result, indent=2)}")
    else:
        print(f"[FAIL] Command validation returned error! Status: {resp.status_code}, Response: {resp.text}")

    # 5. Fetch Postmortem Report
    if target_id:
        postmortem_url = f"{BASE_URL}/incidents/{target_id}/postmortem"
        print(f"\n5. Fetching postmortem report for #{target_id}...")
        resp = requests.get(postmortem_url, headers=headers)
        if resp.status_code == 200:
            pm = resp.json()
            print("[OK] Postmortem fetched successfully!")
            print(f"   Summary: {pm.get('executive_summary', 'None')[:150]}...")
        else:
            # Let's generate it
            generate_url = f"{BASE_URL}/incidents/{target_id}/postmortem/generate"
            print(f"   Postmortem not found. Attempting generation via {generate_url}...")
            headers["Idempotency-Key"] = str(uuid.uuid4())
            resp = requests.post(generate_url, headers=headers)
            if resp.status_code == 200:
                pm = resp.json()
                print("[OK] Postmortem generated successfully!")
                print(f"   Summary: {pm.get('executive_summary', 'None')[:150]}...")
            else:
                print(f"[FAIL] Postmortem generation failed! Status: {resp.status_code}, Response: {resp.text}")

if __name__ == "__main__":
    test_flow()
