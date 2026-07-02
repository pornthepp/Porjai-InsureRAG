# RAG Answer UAT — 2026-07-02

## สภาพแวดล้อม

- ทดสอบผ่าน `answer_question()` และ LangGraph จริง
- Retrieval ใช้ ChromaDB แบบ cosine
- Router, rewriter, retrieval grader, generator และ hallucination grader ใช้ `google/gemma-3-4b-it`

## ผลทดสอบ

| กรณี | ผล | สิ่งที่พบ |
|---|---|---|
| `ประกันชีวิต` → `การเคลม` | ผ่าน | พบ 2 chunks ตอบวงเงิน 1,000,000 บาทและอุบัติเหตุเพิ่ม 100% ตรงไฟล์ข้อมูล แต่คำว่า “ประสบการณ์การเคลม” ไม่เป็นธรรมชาติ |
| บริบทชีวิต → `ต้องใช้เอกสารอะไรบ้าง` | ไม่ผ่าน | Offline Gate ตอบว่านอกเรื่องก่อนนำ category เดิมมาเติม ทั้งที่ไฟล์มีรายการเอกสารเคลม |
| `ประกันรถยนต์คุ้มครองน้ำท่วมไหม` | ผ่าน | พบ 2 chunks และตอบว่าชั้น 1 คุ้มครองตามเงื่อนไขกรมธรรม์ |
| `ประกันชีวิตเปลี่ยนผู้รับประโยชน์ได้ไหม` | ไม่ผ่าน | ไฟล์ไม่มีข้อมูลการเปลี่ยนผู้รับประโยชน์ Hallucination grader ตัดสินว่าไม่ grounded 2 รอบ แต่ graph ยังคืนคำตอบล่าสุดให้ผู้ใช้ |
| `ประกันรถยนต์ 2+ กับ 3+ ต่างกันอย่างไร` | error | Gemma คืน `content=None` จาก retrieval grader แล้วโค้ดเรียก `.strip()` ทำให้ `AttributeError` |

## สรุปช่องโหว่

1. Offline Gate ทำงานก่อน conversation context จึงปัดคำถามต่อเนื่องบางคำผิด
2. การอ่านผลจาก LLM ไม่มีการรองรับ `None` หรือข้อความผิดรูปแบบ
3. เมื่อ hallucination ไม่ผ่านครบจำนวน retry ระบบยังปล่อยคำตอบที่ไม่ grounded
4. Unit tests 47 ข้อผ่าน แต่ยังไม่มี integration tests ครอบคลุมสามกรณีด้านบน

## ลำดับแก้ที่แนะนำ

1. รองรับ `None` และ API error ใน grader ทุกตัว
2. เมื่อ hallucination ไม่ผ่านครบ retry ให้คืน fallback แทนคำตอบล่าสุด
3. ให้ context-aware follow-up ผ่าน Offline Gate อย่างปลอดภัย
4. เพิ่ม integration tests แล้วรัน UAT ชุดเดิมซ้ำ
