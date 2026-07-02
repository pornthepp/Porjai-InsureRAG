# Cosine Retrieval Design

## ปัญหา

คำค้น `ประกันชีวิต การเคลม` พบ `LIFE-001` เป็นอันดับแรก แต่ ChromaDB คืนค่า L2 distance `4.83` ขณะที่ระบบรับไม่เกิน `1.0` เอกสารจึงถูกทิ้งก่อนเข้า grader และ generator

## แบบแก้

- สร้าง collection ด้วย `hnsw:space = cosine`
- ใช้ threshold ที่มีความหมายกับ cosine distance
- rebuild collection เพราะ metric ของ collection เดิมเปลี่ยนภายหลังไม่ได้
- เพิ่ม regression test ยืนยัน configuration และการรับเอกสารที่ใกล้
- ทดสอบคำจริง `ประกันชีวิต การเคลม` หลัง rebuild

## ขอบเขต

แก้เฉพาะ retrieval metric และเกณฑ์กรอง ไม่เปลี่ยน router, conversation flow หรือข้อความตอบ

## เกณฑ์ผ่าน

- `LIFE-001` ผ่านตัวกรองสำหรับคำค้นเรื่องเคลมประกันชีวิต
- เอกสารที่ไกลยังถูกปฏิเสธ
- unit test ทั้งหมดผ่าน
