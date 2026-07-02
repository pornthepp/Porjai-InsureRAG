from langgraph.graph import StateGraph, END
from graph_state import GraphState
from graph_nodes import (
    route_node,
    search_node,
    rewrite_node,
    generate_node,
    hallucination_check_node,
    fallback_node,
)

MAX_SEARCH_RETRY = 2
MAX_GENERATION_RETRY = 2


def decide_after_search(state: GraphState) -> str:
    """หลัง search_node: ถ้ามี documents ไปต่อที่ generate_node, ถ้าไม่มีและยังไม่ครบ retry ไป rewrite_node"""
    if state["documents"]:
        return "generate"
    if state["search_attempts"] < MAX_SEARCH_RETRY:
        return "rewrite"
    return "generate"  # ครบ retry แล้ว ไป generate_node เพื่อตอบ fallback


def decide_after_hallucination_check(state: GraphState) -> str:
    """หลังตรวจ hallucination: ถ้า grounded จบเลย, ถ้าไม่และยังไม่ครบ retry กลับไป generate ใหม่"""
    if state["is_grounded"]:
        return "end"
    if state["generation_attempts"] < MAX_GENERATION_RETRY:
        return "regenerate"
    return "fallback"  # ครบ retry แล้วแต่ยังไม่ grounded → ตอบ fallback แทนคำตอบล่าสุด


def build_graph():
    graph = StateGraph(GraphState)

    # เพิ่ม Node ทั้งหมดเข้ากราฟ
    graph.add_node("route", route_node)
    graph.add_node("search", search_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)
    graph.add_node("hallucination_check", hallucination_check_node)
    graph.add_node("fallback", fallback_node)

    # กำหนดจุดเริ่มต้น
    graph.set_entry_point("route")

    # เส้นทางตรงไปตรงมา (ไม่มีเงื่อนไข)
    graph.add_edge("route", "search")
    graph.add_edge("rewrite", "search")          # rewrite แล้ววนกลับไป search ใหม่
    graph.add_edge("generate", "hallucination_check")

    # เส้นทางมีเงื่อนไข (conditional edge)
    graph.add_conditional_edges(
        "search",
        decide_after_search,
        {
            "generate": "generate",
            "rewrite": "rewrite",
        },
    )

    graph.add_conditional_edges(
        "hallucination_check",
        decide_after_hallucination_check,
        {
            "end": END,
            "regenerate": "generate",            # ไม่ grounded → กลับไป generate ใหม่
            "fallback": "fallback",              # ครบ retry แล้วยังไม่ grounded → ตอบ fallback
        },
    )

    graph.add_edge("fallback", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    initial_state = {
        "question": "เมาแล้วขับเคลมประกันได้ไหม",
        "current_question": "",
        "category": "",
        "documents": [],
        "search_attempts": 0,
        "answer": "",
        "generation_attempts": 0,
        "is_grounded": False,
    }

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 50)
    print(f"คำตอบสุดท้าย: {final_state['answer']}")
    print(f"ใช้รอบค้นหา: {final_state['search_attempts']}, รอบสร้างคำตอบ: {final_state['generation_attempts']}")