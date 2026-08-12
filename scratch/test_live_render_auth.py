import requests

url = 'https://sentinelflow-backend-sjrb.onrender.com/api/v1/auth/login'
test_cases = [
    ('admin@sentinelflow.ai', 'admin123'),
    ('admin@sentinelflow.ai', 'AdminPass123!'),
    ('engineer@sentinelflow.ai', 'eng123'),
    ('viewer@sentinelflow.ai', 'view123'),
    ('judge@sentinelflow.ai', 'JudgeDemo123!'),
]

for email, password in test_cases:
    res = requests.post(url, json={'email': email, 'password': password})
    print(f"Testing {email} with password '{password}':")
    print(f"  Status: {res.status_code}")
    print(f"  Body: {res.text}")
