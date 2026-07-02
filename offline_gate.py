from typing import Optional

from text_normalizer import normalize_text

GREETING_RESPONSE = (
    "สวัสดีค่ะ ยินดีให้บริการเรื่องประกันรถยนต์และประกันชีวิตค่ะ "
    "ต้องการสอบถามเรื่องใดคะ"
)

OUT_OF_SCOPE_RESPONSE = (
    "ขออภัยค่ะ ระบบให้ข้อมูลเฉพาะเรื่องประกันรถยนต์และ"
    "ประกันชีวิตเท่านั้น กรุณาสอบถามเกี่ยวกับประกันภัยนะคะ"
)

INSURANCE_KEYWORDS = [
    "ประกัน",
    "ประกันภัย",
    "ประกันรถ",
    "ประกันรถยนต์",
    "ประกันชีวิต",
    "กรมธรรม์",
    "เบี้ย",
    "เคลม",
    "คุ้มครอง",
    "อุบัติเหตุ",
    "รถชน",
    "น้ำท่วม",
    "ไฟไหม้",
    "โปรโมชั่น",
    "ส่วนลด",
    "ซ่อมห้าง",
    "ซ่อมอู่",
]

CAR_INCIDENT_KEYWORDS = (
    "ชน",
    "อุบัติเหตุ",
    "น้ำท่วม",
    "ไฟไหม้",
    "รถหาย",
    "ซ่อม",
)

GREETING_KEYWORDS = (
    "สวัสดี",
    "หวัดดี",
    "hello",
    "hi",
)


def _normalize(message: str) -> str:
    """ปรับข้อความให้อยู่ในรูปที่ตรวจสอบง่ายขึ้น"""
    return normalize_text(message)


def _is_insurance_question(message: str) -> bool:
    """ตรวจว่าข้อความเกี่ยวข้องกับงานประกันหรือไม่"""

    if message == "รถยนต์":
        return True

    if any(keyword in message for keyword in INSURANCE_KEYWORDS):
        return True

    # รองรับคำถาม เช่น “รถชนต้องทำอย่างไร”
    has_car = "รถ" in message
    has_incident = any(
        keyword in message for keyword in CAR_INCIDENT_KEYWORDS
    )

    return has_car and has_incident


def check_offline_gate(message: str) -> Optional[str]:
    """
    คืนข้อความเมื่อ Offline Gate ตอบเองได้

    คืน None เมื่อควรส่งคำถามต่อเข้า RAG และ LLM
    """
    normalized_message = _normalize(message)

    if not normalized_message:
        return "กรุณาพิมพ์คำถามที่ต้องการสอบถามค่ะ"

    if _is_insurance_question(normalized_message):
        return None

    if any(
        greeting in normalized_message
        for greeting in GREETING_KEYWORDS
    ):
        return GREETING_RESPONSE

    return OUT_OF_SCOPE_RESPONSE