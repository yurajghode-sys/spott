import urllib.request
import json

# Test login
login_data = {
    "email": "user@spott.app",
    "password": "User@1234"
}

print("Logging in...")
login_data_json = json.dumps(login_data).encode('utf-8')
req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login",
                            data=login_data_json,
                            headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        login_result = json.loads(response.read().decode('utf-8'))
        token = login_result["data"]["token"]
        print(f"Got token: {token[:20]}...")

        # Test creating an event
        event_data = {
            "title": "Test Event from API",
            "category": "Tech",
            "datetime_iso": "2026-04-20T15:00:00",
            "location": "Test Location",
            "price": "Free",
            "description": "This is a test event created via API",
            "capacity": 50,
            "status": "published",
            "emoji": "🧪",
            "tags": ["test"]
        }

        event_data_json = json.dumps(event_data).encode('utf-8')
        req2 = urllib.request.Request("http://127.0.0.1:8000/api/events",
                                     data=event_data_json,
                                     headers={'Content-Type': 'application/json',
                                             'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req2) as response2:
            create_result = json.loads(response2.read().decode('utf-8'))
            print("Event created successfully!")
            print(f"Event ID: {create_result['data']['id']}")
            print(f"Event title: {create_result['data']['title']}")
except Exception as e:
    print(f"Error: {e}")