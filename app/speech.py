import base64
import os

from .deepinfra import post_with_retry
from dotenv import load_dotenv

load_dotenv()

INFERENCE_BASE = "https://api.deepinfra.com/v1/inference"

MAX_VOICE_DESCRIPTION = (
    "A male late-night TV talk show host voice from the 1980s: smooth, confident, "
    "warmly sardonic, faintly synthetic and buzzy like an old analog broadcast, "
    "energetic and charismatic with a slight smirk in every word."
)


async def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Speech-to-text via Whisper on DeepInfra."""
    model = os.environ.get("STT_MODEL", "openai/whisper-large-v3-turbo")
    resp = await post_with_retry(
        "https://api.deepinfra.com/v1/openai/audio/transcriptions",
        files={"file": ("speech.webm", audio_bytes, content_type)},
        data={"model": model},
        timeout=60,
    )
    return resp.json().get("text", "").strip()


async def synthesize_speech(text: str) -> bytes:
    """Text-to-speech via Qwen3-TTS-VoiceDesign on DeepInfra. Returns audio bytes."""
    model = os.environ.get("TTS_MODEL", "Qwen/Qwen3-TTS-VoiceDesign")
    payload = {
        "model": model,
        "input": text,
        "voice": MAX_VOICE_DESCRIPTION,
        "response_format": "mp3",
    }
    resp = await post_with_retry(
        f"{INFERENCE_BASE}/{model}", json=payload, timeout=120
    )
    ct = resp.headers.get("content-type", "")
    if "application/json" in ct:
        data = resp.json()
        audio = data.get("audio") or data.get("data") or ""
        if "," in audio and audio.split(",", 1)[0].endswith("base64"):
            audio = audio.split(",", 1)[1]
        return base64.b64decode(audio)
    return resp.content
