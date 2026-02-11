"""Test login + call logs API"""
import urllib.request
import json

# Login
req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=json.dumps({"email": "test@test.com", "password": "test123"}).encode(),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())["access_token"]
print("LOGIN OK")

# Get calls
req2 = urllib.request.Request(
    "http://localhost:8000/api/v1/calls?limit=5",
    headers={"Authorization": f"Bearer {token}"}
)
resp2 = urllib.request.urlopen(req2)
calls = json.loads(resp2.read())
print(f"Total calls: {calls.get('total', '?')}")
print(f"Items returned: {len(calls.get('items', []))}")
for c in calls.get("items", [])[:5]:
    print(f"  id={c['id']} status={c['status']} duration={c.get('duration')} agent={c.get('agent_name','?')}")
