from graph_builder import build_graph

app = build_graph()

initial_state = {
    "question": "ต่อประกันรถได้ส่วนลดกี่เปอร์เซ็นต์",
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