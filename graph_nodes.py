from graph_state import GraphState
from query_router import route_query


def route_node(state: GraphState) -> dict:
    """Node แรก: ใช้ category ที่มีอยู่ก่อน ถ้าไม่มีค่อยจำแนกใหม่"""
    question = state["question"]
    category = state.get("category") or route_query(question)

    print(f"🧭 [route_node] หมวดที่จำแนกได้: {category}")

    return {
        "category": category,
        "current_question": question,
        "search_attempts": 0,
        "generation_attempts": 0,
    }

from retrieval_pipeline import _search_and_grade


def search_node(state: GraphState) -> dict:
    """Node ที่ 2: ค้นหาใน ChromaDB ตามหมวด แล้วส่งให้ Retrieval Grader กรอง"""
    current_question = state["current_question"]
    category = state["category"]
    attempts = state["search_attempts"] + 1

    print(f"🔎 [search_node] รอบที่ {attempts}: ค้นหาด้วย \"{current_question}\"")

    graded_docs = _search_and_grade(current_question, category)

    print(f"   ผ่านการตรวจ {len(graded_docs)} chunk")

    return {
        "documents": graded_docs,
        "search_attempts": attempts,
    }

from query_rewriter import rewrite_query


def rewrite_node(state: GraphState) -> dict:
    """Node ที่ 3: ปรับคำถามให้เป็นศัพท์ทางการ เพื่อค้นหาใหม่อีกรอบ"""
    current_question = state["current_question"]
    new_question = rewrite_query(current_question)

    print(f"✏️ [rewrite_node] ปรับคำถาม: \"{current_question}\" → \"{new_question}\"")

    return {
        "current_question": new_question,
    }

from generator import generate_answer, FALLBACK_RESPONSE


def generate_node(state):
    question = state["question"]
    documents = state["documents"]
    attempts = state["generation_attempts"] + 1

    print(f"💬 [generate_node] รอบที่ {attempts}: กำลังสร้างคำตอบ...")

    answer = generate_answer(question, documents)   
    print(f"   คำตอบ: {answer}")

    return {
        "answer": answer,
        "generation_attempts": attempts,
    }


from hallucination_grader import check_hallucination


def hallucination_check_node(state: GraphState) -> dict:
    """Node ที่ 5: ตรวจว่าคำตอบมีหลักฐานรองรับจาก context จริงไหม"""
    answer = state["answer"]
    documents = state["documents"]

    # ถ้าไม่มี context เลย (เป็น fallback ตั้งแต่ generate_node) ไม่ต้องตรวจซ้ำ ถือว่า grounded ไปเลย
    if not documents:
        print("🛡️ [hallucination_check_node] เป็น fallback response อยู่แล้ว → ข้ามการตรวจ")
        return {"is_grounded": True}

    context = "\n\n".join(f"[{doc['id']}]\n{doc['text']}" for doc in documents)
    is_grounded = check_hallucination(answer, context)

    print(f"🛡️ [hallucination_check_node] ผลตรวจ: {'✅ grounded' if is_grounded else '❌ hallucinated'}")

    return {"is_grounded": is_grounded}


def fallback_node(state: GraphState) -> dict:
    """Node สุดท้ายเมื่อ hallucination check ไม่ผ่านครบจำนวน retry: แทนคำตอบล่าสุดด้วย fallback"""
    print("⚠️ [fallback_node] hallucination ไม่ผ่านครบ retry → ใช้ fallback response แทนคำตอบล่าสุด")

    return {"answer": FALLBACK_RESPONSE}