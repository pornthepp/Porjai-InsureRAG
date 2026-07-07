# วิธีรันโปรเจกต์ (How to Run)

โปรเจกต์นี้มี 2 ส่วน: **backend** (Python/FastAPI + RAG pipeline) และ **frontend** (React/Vite)

## สิ่งที่ต้องมีก่อน (Prerequisites)

- Python 3.9+
- Node.js 18+ และ npm
- OpenRouter API key (ใช้เรียก LLM สำหรับ router/grader/generator) — สมัครได้ที่ https://openrouter.ai

## 1) ตั้งค่า Backend

```bash
# สร้างและเปิดใช้งาน virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# ติดตั้ง dependencies
pip install -r requirements.txt
```

สร้างไฟล์ `.env` ที่ root ของโปรเจกต์:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_API_URL=https://openrouter.ai/api/v1
```

### สร้าง Vector Database (ทำครั้งแรกเท่านั้น)

ข้อมูลประกันภัยอยู่ใน `data/*.txt` ต้องรัน ingest ก่อนถึงจะค้นหา (retrieve) เอกสารได้:

```bash
python ingest.py
```

คำสั่งนี้จะสร้างโฟลเดอร์ `my_vectordb/` เก็บ embeddings (ไม่ commit เข้า git เพราะอยู่ใน `.gitignore`)

### รัน Backend server

```bash
uvicorn backend.main:app --reload --port 8000
```

ตรวจสอบว่าพร้อมใช้งานที่ http://localhost:8000/api/health

## 2) ตั้งค่า Frontend

```bash
cd frontend
npm install
npm run dev
```

เปิดเบราว์เซอร์ที่ http://localhost:5173 (Vite dev server จะยิง request ไปที่ backend พอร์ต 8000)

## 3) รัน Tests (ฝั่ง backend)

```bash
python -m unittest discover test
```

## หมายเหตุ

- ถ้าไม่ตั้งค่า `OPENROUTER_API_KEY` backend ยังรันได้ แต่คำถามที่ต้องใช้ LLM (router/grader/generator) จะล้มเหลว — คำถามที่ตอบได้จาก offline gate/cache จะยังทำงานปกติ
- production build: รัน `npm run build` ใน `frontend/` จะได้ `frontend/dist/` ซึ่ง backend จะ mount ให้อัตโนมัติถ้าโฟลเดอร์นี้มีอยู่
