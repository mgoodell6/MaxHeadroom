import json
import os
import threading
import time
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NOTES_FILE = DATA_DIR / "notes.json"

_lock = threading.Lock()


def _ensure_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not NOTES_FILE.exists():
        NOTES_FILE.write_text("[]", encoding="utf-8")


def load_notes() -> list[dict[str, Any]]:
    _ensure_file()
    with _lock:
        try:
            return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []


def _save(notes: list[dict[str, Any]]) -> None:
    _ensure_file()
    NOTES_FILE.write_text(
        json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_note(text: str) -> dict[str, Any]:
    notes = load_notes()
    note = {
        "id": f"{int(time.time() * 1000)}",
        "text": text.strip(),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    notes.append(note)
    with _lock:
        _save(notes)
    return note


def delete_note(note_id: str) -> bool:
    notes = load_notes()
    remaining = [n for n in notes if n.get("id") != note_id]
    if len(remaining) == len(notes):
        return False
    with _lock:
        _save(remaining)
    return True


def notes_as_context() -> str:
    notes = load_notes()
    if not notes:
        return "No notes saved yet."
    lines = [f"- [{n['created']}] {n['text']}" for n in notes[-50:]]
    return "\n".join(lines)
