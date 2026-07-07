import contextlib
import json
import logging
import os
import queue
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graph_builder import build_graph
from chat_service import answer_question

logger = logging.getLogger("backend.main")

app = FastAPI()

# อ่าน allowed origin จาก env เผื่อรัน frontend คนละพอร์ต/โฮสต์ (เช่น deploy จริง)
# ถ้าไม่ตั้งค่า ใช้ default เดิมคือ dev server ของ Vite (http://localhost:5173)
# รองรับหลาย origin คั่นด้วย comma
_allowed_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [
    origin.strip() for origin in _allowed_origins_env.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph = build_graph()

# ตรวจตอน startup ว่ามี OPENROUTER_API_KEY ไหม (generator/router/rewriter/grader ทุกตัว
# ต้องใช้ key นี้เรียก LLM) ถ้าไม่มี ไม่ abort process (ยังให้ offline gate/router/cache
# ทำงานต่อได้) แต่ log ข้อความ actionable ชัดเจน และให้ /api/health รายงานสถานะจริง
# ห้าม print ค่า key เอง (ไม่ log ค่า secret ใดๆ)
_config_ready = bool(os.getenv("OPENROUTER_API_KEY"))

if not _config_ready:
    logger.warning(
        "OPENROUTER_API_KEY ไม่ถูกตั้งค่า — คำถามที่ต้องใช้ LLM (router/grader/generator) "
        "จะล้มเหลวตอน request จริง กรุณาตั้งค่า OPENROUTER_API_KEY ใน .env หรือ environment "
        "ก่อนรัน backend"
    )

# session_id -> {"cache": {...}, "conversation": {...}}
# ใช้ OrderedDict เป็น LRU cache กัน RAM รั่วถ้ามี sessionId มั่วเข้ามาไม่จำกัด
# (spam sessionId ใหม่ทุก request) — เกิน MAX_SESSIONS แล้วเก่าสุดจะถูก evict ทิ้ง
MAX_SESSIONS = 500
_sessions: "OrderedDict[str, dict]" = OrderedDict()

# sys.stdout เป็น global ระดับ process แต่ _run_pipeline ใช้ contextlib.redirect_stdout
# เพื่อดัก log ต่อ request ถ้ามีสอง request วิ่งพร้อมกัน (เช่น FastAPI threadpool)
# การ enter/exit ของ redirect_stdout ที่ทับซ้อนกันข้าม thread จะทำให้ log ปนกันหรือหาย
# ล็อกนี้ serialize การเรียก answer_question (รวม redirect_stdout) ให้รันได้ทีละ request
# ยอมรับได้เพราะทั้งระบบใช้ embedding model + graph ตัวเดียวร่วมกันอยู่แล้ว (ไม่ได้ทำให้ช้าลงจริง)
_pipeline_lock = threading.Lock()


def _get_session(session_id: str) -> dict:
    if session_id in _sessions:
        _sessions.move_to_end(session_id)
        return _sessions[session_id]

    _sessions[session_id] = {"cache": {}, "conversation": {}}
    if len(_sessions) > MAX_SESSIONS:
        _sessions.popitem(last=False)  # evict ตัวเก่าสุด (least-recently-used)
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


MIN_THINK_SECONDS = 2.0


def _run_pipeline(question: str, session: dict, q: "queue.Queue"):
    writer = _QueueWriter(q)
    start_time = time.monotonic()
    try:
        with _pipeline_lock:
            with contextlib.redirect_stdout(writer):
                answer = answer_question(
                    question,
                    _graph,
                    session["cache"],
                    session["conversation"],
                )

        # บังคับให้ใช้เวลาคิดขั้นต่ำ MIN_THINK_SECONDS ต่อคำถาม (กันคำตอบ offline/cache
        # ที่เร็วมากจนดูไม่เป็นธรรมชาติ) — sleep อยู่นอก _pipeline_lock เสมอ ไม่งั้น delay
        # ปลอมๆ นี้จะไปบล็อก session อื่นที่รอคิวอยู่โดยไม่จำเป็น
        elapsed = time.monotonic() - start_time
        if elapsed < MIN_THINK_SECONDS:
            time.sleep(MIN_THINK_SECONDS - elapsed)

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
    if not _config_ready:
        return {
            "status": "degraded",
            "config_ready": False,
            "detail": "OPENROUTER_API_KEY is not set; LLM-backed calls will fail",
        }
    return {"status": "ok", "config_ready": True}


# เสิร์ฟ React build (frontend/dist) จาก process เดียวกันตอน production
# (ตอน dev ใช้ Vite dev server แยกพอร์ต ไม่มีโฟลเดอร์ dist อยู่ mount ข้ามไปเฉยๆ)
# ต้อง mount หลัง route API ทั้งหมดเสมอ ไม่งั้นจะไป intercept "/api/*" ก่อนถึง route จริง
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
