import httpx

r = httpx.post(
    "http://127.0.0.1:8000/chat",
    json={"history": [{"role": "user", "content": "hi"}], "speak": False},
    timeout=120,
)
print(r.status_code, r.text[:300])
