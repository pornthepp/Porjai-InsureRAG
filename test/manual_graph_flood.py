from graph_builder import build_graph

app = build_graph()

initial_state = {
    "question": "ประกันรถคุ้มครองน้ำท่วมไหม",
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