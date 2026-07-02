import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

REWRITER_MODEL = "google/gemma-3-4b-it"

REWRITER_SYSTEM_PROMPT = """คุณเป็นผู้ช่วยปรับปรุงคำถามให้ค้นหาข้อมูลได้แม่นยำขึ้น
หน้าที่ของคุณคือแปลงคำถามภาษาพูด/ภาษาแชท ให้เป็นคำถามที่ใช้ศัพท์ทางการของธุรกิจประกันภัย
โดยคงความหมายเดิมไว้ทุกประการ ห้ามเปลี่ยนเจตนาของคำถาม

ตอบกลับมาเฉพาะคำถามที่ปรับปรุงแล้วเท่านั้น ห้ามอธิบายเพิ่ม ห้ามมีคำนำหรือคำลงท้าย"""

MIN_REWRITE_LENGTH = 15

def rewrite_query(question: str) -> str:
    """แปลงคำถามภาษาพูดให้เป็นศัพท์ทางการ คืนค่าเป็นคำถามใหม่"""

    question = (question or "").strip()

    if len(question) < MIN_REWRITE_LENGTH:
        return question

    try:
        response = client.chat.completions.create(
            model=REWRITER_MODEL,
            messages=[
                {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.4,
            max_tokens=50,
        )
        content = response.choices[0].message.content
    except Exception:
        content = None

    # ปรับคำถามไม่ได้ (None หรือ API error) → ใช้คำถามเดิมต่อ ไม่ให้ flow สะดุด
    return (content or "").strip() or question


if __name__ == "__main__":
    test_questions = [
        "รถเมาขับชนเคลมได้ป่าวคะ",
        "เครื่องมันร้อนทำไง",
    ]

    for q in test_questions:
        rewritten = rewrite_query(q)
        print(f"คำถามเดิม: {q}")
        print(f"   → ปรับเป็น: {rewritten}\n")