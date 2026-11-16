"""Generate the Max Headroom-style avatar with FLUX-1-schnell (one-off script)."""
import base64
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["DEEPINFRA_API_KEY"]
MODEL = os.environ.get("IMAGE_MODEL", "black-forest-labs/FLUX-1-schnell")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "max.png")

# Description avoids using the character's trademark name directly
PROMPT = (
    "1980s style computer-generated television host head and shoulders, retro CGI "
    "vintage broadcast look, slicked-back hair, dark reflective sunglasses-like eyes, "
    "giant chrome metallic grin, wearing a shiny suit with a loosened tie,azzi "
    "bluish-gray studio lighting, subtle CRT scanlines and VHS video distortion "
    "artifacts, background of abstract dark blue TV-studio set with glowing grid, "
    "slightly creepy humorous charisma, square composition, digital broadcast look"
)

PROMPT = PROMPT.replace(",azzi", "")

payload = {
    "model": MODEL,
    "prompt": PROMPT,
    "num_inference_steps": 4,
    "image_size": "square_hd",
}

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

resp = httpx.post(
    f"https://api.deepinfra.com/v1/inference/{MODEL}", headers=headers, json=payload, timeout=120
)
resp.raise_for_status()
data = resp.json()

img_bytes = None
for key in ("image", "images"):
    val = data.get(key)
    if isinstance(val, str) and val.startswith("data:image"):
        img_bytes = base64.b64decode(val.split(",", 1)[1])
    elif isinstance(val, list) and val:
        first = val[0]
        if isinstance(first, str) and first.startswith("data:image"):
            img_bytes = base64.b64decode(first.split(",", 1)[1])
if img_bytes is None:
    url = data.get("image_url") or data.get("images_url", [None])[0]
    if not url:
        print("Unexpected response:", json.dumps(data)[:2000])
        sys.exit(1)
    img_bytes = httpx.get(url, timeout=60).content

with open(OUT, "wb") as f:
    f.write(img_bytes)
print("Saved", OUT, len(img_bytes), "bytes")
