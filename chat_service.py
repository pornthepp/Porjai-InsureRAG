from offline_gate import check_offline_gate
from query_router import route_query
from text_normalizer import normalize_text

GENERAL_CLARIFY_RESPONSE = (
    "หนูขอสอบถามเพิ่มเติมได้ไหมคะ "
    "คุณลูกค้าสนใจประกันรถยนต์หรือประกันชีวิตคะ "
    "เลือกจากปุ่มด้านล่างได้เลยค่ะ"
    "[OPTIONS:ประกันรถยนต์:🚗 ประกันรถยนต์|ประกันชีวิต:❤️ ประกันชีวิต]"
)

LIFE_CLARIFY_RESPONSE = (
    "หนูขอสอบถามเพิ่มเติมเกี่ยวกับประกันชีวิตได้ไหมคะ "
    "คุณลูกค้าต้องการทราบเรื่องความคุ้มครอง เบี้ยประกัน การเคลม "
    "ผู้รับประโยชน์ หรือการกู้เงินกรมธรรม์คะ"
    "[OPTIONS:ความคุ้มครอง|เบี้ยประกัน|การเคลม|ผู้รับประโยชน์|กู้เงินกรมธรรม์]"
)

CAR_CLARIFY_RESPONSE = (
    "หนูขอสอบถามเพิ่มเติมเกี่ยวกับประกันรถยนต์ได้ไหมคะ "
    "คุณลูกค้าต้องการทราบเรื่องความคุ้มครอง เบี้ยประกัน การเคลม "
    "หรือโปรโมชั่นคะ"
    "[OPTIONS:ความคุ้มครอง|เบี้ยประกัน|การเคลม|โปรโมชั่น]"
)

LIFE_BROAD_TERMS = {"ประกันชีวิต"}
CAR_BROAD_TERMS = {"ประกันรถ", "ประกันรถยนต์", "รถยนต์", "รถ"}

FOLLOW_UP_TERMS = (
    "คุ้มครอง",
    "เบี้ย",
    "ราคา",
    "เคลม",
    "โปรโมชั่น",
    "ส่วนลด",
    "เงื่อนไข",
    "ข้อยกเว้น",
    "เอกสาร",
    "กรมธรรม์",
)

CONTEXT_CATEGORIES = {
    "car_insurance",
    "life_insurance",
}

CATEGORY_QUERY_PREFIX = {
    "car_insurance": "ประกันรถยนต์",
    "life_insurance": "ประกันชีวิต",
}

EXPLICIT_CAR_TERMS = (
    "ประกันรถ",
    "ประกันรถยนต์",
    "รถยนต์",
)

EXPLICIT_LIFE_TERMS = (
    "ประกันชีวิต",
    "กรมธรรม์ชีวิต",
    "ผู้รับประโยชน์",
    "เวนคืน",
)

def _make_cache_key(question: str, category=None) -> str:
    key = " ".join((question or "").strip().lower().split())

    if category:
        return f"{category}:{key}"

    return key


def answer_question(
    question: str,
    graph,
    cache=None,
    conversation=None,
) -> str:
    if conversation is None:
        conversation = {}

    normalized_question = normalize_text(question)

    if normalized_question in LIFE_BROAD_TERMS:
        conversation["category"] = "life_insurance"
        print("[offline_menu] category: life_insurance")
        return LIFE_CLARIFY_RESPONSE

    if normalized_question in CAR_BROAD_TERMS:
        conversation["category"] = "car_insurance"
        print("[offline_menu] category: car_insurance")
        return CAR_CLARIFY_RESPONSE

    previous_category = conversation.get("category")

    is_followup = any(
        term in normalized_question
        for term in FOLLOW_UP_TERMS
    )

    is_context_followup = (
        is_followup
        and previous_category in CONTEXT_CATEGORIES
    )

    # follow-up ที่ต่อเนื่องจากบทสนทนาเดิม (เช่น "ต้องใช้เอกสารอะไรบ้าง" หลังคุยเรื่องประกันชีวิต)
    # ให้ผ่านเข้า RAG โดยตรง ไม่ต้องเช็ค Offline Gate เพราะ gate ไม่รู้จัก context ของบทสนทนา
    if not is_context_followup:
        offline_answer = check_offline_gate(question)

        if offline_answer is not None:
            print("[offline_gate] offline response")
            return offline_answer

    category = None

    has_explicit_car = any(
        term in normalized_question
        for term in EXPLICIT_CAR_TERMS
    )
    has_explicit_life = any(
        term in normalized_question
        for term in EXPLICIT_LIFE_TERMS
    )

    rag_question = question

    if has_explicit_car and not has_explicit_life:
        category = "car_insurance"
        prefix = CATEGORY_QUERY_PREFIX[category]
        if prefix not in normalized_question:
            rag_question = f"{prefix} {normalized_question}"
    elif has_explicit_life and not has_explicit_car:
        category = "life_insurance"
        prefix = CATEGORY_QUERY_PREFIX[category]
        if prefix not in normalized_question:
            rag_question = f"{prefix} {normalized_question}"
    elif is_context_followup:
        category = previous_category
        prefix = CATEGORY_QUERY_PREFIX[category]
        rag_question = f"{prefix} {normalized_question}"
        print(f"[context] category: {category}")

    cache_key = _make_cache_key(question, category)

    if cache is not None and cache_key in cache:
        print("[cache_hit] cached answer")
        return cache[cache_key]

    if category is None:
        category = route_query(question)

    if category == "general":
        answer = GENERAL_CLARIFY_RESPONSE

        if cache is not None:
            cache[cache_key] = answer

        return answer

    conversation["category"] = category

    initial_state = {
        "question": rag_question,
        "current_question": "",
        "category": category,
        "documents": [],
        "search_attempts": 0,
        "answer": "",
        "generation_attempts": 0,
        "is_grounded": False,
    }

    final_state = graph.invoke(initial_state)
    answer = final_state["answer"]

    if cache is not None:
        cache[cache_key] = answer

    return answer