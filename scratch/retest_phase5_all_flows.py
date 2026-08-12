import requests
import json

BASE_URL = 'https://sentinelflow-backend-sjrb.onrender.com/api/v1'

def run_phase5_full_retest():
    print("==========================================================================")
    print("   SENTINELFLOW AI — PHASE 5 FULL AUTHENTICATION RETEST (LIVE HTTP)")
    print("==========================================================================")

    import random, string
    rnd = ''.join(random.choices(string.ascii_lowercase, k=6))
    test_email = f"phase5_retest_{rnd}@sentinelflow.ai"
    initial_password = "InitialPassword123!"
    reset_new_password = "ResetNewPassword123!"

    # 1. User Registration
    print(f"\n1. Testing Registration for {test_email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": test_email,
        "password": initial_password,
        "full_name": "Phase 5 Retest User",
        "role": "engineer"
    })
    print(f"   Status: {reg_res.status_code}")
    print(f"   Body: {reg_res.text}")
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    v_token = reg_res.json()["verification_token"]
    print(f"   [FLOW 2a] Registration PASSED!")

    # 2. Login Before Verification (Expected 403)
    print(f"\n2. Testing Login BEFORE Email Verification...")
    unver_login = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": initial_password})
    print(f"   Status: {unver_login.status_code} (Expected 403)")
    print(f"   Body: {unver_login.text}")
    assert unver_login.status_code == 403, f"Expected 403 for unverified user, got: {unver_login.status_code}"

    # 3. Email Verification
    print(f"\n3. Testing Email Verification (POST /auth/verify-email)...")
    ver_res = requests.post(f"{BASE_URL}/auth/verify-email?token={v_token}")
    print(f"   Status: {ver_res.status_code}")
    print(f"   Body: {ver_res.text}")
    assert ver_res.status_code == 200, f"Email verification failed: {ver_res.text}"

    # 4. Login After Verification
    print(f"\n4. Testing Login AFTER Email Verification...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": initial_password})
    print(f"   Status: {login_res.status_code}")
    print(f"   Body: {login_res.text}")
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    auth_data = login_res.json()
    access_token = auth_data["access_token"]
    refresh_token = auth_data["refresh_token"]
    print(f"   [FLOW 2b] Login PASSED! Bearer token & refresh token acquired.")

    # 5. Forgot Password
    print(f"\n5. Testing Forgot Password (POST /auth/forgot-password)...")
    forgot_res = requests.post(f"{BASE_URL}/auth/forgot-password", json={"email": test_email})
    print(f"   Status: {forgot_res.status_code}")
    print(f"   Body: {forgot_res.text}")
    assert forgot_res.status_code == 200, f"Forgot password failed: {forgot_res.text}"
    reset_token = forgot_res.json()["reset_token"]
    print(f"   [FLOW 2d] Forgot Password PASSED! Reset token generated.")

    # 6. Reset Password
    print(f"\n6. Testing Reset Password (POST /auth/reset-password)...")
    reset_res = requests.post(f"{BASE_URL}/auth/reset-password", json={
        "token": reset_token,
        "new_password": reset_new_password
    })
    print(f"   Status: {reset_res.status_code}")
    print(f"   Body: {reset_res.text}")
    assert reset_res.status_code == 200, f"Reset password failed: {reset_res.text}"
    print(f"   [FLOW 2e] Reset Password PASSED!")

    # 7. Verify Old Password Fails & New Password Succeeds
    print(f"\n7. Verifying Old Password Fails and New Password Succeeds...")
    old_login = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": initial_password})
    print(f"   Old Password Login Status: {old_login.status_code} (Expected 401)")
    assert old_login.status_code == 401, f"Old password should fail with 401, got: {old_login.status_code}"

    new_login = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": reset_new_password})
    print(f"   New Password Login Status: {new_login.status_code} (Expected 200)")
    assert new_login.status_code == 200, f"New password login failed: {new_login.text}"
    new_auth = new_login.json()
    new_access = new_auth["access_token"]
    new_refresh = new_auth["refresh_token"]
    print(f"   New Password Login PASSED!")

    # 8. User Profile (GET /auth/me) & Token Refresh (POST /auth/refresh)
    print(f"\n8. Testing User Profile & Token Refresh...")
    me_res = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    print(f"   GET /auth/me Status: {me_res.status_code}")
    assert me_res.status_code == 200, f"GET /auth/me failed: {me_res.text}"

    ref_res = requests.post(f"{BASE_URL}/auth/refresh", headers={"X-Refresh-Token": new_refresh})
    print(f"   POST /auth/refresh Status: {ref_res.status_code}")
    assert ref_res.status_code == 200, f"Refresh failed: {ref_res.text}"
    latest_refresh = ref_res.json()["refresh_token"]

    # 9. Logout & Session Revocation
    print(f"\n9. Testing Logout (POST /auth/logout)...")
    logout_res = requests.post(f"{BASE_URL}/auth/logout", headers={"X-Refresh-Token": latest_refresh})
    print(f"   Status: {logout_res.status_code}")
    print(f"   Body: {logout_res.text}")
    assert logout_res.status_code == 200, f"Logout failed: {logout_res.text}"
    print(f"   [FLOW 2c] Logout PASSED!")

    # 10. Verify Revoked Refresh Token Fails
    print(f"\n10. Verifying Revoked Token Cannot Be Used for Refresh...")
    rev_ref = requests.post(f"{BASE_URL}/auth/refresh", headers={"X-Refresh-Token": latest_refresh})
    print(f"   Revoked Refresh Token Status: {rev_ref.status_code} (Expected 401)")
    assert rev_ref.status_code == 401, "Revoked refresh token was accepted!"

    print("\n==========================================================================")
    print("   === ALL 7 AUTHENTICATION FLOWS RETESTED & 100% SUCCESSFUL LIVE! ===")
    print("==========================================================================")

if __name__ == "__main__":
    run_phase5_full_retest()
