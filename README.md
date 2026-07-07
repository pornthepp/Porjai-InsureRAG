---
title: คุยกับน้องพอใจ
emoji: 🛡️
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# คุยกับน้องพอใจ — Insurance RAG Chatbot

แชทบอทตอบคำถามเรื่องประกันรถยนต์และประกันชีวิต โดยใช้ RAG (Retrieval-Augmented
Generation) ตอบเฉพาะเรื่องที่มีข้อมูลจริงในระบบเท่านั้น

## สถาปัตยกรรม

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI (Python) — ครอบ pipeline RAG (LangGraph) ไว้ข้างใน สตรีม
  log การทำงานแบบ real-time ผ่าน SSE
- **Retrieval**: ChromaDB + sentence-transformers (multilingual embedding)
- **LLM**: เรียกผ่าน OpenRouter (`google/gemma-3-4b-it`)

Deploy เป็น Docker container เดียว — FastAPI เสิร์ฟทั้ง React build (static
files) และ API endpoint (`/api/*`) จากพอร์ตเดียวกัน

## ตั้งค่าก่อนรัน

ต้องตั้งค่า **Secret** ชื่อ `OPENROUTER_API_KEY` ใน Space Settings (ห้าม commit
ไฟล์ .env ลงในโค้ดเด็ดขาด) ไม่งั้นคำถามที่ต้องใช้ LLM (router, grader,
generator) จะล้มเหลว — ตรวจสอบสถานะได้ที่ `/api/health`

## รันเองในเครื่อง (dev)

```bash
# backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python ingest.py       # สร้าง ChromaDB จาก data/*.txt
python -m uvicorn backend.main:app --port 8001

# frontend (terminal แยก)
cd frontend
npm install
npm run dev
```

**ข้อมูลตัวอย่าง:** ตัวเลขราคา/เงื่อนไขใน `data/*.txt` เป็นข้อมูลตัวอย่างสำหรับ
ทดสอบเท่านั้น ไม่ใช่ข้อมูลจริงจากบริษัทประกันใด ต้องแทนที่ด้วยข้อมูลจริงก่อนใช้
งานกับลูกค้าจริง
