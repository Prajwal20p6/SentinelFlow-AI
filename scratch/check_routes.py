import requests

resp = requests.get("https://sentinelflow-backend-sjrb.onrender.com/api/v1/openapi.json")
if resp.status_code == 200:
    schema = resp.json()
    paths = schema.get("paths", {})
    pm_paths = [p for p in paths if "postmortem" in p]
    print("Found postmortem routes in production:")
    for p in pm_paths:
        print(f" - {p}: {list(paths[p].keys())}")
else:
    print(f"Failed to fetch openapi.json: {resp.status_code}")
