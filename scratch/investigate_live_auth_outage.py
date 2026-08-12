import requests
import json
import sys
import os

sys.path.insert(0, 'backend')
from app.core.database import SessionLocal
from app.models.models import User, UserSession

BASE_URL = 'https://sentinelflow-backend-sjrb.onrender.com/api/v1'

def investigate_all_flows():
    print("==========================================================================")
    print("   SENTINELFLOW AI — PRODUCTION AUTHENTICATION OUTAGE INVESTIGATION")
    print("==========================================================================")

    import random, string
    rnd = ''.join(random.choices(string.ascii_lowercase, k=6))
    test_email = f"outage_test_{rnd}@sentinelflow.ai"
    test_password = "OutageTestPassword123!"

    # -------------------------------------------------------------------------
    # FLOW 2a: User Registration
    # -------------------------------------------------------------------------
    print("\n--- [FLOW 2a] User Registration (POST /auth/register) ---")
    reg_payload = {
        "email": test_email,
        "password": test_password,
        "full_name": "Outage Test User",
        "role": "engineer"
    }
    print(f"Request URL: {BASE_URL}/auth/register")
    print(f"Payload: {json.dumps(reg_payload)}")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    print(f"Response Status: {reg_res.status_code}")
    print(f"Response Headers: {dict(reg_res.headers)}")
    print(f"Response Body: {reg_res.text}")

    # Check Neon DB directly
    db = SessionLocal()
    db_user_reg = db.query(User).filter(User.email == test_email).first()
    if db_user_reg:
        print(f"DB Verification: USER CREATED IN NEON DB | ID: {db_user_reg.id} | Email: {db_user_reg.email} | Active: {db_user_reg.is_active} | Verified: {db_user_reg.email_verified} | Hash: {db_user_reg.hashed_password[:30]}...")
    else:
        print(f"DB Verification: USER NOT FOUND IN NEON DB!")

    # -------------------------------------------------------------------------
    # FLOW 2b: Login (Before Email Verification)
    # -------------------------------------------------------------------------
    print("\n--- [FLOW 2b] Login (POST /auth/login) [Before Email Verification] ---")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    print(f"Request URL: {BASE_URL}/auth/login")
    print(f"Payload: {json.dumps(login_payload)}")
    login_res = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    print(f"Response Status: {login_res.status_code}")
    print(f"Response Body: {login_res.text}")

    # -------------------------------------------------------------------------
    # FLOW 2d: Forgot Password
    # -------------------------------------------------------------------------
    print("\n--- [FLOW 2d] Forgot Password (POST /auth/forgot-password) ---")
    forgot_payload = {
        "email": test_email
    }
    print(f"Request URL: {BASE_URL}/auth/forgot-password")
    print(f"Payload: {json.dumps(forgot_payload)}")
    forgot_res = requests.post(f"{BASE_URL}/auth/forgot-password", json=forgot_payload)
    print(f"Response Status: {forgot_res.status_code}")
    print(f"Response Body: {forgot_res.text}")

    # Check Neon DB for reset token
    db.expire_all()
    db_user_forgot = db.query(User).filter(User.email == test_email).first()
    reset_token = None
    if db_user_forgot:
        reset_token = db_user_forgot.password_reset_token
        print(f"DB Verification: Reset Token in DB: {reset_token} | Expires: {db_user_forgot.password_reset_expires}")

    # -------------------------------------------------------------------------
    # FLOW 2e: Reset Password
    # -------------------------------------------------------------------------
    print("\n--- [FLOW 2e] Reset Password (POST /auth/reset-password) ---")
    new_password = "NewResetPassword123!"
    if reset_token:
        reset_payload = {
            "token": reset_token,
            "new_password": new_password
        }
        print(f"Request URL: {BASE_URL}/auth/reset-password")
        print(f"Payload: {json.dumps(reset_payload)}")
        reset_res = requests.post(f"{BASE_URL}/auth/reset-password", json=reset_payload)
        print(f"Response Status: {reset_res.status_code}")
        print(f"Response Body: {reset_res.text}")
    else:
        print("Skipping Reset Password API call (no token found in DB)")

    # -------------------------------------------------------------------------
    # FLOW 2f: Email Verification & Post-Verification Login
    # -------------------------------------------------------------------------
    print("\n--- [FLOW 2f] Email Verification & Active Account Login ---")
    v_token = None
    try:
        v_token = reg_res.json().get("verification_token")
    except:
        pass

    if v_token:
        print(f"Calling POST /auth/verify-email?token={v_token[:20]}...")
        ver_res = requests.post(f"{BASE_URL}/auth/verify-email?token={v_token}")
        print(f"Verify Status: {ver_res.status_code} | Body: {ver_res.text}")

    print("\nAttempting Login again with test_password...")
    login_res_2 = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": test_password})
    print(f"Login Status with original password: {login_res_2.status_code} | Body: {login_res_2.text}")

    if reset_token:
        print("\nAttempting Login with new_password (after reset)...")
        login_res_3 = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": new_password})
        print(f"Login Status with new password: {login_res_3.status_code} | Body: {login_res_3.text}")

    # -------------------------------------------------------------------------
    # FLOW 2c: Logout
    # -------------------------------------------------------------------------
    print("\n--- [FLOW 2c] Logout (POST /auth/logout) ---")
    if login_res_3.status_code == 200:
        ref_tok = login_res_3.json().get("refresh_token")
        logout_res = requests.post(f"{BASE_URL}/auth/logout", headers={"X-Refresh-Token": ref_tok})
        print(f"Logout Status: {logout_res.status_code} | Body: {logout_res.text}")

    db.close()
    print("\n==========================================================================")

if __name__ == "__main__":
    investigate_all_flows()
