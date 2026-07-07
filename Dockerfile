# ---- Stage 1: build React frontend ----
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend + baked-in data ----
FROM python:3.11-slim

WORKDIR /app

# torch แยกติดตั้งก่อนด้วย CPU-only wheel กันดึงเวอร์ชัน CUDA มาโดยไม่ตั้งใจ
# (ใหญ่เกินจำเป็นมากสำหรับ CPU-only ของ HF Spaces free tier)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# โค้ด backend + pipeline (ไม่รวม frontend/, test/, venv/, data ที่ไม่จำเป็น ตาม .dockerignore)
COPY *.py ./
COPY backend/ ./backend/
COPY data/ ./data/

# build ChromaDB ตอน build image เลย (ไม่ต้องรอ ingest ตอน container start ทุกครั้ง)
RUN python ingest.py

# ไฟล์ React ที่ build เสร็จจาก stage 1
COPY --from=frontend-build /frontend/dist ./frontend/dist

# HF Spaces (Docker) รันด้วย user ที่ไม่ใช่ root และคาดหวัง container ฟังพอร์ต 7860
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
