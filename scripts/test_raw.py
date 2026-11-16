import json
import sys

import httpx

payload = {"history": [{"role": "user", "content": "Tell me a joke."}], "speak": False}
r = httpx.post("http://127.0.0.1:8000/chat/stream", json=payload, timeout=60)
print(r.status_code, r.text[:500])
sys.exit(0)
