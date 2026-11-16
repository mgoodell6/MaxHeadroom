import httpx

r = httpx.post(
    "http://127.0.0.1:8000/tts",
    json={"text": "H-hello there!"},
    timeout=120,
)
print(r.status_code, r.text[:120])
