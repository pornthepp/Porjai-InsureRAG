import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

GENERATOR_MODEL = "google/gemma-3-4b-it"

GENERATOR_SYSTEM_PROMPT = """คุณเป็นพนักงานบริการลูกค้าของบริษัทประกันภัย
หน้าที่ของคุณคือตอบคำถามลูกค้าโดยใช้ "บริบท" ที่ให้มาเท่านั้น 

กฎเหล็ก:
- ตอบจากบริบทที่ให้เท่านั้น ห้ามเดาหรือเติมข้อมูลที่ไม่มีในบริบท
- ห้ามพูดทวนคำถามของลูกค้าซ้ำก่อนตอบ (เช่น ถ้าลูกค้าถาม "กินข้าวยัง" ห้ามตอบ "กินข้าวยังคะ?" กลับไปก่อน)
  ให้ตอบเข้าเนื้อหาทันทีโดยไม่ทวนคำถาม
- ถ้าคำถามเป็นการทักทายหรือพูดคุยทั่วไป (เช่น สวัสดี, ทานข้าวยังไหม, สบายดีไหม) ที่ไม่เกี่ยวกับประกันภัยเลย
  ให้ตอบกลับแบบเป็นมิตรสั้นๆ แล้วชวนถามคำถามเกี่ยวกับประกันรถยนต์หรือประกันชีวิต
  ห้ามบอกว่าข้อมูลไม่อยู่ในระบบ และห้ามเสนอต่อสายให้เจ้าหน้าที่กับคำถามประเภทนี้ เพราะไม่ใช่เรื่องเร่งด่วน
- ถ้าเป็นคำถามเกี่ยวกับประกันภัยจริง แต่บริบทไม่มีคำตอบ ให้บอกตามตรงว่าไม่มีข้อมูลส่วนนี้ ห้ามมั่วตอบ
  และแนะนำให้ติดต่อเจ้าหน้าที่เพื่อตรวจสอบเพิ่มเติม
- เรียกลูกค้าหรือผู้ใช้งานว่า คุณลูกค้า
- เรียกตัวเองว่า หนู
- ตอบให้กระชับ สุภาพ เป็นธรรมชาติแบบพนักงานคุยกับลูกค้าลงท้ายด้วย คะ สำหรับประโยคคำถาม ค่ะ สำหรับประโยคบอกเล่า
- จัดรูปแบบคำตอบให้อ่านง่ายเสมอ หากข้อมูลยาวหรือมีหลายหัวข้อ ให้แบ่งเป็นข้อๆ (Bullet points) และใช้ตัวหนา (Bold) เน้นข้อความสำคัญ
- อนุญาตให้ใส่ Emoji เล็กน้อยที่หน้าหัวข้อเพื่อให้อ่านแล้วสบายตาและดูเป็นกันเองมากขึ้น (เช่น 🛡️, 💰, 📸, 🚗, ❤️)"""

FALLBACK_RESPONSE = "ขออภัยค่ะ ไม่พบข้อมูลส่วนนี้ในระบบ มีเรื่องอื่นให้ช่วยไหมคะ"


def generate_answer(question, documents):
    if not documents:
        return FALLBACK_RESPONSE

    context = "\n\n".join(
        f"[{doc['id']}]\n{doc['text']}"
        for doc in documents
    )

    user_prompt = (
        f"บริบท:\n{context}\n\n"
        f"คำถามลูกค้า: {question}"
    )

    try:
        response = client.chat.completions.create(
            model=GENERATOR_MODEL,
            messages=[
                {"role": "system","content": GENERATOR_SYSTEM_PROMPT,},
                {"role": "user","content": user_prompt,},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content
    except Exception:
        content = None

    if not content:
        return FALLBACK_RESPONSE

    return content.strip()


if __name__ == "__main__":
    # ทดสอบกรณีมี context (CAR-003)
    test_docs = [
        {"id": "CAR-003", "text": "ประกันไม่คุ้มครองกรณีผู้ขับขี่เมาแล้วขับ (แอลกอฮอล์เกิน 50 มิลลิกรัมเปอร์เซ็นต์) ไม่คุ้มครองการใช้รถผิดประเภท เช่น นำรถยนต์ส่วนบุคคลไปขับขี่รับส่งผู้โดยสารแบบ ride-hailing โดยไม่แจ้งบริษัทล่วงหน้า ไม่คุ้มครองความเสียหายจากสนามแข่งหรือการแข่งรถทุกชนิด"}
    ]
    answer = generate_answer("เมาแล้วขับเคลมประกันได้ไหม", test_docs)
    print("กรณีมี context:")
    print(f"   {answer}\n")

    # ทดสอบกรณีไม่มี context เลย (Grader กรองหมด)
    answer_empty = generate_answer("ประกันรถคุ้มครองน้ำท่วมไหม", [])
    print("กรณีไม่มี context:")
    print(f" {answer_empty}")