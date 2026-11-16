import json
import os

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import llm, speech
from .notes import add_note, delete_note, load_notes, notes_as_context

load_dotenv()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

app = FastAPI(title="Max Headroom Personal Assistant")


class ChatRequest(BaseModel):
    history: list  # [{role, content}, ...] -- no system messages expected
    speak: bool = True


class NoteAdd(BaseModel):
    text: str


# ---------- Chat / voice ----------

@app.post("/speech")
async def speech_to_text(file: UploadFile = File(...)):
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio upload")
    try:
        text = await speech.transcribe_audio(audio, file.content_type or "audio/webm")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Speech-to-text failed: {exc}") from exc
    return {"text": text}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream reply tokens as server-sent events; one final [DONE]."""
    history = [m for m in req.history if m.get("role") in ("user", "assistant")]
    if not history:
        raise HTTPException(400, "No user message")

    async def event_source():
        try:
            async for piece in llm.chat_stream(history, notes_as_context()):
                yield f"data: {json.dumps({'t': piece})}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/chat")
async def chat(req: ChatRequest):
    history = [m for m in req.history if m.get("role") in ("user", "assistant")]
    content = history[-1]["content"] if history else ""
    if not content:
        raise HTTPException(400, "No user message")
    try:
        reply = await llm.chat(history, notes_as_context())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Chat failed: {exc}") from exc

    result = {"reply": reply, "audio": None}
    if req.speak:
        try:
            audio = await speech.synthesize_speech(reply)
            import base64

            result["audio"] = base64.b64encode(audio).decode("ascii")
        except Exception as exc:  # noqa: BLE001
            # TTS failure shouldn't kill the chat; frontend falls back
            result["audio_error"] = str(exc)
    return result


@app.post("/tts")
async def tts(text: str = Body(..., embed=True)):
    try:
        audio = await speech.synthesize_speech(text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"TTS failed: {exc}") from exc
    import base64

    return {"audio": base64.b64encode(audio).decode("ascii")}


# ---------- Notes ----------

@app.get("/notes")
async def get_notes():
    return load_notes()


@app.post("/notes")
async def post_note(note: NoteAdd):
    if not note.text.strip():
        raise HTTPException(400, "Note text is empty")
    return add_note(note.text)


@app.delete("/notes/{note_id}")
async def remove_note(note_id: str):
    if not delete_note(note_id):
        raise HTTPException(404, "Note not found")
    return {"ok": True}


# ---------- Static frontend ----------

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
