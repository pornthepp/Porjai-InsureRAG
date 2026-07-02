import contextlib
import json
import queue
import threading
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph_builder import build_graph
from chat_service import answer_question

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph = build_graph()

# session_id -> {"cache": {...}, "conversation": {...}}
_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"cache": {}, "conversation": {}}
    return _sessions[session_id]


class ChatRequest(BaseModel):
    sessionId: str
    question: str


class _QueueWriter:
    """ตัวรับแทน stdout: ส่งทุกบรรทัดที่ print() ออกมาจาก answer_question เข้า queue ทีละบรรทัด"""

    def __init__(self, q: "queue.Queue"):
        self._q = q
        self._buffer = ""

    def write(self, text: str):
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._q.put(("log", line))

    def flush(self):
        pass


def _run_pipeline(question: str, session: dict, q: "queue.Queue"):
    writer = _QueueWriter(q)
    try:
        with contextlib.redirect_stdout(writer):
            answer = answer_question(
                question,
                _graph,
                session["cache"],
                session["conversation"],
            )
        q.put(("done", answer))
    except Exception as exc:  # noqa: BLE001 - surface any pipeline failure to the client
        q.put(("error", str(exc)))


@app.post("/api/chat")
def chat(req: ChatRequest):
    session = _get_session(req.sessionId)
    q: "queue.Queue" = queue.Queue()

    thread = threading.Thread(
        target=_run_pipeline, args=(req.question, session, q), daemon=True
    )
    thread.start()

    def event_stream():
        while True:
            kind, payload = q.get()
            yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"
            if kind in ("done", "error"):
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/session")
def new_session():
    return {"sessionId": str(uuid.uuid4())}


@app.get("/api/health")
def health():
    return {"status": "ok"}
