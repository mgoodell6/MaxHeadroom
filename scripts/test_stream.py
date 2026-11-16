import json
import time

import httpx

payload = {
    "history": [
        {"role": "user", "content": "Tell me one quick joke, Max, one sentence only."}
    ],
    "speak": False,
}
t0 = time.time()
first = None
full = ""
with httpx.stream(
    "POST", "http://127.0.0.1:8000/chat/stream", json=payload, timeout=120
) as r:
    for line in r.iter_lines():
        if line.startswith("data: ") and line[6:] != "[DONE]":
            o = json.loads(line[6:])
            if "t" in o and first is None:
                first = time.time() - t0
            full += o.get("t", "")
print("first token:", round(first, 2) if first else None, "s; total:", round(time.time() - t0, 2), "s")
print(full[:160])
