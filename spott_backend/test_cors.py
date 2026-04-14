import urllib.request

# Test normal GET
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/events') as r:
        print('GET /api/events status', r.status)
        print('Headers:', dict(r.getheaders()))
except Exception as e:
    print('GET failed', e)

# Preflight OPTIONS test
req = urllib.request.Request('http://127.0.0.1:8000/api/events', method='OPTIONS')
req.add_header('Origin', 'http://localhost:3000')
req.add_header('Access-Control-Request-Method', 'POST')
req.add_header('Access-Control-Request-Headers', 'authorization,content-type')
try:
    with urllib.request.urlopen(req) as r:
        print('OPTIONS status', r.status)
        print('CORS headers:', {k:v for k,v in r.getheaders() if 'Access-Control' in k})
except Exception as e:
    print('OPTIONS failed', e)
