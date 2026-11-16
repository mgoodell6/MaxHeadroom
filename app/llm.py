import os
from collections.abc import AsyncIterator

import httpx

from .deepinfra import _headers, post_with_retry
from .prompt import build_messages
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.deepinfra.com/v1/openai"

TIMEOUT = httpx.Timeout(30, read=120)


async def chat(history: list, notes_context: str) -> str:
    model = os.environ.get("CHAT_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    payload = {
        "model": model,
        "messages": build_messages(history, notes_context),
        "max_tokens": 600,
        "temperature": 0.9,
        "presence_penalty": 0.4,
        "stream": False,
    }
    resp = await post_with_retry(f"{API_BASE}/chat/completions", json=payload, timeout=120)
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def chat_stream(history: list, notes_context: str) -> AsyncIterator[str]:
    """Yield reply text deltas as they arrive."""
    model = os.environ.get("CHAT_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    payload = {
        "model": model,
        "messages": build_messages(history, notes_context),
        "max_tokens": 600,
        "temperature": 0.9,
        "presence_penalty": 0.4,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream(
            "POST", f"{API_BASE}/chat/completions", headers=_headers(), json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                chunk = line[len("data: "):]
                if chunk.strip() == "[DONE]":
                    break
                try:
                    import json as _json

                    obj = _json.loads(chunk)
                except ValueError:
                    continue
                choice = (obj.get("choices") or [{}])[0]
                piece = (choice.get("delta") or {}).get("content")
                if piece:
                    yield piece
