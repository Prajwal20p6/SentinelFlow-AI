import requests
import json
import asyncio
import websockets

BASE_URL = 'https://sentinelflow-backend-sjrb.onrender.com/api/v1'

def run_regression_tests():
    print("============================================================")
    print("   SENTINELFLOW AI — PHASE 7 REGRESSION PASS (LIVE TEST)")
    print("============================================================")

    import random, string
    rnd = ''.join(random.choices(string.ascii_lowercase, k=6))
    email = f"regtest_{rnd}@sentinelflow.ai"
    password = "RegressionPass123!"

    print(f"\n1. Registering test account: {email}")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Regression Test User",
        "role": "engineer"
    })
    print(f"   Status: {reg_res.status_code}")
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    v_token = reg_res.json()["verification_token"]

    print(f"\n2. Verifying email token...")
    v_res = requests.post(f"{BASE_URL}/auth/verify-email?token={v_token}")
    print(f"   Status: {v_res.status_code}")
    assert v_res.status_code == 200, f"Email verification failed: {v_res.text}"

    print(f"\n3. Authenticating user (POST /auth/login)...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    print(f"   Status: {login_res.status_code}")
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    auth_data = login_res.json()
    access_token = auth_data["access_token"]
    refresh_token = auth_data["refresh_token"]
    user_info = auth_data["user"]
    print(f"   Tokens acquired successfully!")
    print(f"   User Profile: {user_info['email']} (Role: {user_info['role']})")

    print(f"\n4. Fetching user profile (GET /auth/me)...")
    me_res = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    print(f"   Status: {me_res.status_code}")
    assert me_res.status_code == 200, f"GET /auth/me failed: {me_res.text}"
    print(f"   Profile retrieved: {me_res.json()['email']}")

    print(f"\n5. Exercising token refresh (POST /auth/refresh)...")
    ref_res = requests.post(f"{BASE_URL}/auth/refresh", headers={"X-Refresh-Token": refresh_token})
    print(f"   Status: {ref_res.status_code}")
    assert ref_res.status_code == 200, f"Token refresh failed: {ref_res.text}"
    new_data = ref_res.json()
    new_access_token = new_data["access_token"]
    new_refresh_token = new_data["refresh_token"]
    print(f"   Token rotated successfully!")

    print(f"\n6. Testing real-time WebSocket connection handshake...")
    async def test_ws():
        ws_url = f"wss://sentinelflow-backend-sjrb.onrender.com/api/v1/ws/reg_test_session?token={new_access_token}"
        async with websockets.connect(ws_url) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"   WebSocket Message Received: {msg[:80]}...")
            await ws.send(json.dumps({"action": "ping"}))
            resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"   WebSocket Ping Response: {resp[:80]}...")
            print(f"   WebSocket WSS authenticated successfully!")
    asyncio.run(test_ws())

    print(f"\n7. Logging out and revoking session (POST /auth/logout)...")
    logout_res = requests.post(f"{BASE_URL}/auth/logout", headers={"X-Refresh-Token": new_refresh_token})
    print(f"   Status: {logout_res.status_code}")
    assert logout_res.status_code == 200, f"Logout failed: {logout_res.text}"
    print(f"   Session revoked on backend!")

    print(f"\n8. Verifying post-logout access controls...")
    post_res = requests.post(f"{BASE_URL}/auth/refresh", headers={"X-Refresh-Token": new_refresh_token})
    print(f"   Revoked Token Refresh Status: {post_res.status_code} (Expected: 401)")
    assert post_res.status_code == 401, f"Revoked refresh token was surprisingly accepted!"
    print(f"   Post-logout access controls strictly enforced!")

    print("\n============================================================")
    print("   === ALL PHASE 7 REGRESSION PASS TESTS PASSED 100% ===")
    print("============================================================")

if __name__ == "__main__":
    run_regression_tests()
