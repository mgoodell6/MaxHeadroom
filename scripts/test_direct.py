import os
import sys

import httpx
from dotenv import load_dotenv

sys.path.insert(0, ".")

load_dotenv()
key = os.environ["DEEPINFRA_API_KEY"]
print("key starts:", key[:4], "len:", len(key))

payload = {
    "model": "meta-llama/Llama-3.3-70B-Instruct",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 10,
}
for url in (
    "https://api.deepinfra.com/v1/openai/chat/completions",
    "https://api.deepinfra.com/openai/chat/completions",
):
    r = httpx.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=60)
    print(url, r.status_code, r.text[:200])
