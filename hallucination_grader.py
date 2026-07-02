import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

HALLUCINATION_GRADER_MODEL = "google/gemma-3-4b-it"

HALLUCINATION_GRADER_SYSTEM_PROMPT = """คุณเป็นกรรมการตรวจสอบความถูกต้องของคำตอบ
หน้าที่ของคุณคือเช็คว่า "คำตอบ" ที่ AI สร้างขึ้น มีหลักฐานรองรับจาก "บริบท" ที่ให้มาจริงหรือไม่

เกณฑ์การตัดสิน:
- ตอบ "grounded" ถ้าทุกข้อเท็จจริงในคำตอบ (ตัวเลข เงื่อนไข ข้อยกเว้น) มีอยู่ในบริบทจริง ไม่ได้แต่งเติมเกินมา
- ตอบ "hallucinated" ถ้าคำตอบมีข้อมูลที่ไม่มีในบริบท ตัวเลขผิดเพี้ยนจากบริบท หรือสรุปเกินกว่าที่บริบทบอกจริง

ตอบกลับมาเป็นคำเดียวเท่านั้น: grounded หรือ hallucinated
ห้ามอธิบายเพิ่ม"""


def check_hallucination(answer: str, context: str) -> bool:
    """ตรวจว่า answer มีหลักฐานรองรับจาก context จริงไหม คืนค่า True = grounded (ปลอดภัย)"""
    user_prompt = f"บริบท:\n{context}\n\nคำตอบที่ต้องตรวจ:\n{answer}"

    try:
        response = client.chat.completions.create(
            model=HALLUCINATION_GRADER_MODEL,
            messages=[
                {"role": "system", "content": HALLUCINATION_GRADER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=10,
        )
        content = response.choices[0].message.content
    except Exception:
        content = None

    # ตรวจไม่ได้ (None หรือ API error) → ถือว่าไม่ grounded ไว้ก่อน ปลอดภัยกว่าปล่อยผ่าน
    verdict = (content or "").strip().lower()
    return verdict.startswith("grounded")


if __name__ == "__main__":
    context = "ผู้เอาประกันสามารถเคลมค่าซ่อมรถได้ในกรณีรถชนทุกประเภท วงเงินคุ้มครองค่าซ่อมตัวรถสูงสุด 200,000 บาทต่อครั้ง"

    # เคสที่ 1: คำตอบ grounded (ตัวเลขตรงกับ context)
    good_answer = "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 200,000 บาทต่อครั้งค่ะ"
    result1 = check_hallucination(good_answer, context)
    print(f"คำตอบ: {good_answer}")
    print(f"   ผล: {'✅ grounded (ปลอดภัย)' if result1 else '❌ hallucinated (มั่ว)'}\n")

    # เคสที่ 2: คำตอบ hallucinated (ตัวเลขผิดจาก context)
    bad_answer = "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 250,000 บาทต่อครั้งค่ะ"
    result2 = check_hallucination(bad_answer, context)
    print(f"คำตอบ: {bad_answer}")
    print(f"   ผล: {'✅ grounded (ปลอดภัย)' if result2 else '❌ hallucinated (มั่ว)'}")