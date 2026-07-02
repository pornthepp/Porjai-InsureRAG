from typing import TypedDict


class GraphState(TypedDict):
    question: str
    current_question: str
    category: str
    documents: list
    search_attempts: int
    answer: str
    generation_attempts: int
    is_grounded: bool