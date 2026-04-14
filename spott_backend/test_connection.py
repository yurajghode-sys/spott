import urllib.request
import json

try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/events', timeout=5) as response:
        data = json.loads(response.read().decode('utf-8'))
        print('Backend API Status: ✅ Connected')
        print(f'Status Code: {response.status}')
        print(f'Events Count: {len(data.get("data", []))}')
        if data.get('data'):
            print(f'First Event: {data["data"][0]["title"]}')
except Exception as e:
    print('Backend API Status: ❌ Not Connected')
    print(f'Error: {e}')