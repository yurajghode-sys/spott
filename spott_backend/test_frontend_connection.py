import urllib.request
import json

# Test the API endpoint that the frontend uses
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/events', timeout=5) as response:
        data = json.loads(response.read().decode('utf-8'))
        print('✅ Backend API is accessible')
        print(f'   Status: {response.status}')
        print(f'   Events available: {len(data.get("data", []))}')
        if data.get('data'):
            print(f'   Sample event: {data["data"][0]["title"]}')

        # Check CORS headers
        cors_headers = {k: v for k, v in response.getheaders() if 'access-control' in k.lower()}
        if cors_headers:
            print('✅ CORS headers present:', cors_headers)
        else:
            print('❌ No CORS headers found')

except Exception as e:
    print('❌ Backend API not accessible')
    print(f'   Error: {e}')