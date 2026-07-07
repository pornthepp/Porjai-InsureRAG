# Porjai InsureRAG

RAG chatbot สำหรับตอบคำถามประกันรถยนต์และประกันชีวิต ออกแบบให้ตอบเฉพาะเรื่องที่มีข้อมูลจริง ไม่เดา และเรียก LLM เท่าที่จำเป็นเท่านั้น

## แนวคิดหลัก

1. ตอบเรื่องประกันรถยนต์และประกันชีวิตได้จากข้อมูลในระบบ
2. ไม่ตอบมั่ว — ถ้าข้อมูลไม่พอ ให้ถามกลับหรือบอกตรง ๆ ว่าไม่รู้
3. ลดการเรียก LLM ให้มากที่สุด (กรองด้วย offline gate/router/cache ก่อนเสมอ)
4. ให้ flow การสนทนาเป็นธรรมชาติสำหรับลูกค้า

ลำดับการทำงาน: กรองก่อน → จัดหมวดคำถามก่อน → ค้นข้อมูล (retrieval) เมื่อจำเป็น → ให้ LLM ตอบเฉพาะตอนมีข้อมูลพอ → ถ้าข้อมูลไม่พอ ห้ามเดา

## โครงสร้างโปรเจกต์

- `backend/` — FastAPI server (`main.py`) เปิด endpoint `/api/chat`, `/api/session`, `/api/health`
- `frontend/` — React + Vite UI
- `data/` — เอกสารประกันภัยต้นฉบับ (`.txt`) ที่ใช้ ingest เข้า vector database
- `graph_builder.py`, `graph_nodes.py`, `graph_state.py` — LangGraph pipeline ของ RAG
- `offline_gate.py`, `query_router.py`, `query_rewriter.py`, `retrieval_pipeline.py`, `retrieval_grader.py`, `hallucination_grader.py`, `generator.py` — แต่ละขั้นตอนของ pipeline (กรอง, จัดหมวด, ปรับคำถาม, ค้นข้อมูล, ตรวจคุณภาพ, ตอบ)
- `ingest.py` — สร้าง vector database จาก `data/`
- `test/` — unit tests
- `docs/` — spec และ plan ของแต่ละฟีเจอร์ (แบบ TDD)

## เริ่มต้นใช้งาน

ดูขั้นตอนละเอียดที่ [howtorun.md](howtorun.md)

สรุปสั้น ๆ:

```bash
pip install -r requirements.txt
python ingest.py                      # สร้าง vector db ครั้งแรก
uvicorn backend.main:app --reload     # รัน backend

cd frontend && npm install && npm run dev   # รัน frontend
```

ต้องตั้งค่า `OPENROUTER_API_KEY` ใน `.env` สำหรับคำถามที่ต้องใช้ LLM (router/grader/generator)

## เอกสารเพิ่มเติม

- [AGENT.md](AGENT.md) — กติกาและเป้าหมายของโปรเจกต์สำหรับผู้ช่วยเขียนโค้ด
- [Rule.md](Rule.md) — กติกาการสนทนาของ chatbot (เมนู, state, น้ำเสียง)
- [WORKFLOW.md](WORKFLOW.md) — ขั้นตอนการทำงาน/พัฒนาโปรเจกต์
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — ประวัติการตัดสินใจและการเปลี่ยนแปลงของโปรเจกต์
- `docs/specs/`, `docs/plans/`, `docs/uat/` — spec, แผนงาน และผลทดสอบ UAT ของแต่ละฟีเจอร์
