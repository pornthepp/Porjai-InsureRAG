import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

GRADER_MODEL = "google/gemma-3-4b-it"

GRADER_SYSTEM_PROMPT = """คุณเป็นกรรมการตรวจสอบความเกี่ยวข้องของเอกสาร
หน้าที่ของคุณคือดูว่า "เนื้อหาเอกสาร" ที่ให้มา สามารถใช้ตอบ "คำถามของลูกค้า" ได้จริงหรือไม่

เกณฑ์การตัดสิน:
- ตอบ "yes" ถ้าเอกสารมีข้อมูลที่ตรงประเด็นกับคำถามจริง สามารถใช้สร้างคำตอบได้
- ตอบ "no" ถ้าเอกสารไม่เกี่ยวข้องกับคำถาม หรือเกี่ยวข้องแค่ผิวเผิน (เช่น มีคำซ้ำกันแต่คนละเรื่อง)

ตอบกลับมาเป็นคำเดียวเท่านั้น: yes หรือ no
ห้ามอธิบายเพิ่ม"""

BATCH_GRADER_SYSTEM_PROMPT = """คุณเป็นกรรมการตรวจสอบความเกี่ยวข้องของเอกสารหลายรายการ

เอกสารแต่ละรายการมีหมายเลข เช่น [0], [1], [2]

ตอบเฉพาะหมายเลขเอกสารที่เกี่ยวข้องกับคำถาม คั่นด้วย comma
ตัวอย่าง: 0,2

ถ้าไม่มีเอกสารใดเกี่ยวข้อง ให้ตอบว่า none
ห้ามอธิบายเพิ่มเติม"""

def grade_documents(question: str, documents: list[dict]) -> list[dict]:
    """ตรวจเอกสารทั้งหมดด้วย LLM เพียงครั้งเดียว"""

    if not documents:
        return []

    numbered_documents = "\n\n".join(
        f"[{index}]\n{doc['text']}"
        for index, doc in enumerate(documents)
    )

    user_prompt = (
        f"คำถาม:\n{question}\n\n"
        f"เอกสาร:\n{numbered_documents}"
    )

    try:
        response = client.chat.completions.create(
            model=GRADER_MODEL,
            messages=[
                {"role": "system", "content": BATCH_GRADER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=30,
        )
        content = response.choices[0].message.content
    except Exception:
        content = None

    answer = (content or "").strip().lower()

    if answer in {"none", "ไม่มี", ""}:
        return []

    selected_indexes = set()

    for value in answer.replace(" ", "").split(","):
        if value.isdigit():
            index = int(value)

            if 0 <= index < len(documents):
                selected_indexes.add(index)

    return [
        doc
        for index, doc in enumerate(documents)
        if index in selected_indexes
    ]

if __name__ == "__main__":
    question = "เมาแล้วขับเคลมประกันได้ไหม"
    test_docs = [
        {"id": "CAR-001", "text": "ผู้เอาประกันสามารถเคลมค่าซ่อมรถได้ในกรณีรถชนทุกประเภท ไม่ว่าจะเป็นฝ่ายผิดหรือไม่ผิด วงเงินคุ้มครองค่าซ่อมตัวรถสูงสุด 200,000 บาทต่อครั้ง"},
        {"id": "CAR-004", "text": "ลูกค้าที่ต่อประกันรถยนต์ชั้น 1 ภายในเดือนมิถุนายน 2026 รับส่วนลดเบี้ยประกัน 15%"},
        {"id": "CAR-003", "text": "ประกันไม่คุ้มครองกรณีผู้ขับขี่เมาแล้วขับ (แอลกอฮอล์เกิน 50 มิลลิกรัมเปอร์เซ็นต์)"},
    ]

    print(f"คำถาม: {question}\n")
    relevant_docs = grade_documents(question, test_docs)

    print(f"\n📊 สรุป: ผ่านการตรวจ {len(relevant_docs)}/{len(test_docs)} เอกสาร")
    for doc in relevant_docs:
        print(f"   - {doc['id']}")
