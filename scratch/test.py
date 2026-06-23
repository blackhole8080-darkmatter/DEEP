import os
import sys

# ensure CWD is in path
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from interface.server import app, settings

client = TestClient(app)
headers = {'x-deep-key': settings.deep_api_key}

print('Testing Finance...')
print(f"Finance status: {client.get('/api/finance/summary', headers=headers).status_code}")

print('Testing Email...')
print(f"Email status: {client.get('/api/email/inbox', headers=headers).status_code}")

print('Testing Missions...')
print(f"Missions status: {client.get('/api/missions', headers=headers).status_code}")
