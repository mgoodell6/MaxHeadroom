"""Shared DeepInfra request helper with retry/backoff for rate limits."""
import asyncio
import os

import httpx

RETRYABLE = {408, 429, 500, 502, 503, 504}


def _headers(for_files: bool = False) -> dict:
    headers = {}
    api_key = os.environ.get("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set. Add it to .env")
    headers["Authorization"] = f"Bearer {api_key}"
    # httpx must set multipart Content-Type itself; pinning application/json breaks uploads
    if not for_files:
        headers["Content-Type"] = "application/json"
    return headers


async def post_with_retry(
    url: str, *, json: dict | None = None, files=None, data=None,
    timeout: float = 60, max_retries: int = 4,
) -> httpx.Response:
    """POST with exponential backoff on 429/5xx, honoring Retry-After."""
    delay = 1.0
    headers = _headers(for_files=files is not None)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries + 1):
            resp = await client.post(url, headers=headers, json=json, files=files, data=data)
            if resp.status_code in RETRYABLE and attempt < max_retries:
                wait = delay
                retry_after = resp.headers.get("retry-after")
                if retry_after:
                    try:
                        wait = max(wait, float(retry_after))
                    except ValueError:
                        pass
                await asyncio.sleep(wait)
                delay = min(delay * 2, 15)
                continue
            resp.raise_for_status()
            return resp
    return resp  # pragma: no cover
