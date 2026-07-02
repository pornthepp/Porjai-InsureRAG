# Cosine Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ให้คำถามเรื่องเคลมประกันชีวิตค้นเอกสารที่มีอยู่ได้ โดยใช้ระยะ cosine ที่ตรงกับ threshold

**Architecture:** กำหนด metric ตอนสร้าง Chroma collection และใช้ค่าคงที่ร่วมกันระหว่าง ingest กับ retrieval จากนั้น rebuild collection และตรวจคำค้นจริง

**Tech Stack:** Python 3.9, unittest, ChromaDB, sentence-transformers

---

### Task 1: ล็อกพฤติกรรมด้วยเทส

**Files:**
- Modify: `test/test_retrieval_pipeline.py`

- [ ] เพิ่มเทสที่ยืนยันว่า cosine distance ที่ใกล้ผ่านเข้า grader และค่าที่ไกลถูกตัด
- [ ] รัน `python -m unittest discover -s test -p "test_retrieval_pipeline.py" -v` และยืนยันว่าเทสใหม่ fail ก่อนแก้ production code

### Task 2: ใช้ cosine metric

**Files:**
- Modify: `ingest.py`
- Modify: `retrieval_pipeline.py`

- [ ] สร้าง collection ด้วย `metadata={"hnsw:space": "cosine"}`
- [ ] เปลี่ยน threshold เป็นค่าที่ใช้กับ cosine distance
- [ ] รันเทสเฉพาะ retrieval ให้ผ่าน

### Task 3: Rebuild และตรวจคำถามจริง

**Files:**
- Rebuild: `my_vectordb`

- [ ] รัน `python ingest.py` เพื่อสร้าง collection ใหม่
- [ ] ค้น `ประกันชีวิต การเคลม` และยืนยันว่า `LIFE-001` ผ่าน threshold
- [ ] รัน `python -m unittest discover -s test -v`

### Task 4: บันทึกงาน

**Files:**
- Modify: `PROJECT_CONTEXT.md`

- [ ] บันทึกต้นเหตุ ไฟล์ที่แก้ คำสั่งที่รัน และผลทดสอบ
