const transcriptEl = document.getElementById("transcript");
const form = document.getElementById("text-form");
const input = document.getElementById("text-input");
const micBtn = document.getElementById("mic");
const muteBtn = document.getElementById("mute");
const statusEl = document.getElementById("status");
const notesListEl = document.getElementById("notes-list");
const noteForm = document.getElementById("note-form");
const noteInput = document.getElementById("note-input");
const stageEl = document.querySelector(".stage");
const avatarFrame = document.querySelector(".avatar-frame");

let history = [];
let muted = false;
let noteQueue = []; // notes Max was asked to save while we watch for them

// ---------- helpers ----------
function scrollTranscript() {
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function setStatus(text) {
  statusEl.textContent = "ON AIR • " + text;
}

function addBubble(cls, text) {
  const div = document.createElement("div");
  div.className = cls;
  div.textContent = text;
  transcriptEl.appendChild(div);
  scrollTranscript();
}

function setSpeaking(on) {
  stageEl.classList.toggle("speaking-frame-jitter", on);
  avatarFrame.classList.toggle("speaking", on);
}

// ---------- chat ----------
async function send(text) {
  if (!text.trim()) return;
  addBubble("user", text);
  history.push({ role: "user", content: text });

  setStatus("Max is d-d-dialing in...");
  setSpeaking(false);

  // streaming max bubble
  const maxDiv = document.createElement("div");
  maxDiv.className = "max";
  transcriptEl.appendChild(maxDiv);
  let reply = "";

  try {
    const resp = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history, speak: !muted }),
    });
    if (!resp.ok || !resp.body) throw new Error((await resp.json()).detail || resp.statusText);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let streamErr = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const line = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") continue;
        try {
          const obj = JSON.parse(payload);
          if (obj.t) { reply += obj.t; maxDiv.textContent = "MAX: " + reply; scrollTranscript(); }
          if (obj.error) streamErr = obj.error;
        } catch {}
      }
    }
    if (!reply && streamErr) throw new Error(streamErr);

    history.push({ role: "assistant", content: reply });
    setStatus("ready");
    loadNotes(); // Max may have saved a note

    // voice in the background so text is already on screen
    if (!muted && reply) {
      speakText(reply).catch(() => {});
    }
  } catch (err) {
    if (maxDiv.textContent) { history.push({ role: "assistant", content: maxDiv.textContent.slice(5) }); }
    let msg = err.message || String(err);
    if (msg.includes("429")) msg = "T-too m-many requests! The s-signal's congested... give it a few s-seconds and try again.";
    if (!maxDiv.textContent) transcriptEl.removeChild(maxDiv);
    addBubble("system", "S-signal issue! " + msg);
    setStatus("error");
  }
}

async function speakText(text) {
  setStatus("Max is f-finding his voice...");
  try {
    const resp = await fetch("/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) return;
    const data = await resp.json();
    setSpeaking(true);
    await playAudio(data.audio);
  } finally {
    setSpeaking(false);
    setStatus("ready");
  }
}

function playAudio(base64) {
  return new Promise((resolve) => {
    const blob = base64ToBlob(base64, "audio/mpeg");
    const audio = new Audio(URL.createObjectURL(blob));
    audio.onended = resolve;
    audio.onerror = resolve;
    audio.play().catch(resolve);
  });
}

function base64ToBlob(b64, type) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type });
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  send(input.value);
  input.value = "";
});

// ---------- mic recording (Web Audio) ----------
let mediaStream = null;
let recorder = null;
let chunks = [];

async function startRecording() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(mediaStream);
    chunks = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      mediaStream.getTracks().forEach((t) => t.stop());
      if (blob.size > 1000) {
        setStatus("transcribing...");
        const fd = new FormData();
        fd.append("file", blob, "speech.webm");
        try {
          const resp = await fetch("/speech", { method: "POST", body: fd });
          if (!resp.ok) {
            let detail = "STT failed";
            try { detail = (await resp.json()).detail || detail; } catch {}
            throw new Error(detail);
          }
          const data = await resp.json();
          if (data.text) {
            send(data.text);
          } else {
            addBubble("system", "N-no signal. Say-ay that again?");
            setStatus("ready");
          }
        } catch (err) {
          addBubble("system", "M-mic malfunction! " + err.message);
          setStatus("ready");
        }
      } else {
        setStatus("ready");
      }
    };
    recorder.start();
    micBtn.classList.add("recording");
    setStatus("recording... release to send");
  } catch (err) {
    addBubble("system", "Can't reach the m-mic: " + err.message);
  }
}

function stopRecording() {
  if (recorder && recorder.state === "recording") {
    recorder.stop();
    micBtn.classList.remove("recording");
  }
}

micBtn.addEventListener("mousedown", startRecording);
micBtn.addEventListener("mouseup", stopRecording);
micBtn.addEventListener("mouseleave", () => {
  if (micBtn.classList.contains("recording")) stopRecording();
});
// touch support
micBtn.addEventListener("touchstart", (e) => { e.preventDefault(); startRecording(); });
micBtn.addEventListener("touchend", (e) => { e.preventDefault(); stopRecording(); });

// Space bar: hold to talk
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !e.repeat && document.activeElement !== input
      && document.activeElement !== noteInput && !muted) startRecording();
});
document.addEventListener("keyup", (e) => {
  if (e.code === "Space" && micBtn.classList.contains("recording")) stopRecording();
});

// ---------- mute ----------
muteBtn.addEventListener("click", () => {
  muted = !muted;
  muteBtn.classList.toggle("off", muted);
  muteBtn.innerHTML = muted ? "&#128263;" : "&#128266;";
});

// ---------- notes ----------
async function loadNotes() {
  try {
    const resp = await fetch("/notes");
    const notes = await resp.json();
    notesListEl.innerHTML = "";
    for (const n of notes) {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="note-text">${escapeHtml(n.created)} — ${escapeHtml(n.text)}</span>
        <button class="del" data-id="${n.id}" title="delete">&#10005;</button>`;
      notesListEl.appendChild(li);
    }
  } catch {
    // ignore transient failures
  }
}

notesListEl.addEventListener("click", async (e) => {
  if (!e.target.classList.contains("del")) return;
  await fetch("/notes/" + e.target.dataset.id, { method: "DELETE" });
  loadNotes();
});

noteForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = noteInput.value.trim();
  if (!text) return;
  await fetch("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  noteInput.value = "";
  addBubble("system", "Note saved to the prompter.");
  loadNotes();
});

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ---------- boot ----------
loadNotes().then(() => {
  // Max's opening line
  const opener = "W-w-welcome back to the b-broadcast! Wha-what's the s-s-story?";
  addBubble("max", opener);
  setStatus("ready");
});
