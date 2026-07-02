# Project Context

## 2026-06-30 — อนุมัติ Hybrid Router

- ผู้ใช้เลือก Hybrid Router: offline ก่อน และเรียก LLM เฉพาะเมื่อจำแนกคำถามประกันไม่ได้
- เพิ่ม design: docs/specs/2026-06-30-hybrid-router-design.md
- เพิ่มแผน TDD: docs/plans/2026-06-30-hybrid-router.md
- อัปเดต AGENT.md ให้ Hybrid Router เป็นกติกาล่าสุดของโปรเจกต์
- ยังไม่ได้แก้ production code
- งานถัดไป: เพิ่ม failing test สำหรับ ซ่อมห้างกับซ่อมอู่ต่างกันยังไง
- โฟลเดอร์โปรเจกต์ยังไม่มี .git จึงยัง commit ไม่ได้

## 2026-07-02 — Rule.md แบบเมนูนำทาง

- ผู้ใช้ขอเก็บรูปแบบผู้ช่วยบริการลูกค้าแบบเมนูหลายชั้นเป็นกติกาถาวร
- สร้าง Rule.md: welcome-first, menu-guided, free-text always available, state switching, offline-first และลำดับบริบท
- อัปเดต AGENT.md ให้ต้องอ่านและทำตาม Rule.md ก่อนแก้หรือรีวิว chatbot
- ระบุชัดว่าเป็นรูปแบบที่สกัดจากตัวอย่างผู้ใช้ ไม่ใช่เอกสารภายในของ True
## 2026-07-02 — แก้ response delay

- แก้ app.py: ลดเวลารอขั้นต่ำจาก 120 วินาทีเป็น 2 วินาที
- ยืนยันว่า offline answer ใช้เวลาจริงประมาณ 1.2 ms และสาเหตุความช้าคือ artificial delay
- ตรวจ syntax ด้วย python -m py_compile app.py ผ่าน
## 2026-07-02 — เพิ่ม process logs สำหรับ offline flow

- สาเหตุ: เมนูและ canned response ตอบก่อนเข้า graph จึงไม่มี stdout และช่องกระบวนการคิดว่าง
- แก้ chat_service.py ให้ส่งสถานะ offline_menu, offline_gate, context และ cache_hit
- แก้ ui/components.py ให้ render สถานะใหม่เป็น Process cards
- ใช้ ASCII raw tags เพื่อรองรับ Windows cp1252; UI ยังแสดงภาษาไทยและไอคอน
- เพิ่ม test/test_process_logs.py; Process 2/2, Cache 2/2, Chat service 10/10 ผ่าน
## 2026-07-02 — แก้เมนูคำว่า ประกัน เป็นสองระดับ

- สาเหตุ: GENERAL_CLARIFY_RESPONSE รวมประเภทประกันและหัวข้อย่อยไว้ใน OPTIONS เดียว
- แก้ระดับแรกให้มีเฉพาะประกันรถยนต์และประกันชีวิต
- หัวข้อความคุ้มครอง เบี้ย การเคลม และโปรโมชั่นยังแสดงหลังเลือกประเภท
- เพิ่ม regression test; Chat service 11/11 และ Process logs 2/2 ผ่าน
## 2026-07-02 — แก้ retrieval ให้ใช้ cosine

- ต้นเหตุ: คำค้น `ประกันชีวิต การเคลม` พบ `LIFE-001` แต่ L2 distance เท่ากับ 4.83 สูงกว่า threshold 1.0 จึงถูกทิ้งก่อนเข้า grader
- แก้ `ingest.py` และ `reindex.py` ให้ collection ใช้ `hnsw:space = cosine`
- แก้ `retrieval_pipeline.py` ให้ threshold เป็น cosine distance 0.5
- เพิ่ม `test/test_ingest_config.py` และปรับ regression test ใน `test/test_retrieval_pipeline.py`
- rebuild `my_vectordb`: 12 chunks (รถยนต์ 6, ชีวิต 6)
- ตรวจคำจริง: `LIFE-001` distance 0.278 และผ่าน threshold
- รัน unit tests ทั้งหมดด้วย UTF-8 และ offline model cache: 46 tests ผ่านทั้งหมด
## 2026-07-02 — เปลี่ยนโมเดลและทดสอบคำตอบจริง

- เปลี่ยน `query_rewriter.py`, `retrieval_grader.py` และ `hallucination_grader.py` จาก GPT-4o-mini เป็น `google/gemma-3-4b-it`
- เพิ่ม `test/test_model_config.py`; unit tests 47 ข้อผ่าน
- UAT ผ่าน: เคลมประกันชีวิต และประกันรถยนต์คุ้มครองน้ำท่วม
- UAT ไม่ผ่าน: follow-up เรื่องเอกสารถูก Offline Gate ปัด, hallucination ครบ retry แล้วยังถูกส่งออก, retrieval grader ไม่รองรับ `content=None`
- รายงาน: `docs/uat/2026-07-02-rag-answer-uat.md`