import os

from dotenv import load_dotenv
from openai import OpenAI

from text_normalizer import normalize_text

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

ROUTER_MODEL = "google/gemma-3-4b-it"

VALID_CATEGORIES = {
    "car_insurance",
    "life_insurance",
    "general",
}

VAGUE_CATEGORY_TERMS = {
    "ประกัน",
    "รถยนต์",
    "ประกันชีวิต",
    "มีประกันแบบไหนบ้าง",
}

CAR_KEYWORDS = (
    "ประกันรถ",
    "ประกันรถยนต์",
    "รถยนต์",
    "เคลมรถ",
    "รถชน",
    "อุบัติเหตุรถ",
    "พ.ร.บ.",
    "พรบ",
    "ชั้น 1",
    "ชั้น1",
    "ชั้นหนึ่ง",
    "อู่",
    "ซ่อมรถ",
)

LIFE_KEYWORDS = (
    "ประกันชีวิต",
    "ชีวิต",
    "เวนคืน",
    "ผู้รับประโยชน์",
    "กรมธรรม์ชีวิต",
    "ทุนประกัน",
    "เสียชีวิต",
)

ROUTER_SYSTEM_PROMPT = """คุณเป็นระบบจำแนกหมวดหมู่คำถามลูกค้าประกันภัย

เลือกเพียงหนึ่งหมวด:
car_insurance = ประกันรถยนต์ การเคลมรถ อุบัติเหตุรถ หรือการซ่อมรถ
life_insurance = ประกันชีวิต กรมธรรม์ชีวิต หรือผู้รับประโยชน์
general = คำถามทั่วไปหรือไม่สามารถระบุหมวดได้

ตอบเพียงชื่อหมวดเท่านั้น:
car_insurance, life_insurance หรือ general
"""


def _normalize(text: str) -> str:
    return normalize_text(text or "")


def _route_offline(normalized_question: str) -> str:
    for keyword in CAR_KEYWORDS:
        if keyword in normalized_question:
            return "car_insurance"

    for keyword in LIFE_KEYWORDS:
        if keyword in normalized_question:
            return "life_insurance"

    return "general"


def _route_with_llm(question: str) -> str:
    try:
        response = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=10,
        )

        content = response.choices[0].message.content
        category = (content or "").strip().lower()

        if category in VALID_CATEGORIES:
            return category

    except Exception:
        pass

    return "general"


def route_query(question: str) -> str:
    """ใช้กฎ offline ก่อน และเรียก LLM เฉพาะคำถามที่กำกวม"""
    normalized_question = _normalize(question)

    if not normalized_question:
        return "general"

    if normalized_question in VAGUE_CATEGORY_TERMS:
        return "general"

    offline_category = _route_offline(normalized_question)

    if offline_category != "general":
        return offline_category

    return _route_with_llm(question)