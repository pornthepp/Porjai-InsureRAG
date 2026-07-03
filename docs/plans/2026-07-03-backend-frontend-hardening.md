# แผนแก้ไขความเสี่ยง Backend (FastAPI) + Frontend (React)

วันที่: 2026-07-03

## Context

เพิ่งย้ายหน้าบ้านจาก Streamlit มาเป็น React + FastAPI (`backend/main.py`, `frontend/`)
เพื่อแก้บั๊ก "การ์ดโคลน" ที่เกิดจาก JS hack เจาะ iframe ใน Streamlit เดิม
โค้ด pipeline หลัก (`chat_service.py`, `graph_builder.py`, `graph_nodes.py` ฯลฯ) ไม่ถูกแตะ
แต่ **โค้ด wiring ใหม่ยังไม่ผ่านการ review ตามหลักการโปรเจกต์** (AGENT.md / Rule.md)
และยังไม่มี test คุม ทั้งที่โปรเจกต์บังคับ test-first

เอกสารนี้คือ requirement สำหรับปิดจุดเสี่ยง ให้แก้ทีละข้อ (ตาม AGENT.md: "แก้ทีละชั้น")
และเขียน test ก่อน/พร้อมแก้ทุกข้อที่ทำได้ (ตาม Rule.md เกณฑ์ตรวจรับ: "ทุกพฤติกรรมสำคัญมี unit test")

หลักการที่ยึด: flow สำคัญกว่า model, ไม่เพิ่มการเรียก LLM, ต้อง honest เรื่อง failure,
พฤติกรรม pipeline เดิมห้ามเปลี่ยน (behavior-preserving)

---

## R1 — [CRITICAL] pipeline execution ไม่ thread-safe (stdout redirect + state race)

**หลักฐาน:** `backend/main.py:59-68` — `_run_pipeline` รันใน thread แล้วใช้
`contextlib.redirect_stdout(writer)` แต่ `sys.stdout` เป็น global ระดับ process
FastAPI รัน sync endpoint (`def chat`) ใน threadpool → ถ้ามี request `/api/chat`
พร้อมกัน 2 อัน (หลายแท็บ/หลายคน) จะเกิด:
1. สอง thread แทน `sys.stdout` ทับกัน → log บรรทัดของ session A ไหลไป stream ของ session B
2. พอ `with` ของ thread หนึ่งจบ มัน restore stdout เดิม → redirect ของอีก thread หาย log หาย
3. `session["cache"]` / `session["conversation"]` ถูกอ่าน/เขียนพร้อมกัน (dict race)

**ต้องแก้:** ครอบการเรียก `answer_question` (รวมทั้ง block `redirect_stdout`) ด้วย
`threading.Lock` ระดับ module เพื่อ serialize การรัน pipeline ทีละครั้ง
(เหมาะสมเพราะทั้งระบบใช้ embedding model + graph ตัวเดียวร่วมกันอยู่แล้ว)
ห้ามลบ `redirect_stdout` ออก (ยังต้องใช้ดัก log) — แค่ทำให้รันทีละอัน

**Acceptance test:** ยิง 2 request พร้อมกันด้วย sessionId ต่างกัน แล้ว assert ว่า
แต่ละ stream มีแต่ log ของตัวเอง (ไม่ปน) และแต่ละอันได้ done answer ของตัวเอง

---

## R2 — [HIGH] `_sessions` โตไม่จำกัด (memory leak / DoS เล็กๆ)

**หลักฐาน:** `backend/main.py:27-33` — `_sessions` dict ไม่เคย evict
ทุก sessionId ใหม่ (client ส่งอะไรมาก็ได้) สร้าง entry ถาวรที่ถือ cache + conversation
เวลาผ่านไป/โดน spam sessionId มั่ว → RAM รั่ว

**ต้องแก้:** จำกัดจำนวน session ด้วย LRU (เช่น `collections.OrderedDict`,
กำหนด MAX เช่น 500 session, insert แล้วเกินให้ evict ตัวเก่าสุด, access แล้ว move-to-end)
พิจารณา cap ขนาด cache ต่อ session ด้วยถ้าทำได้ง่าย เก็บ in-memory เหมือนเดิม

**Acceptance test:** สร้าง session เกิน MAX แล้ว assert ว่า session เก่าสุดถูก evict,
และการ access session เดิมช่วย refresh ความ recent (ไม่ถูก evict ก่อน)

---

## R3 — [HIGH] backend ไม่มี test เลย (ผิดกติกา test-first)

**หลักฐาน:** AGENT.md ("เพิ่ม test ก่อนหรืออย่างน้อยเพิ่ม test พร้อมกัน"),
Rule.md เกณฑ์ตรวจรับ ("ทุกพฤติกรรมสำคัญมี unit test ก่อนแก้โค้ด")
ไม่มีไฟล์ test ไหนคุม `backend/main.py`

**ต้องแก้:** เพิ่ม `test/test_backend_api.py` (ใช้ `unittest` + `fastapi.testclient.TestClient`
ตามสไตล์เดิม ดูตัวอย่าง `test/test_chat_service.py` ที่ mock ด้วย `FakeGraph`)
ครอบพฤติกรรม:
- (a) คำถามที่เข้า RAG → SSE ส่ง event `log` หลายอัน ตามด้วย event `done` ที่มี answer
- (b) pipeline โยน exception → ได้ event `error` (ไม่ใช่ HTTP 500 หน้าแตก)
- (c) session isolation — 2 sessionId เก็บ conversation/cache แยกกันจริง
- (d) คำถามกว้าง/offline (เช่น "ประกันชีวิต") → ได้ done โดย **ไม่ invoke graph**
  (ยืนยันว่า wiring ไม่ทำให้ต้นทุน LLM รั่ว)

**หมายเหตุ:** ให้ mock ที่ระดับ `answer_question` หรือฉีด FakeGraph ผ่าน seam
เพื่อไม่ต้องโหลดโมเดลจริงตอนเทส TestClient อ่าน SSE ได้จาก `response.text`
(assert รูปแบบ `event: ...` / `data: ...`)

---

## R4 — [MEDIUM] ไม่ fail-fast เมื่อ config หาย + health โกหกว่า ok

**หลักฐาน:** `generator.py:7-10` (และ query_router / query_rewriter / retrieval_grader /
hallucination_grader) อ่าน `OPENROUTER_API_KEY` ด้วย `os.getenv` ตอน import
ถ้า key หาย ความล้มเหลวจะโผล่กลาง request เป็น error string งงๆ ส่งให้ผู้ใช้
(ขัด Rule.md น้ำเสียง "ไม่อ้างว่าตรวจสอบสำเร็จถ้ายังไม่ได้ทำ")
`backend/main.py:99-101` `health()` คืน ok เสมอ

**ต้องแก้:** ตอน startup ตรวจว่ามี `OPENROUTER_API_KEY` ไหม ถ้าไม่มีให้ log ข้อความ
ที่ actionable ชัดเจน (ห้าม print ตัว key) และให้ `/api/health` สะท้อนสถานะ config/model
ว่าพร้อมจริงไหม (เลือกทางใดทางหนึ่ง: abort startup หรือ health รายงาน not-ready)

**Acceptance:** เมื่อ env ไม่มี key → startup log ข้อความชัดว่าต้องตั้งค่าอะไร
และ health สะท้อนสถานะ (มี test เบาๆ ได้ถ้าทำได้โดยไม่โหลดโมเดลจริง)

---

## R5 — [MEDIUM] path ผูกกับ cwd แตกง่ายเมื่อรันจากที่อื่น (behavior-preserving)

**หลักฐาน:** `retrieval_pipeline.py:5,13` — `DB_PATH="./my_vectordb"` อิง cwd
backend เป็น entrypoint ใหม่ ถ้ารันจาก dir อื่น ChromaDB โหลด collection พังตอน import
ด้วย error งงๆ

**ต้องแก้:** resolve `DB_PATH` (และ path data ที่เกี่ยว) ให้อิง project root
(เช่น `Path(__file__).resolve().parent`) แทน cwd ให้รันจากไหนก็ได้ ผลเหมือนเดิม
แก้ชั้นเดียวใน `retrieval_pipeline.py` (และ `ingest.py` ถ้าใช้ค่าเดียวกัน)

**ข้อควรระวัง (risk-guard):** นี่แตะ hot path ของ pipeline ที่ทำงานได้อยู่แล้ว
ต้องรัน **test ทั้งชุด** หลังแก้ ถ้ามีอะไรแดงให้ย้อนกลับทันที ห้ามฝืน
พฤติกรรมเมื่อรันจาก project root ต้องเหมือนเดิมเป๊ะ

**Acceptance:** `python -m unittest` ทั้งชุดยังเขียว, retrieval tests เดิมผ่านหมด

---

## R6 — [LOW] frontend กันกดซ้ำไม่แน่น + SSE ค้าง pending

**หลักฐาน:** `frontend/src/App.tsx` `sendMessage` เช็ค `if (!question.trim() || pending)`
แต่ `pending` อ่านจาก closure เก่า → กด Enter รัวสองทีในเฟรมเดียวอาจผ่าน guard ทั้งคู่
`frontend/src/api.ts` `streamChat` ถ้า stream จบโดยไม่มี event `done`/`error`
ฝั่ง React จะค้าง `pending=true` (input ล็อกถาวร)

**ต้องแก้:** ใช้ ref-based in-flight guard ใน App.tsx กันส่งซ้อน และใน App.tsx
เคลียร์ `pending` ใน finally เสมอแม้ stream จบแบบไม่มี done/error (defensive)
UX ต้องเหมือนเดิม

**Acceptance (manual):** กด Enter รัวสองที ส่ง request เดียว, ถ้า backend ปิด stream
โดยไม่มี done → input กลับมาใช้ได้ ไม่ค้าง

---

## R7 — [LOW] CORS origin hardcoded

**หลักฐาน:** `backend/main.py:19` fix ที่ `http://localhost:5173`

**ต้องแก้:** อ่าน allowed origin จาก env (default `http://localhost:5173`) เผื่อพอร์ต/โฮสต์อื่น

---

## ลำดับงานที่แนะนำ

1. R3 ก่อน (วาง test harness ให้ backend) — แล้วค่อยใช้ test คุมข้ออื่น
2. R1 (critical) พร้อม test concurrency
3. R2 (LRU) พร้อม test
4. R4, R7 (config/health/CORS)
5. R5 (path) — รัน full suite คุม
6. R6 (frontend) — ตรวจด้วย UI จริง

หลังแก้แต่ละข้อ: รัน `python -m unittest` เฉพาะส่วนที่เกี่ยว แล้วรันทั้งชุดปิดท้าย
