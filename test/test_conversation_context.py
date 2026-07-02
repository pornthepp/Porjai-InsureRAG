import unittest
from unittest.mock import patch

from chat_service import answer_question


class FakeGraph:
    def __init__(self):
        self.invoke_count = 0
        self.last_state = None

    def invoke(self, state):
        self.invoke_count += 1
        self.last_state = state
        return {"answer": "คำตอบจาก RAG"}


class ConversationContextTest(unittest.TestCase):

    @patch("chat_service.route_query")
    def test_followup_uses_previous_car_category_without_router(
        self,
        mock_route_query,
    ):
        graph = FakeGraph()
        cache = {}
        conversation = {}

        answer_question(
            "ประกันรถยนต์",
            graph,
            cache,
            conversation,
        )

        answer_question(
            "คุ้มครอง",
            graph,
            cache,
            conversation,
        )

        self.assertEqual(
            conversation["category"],
            "car_insurance",
        )
        mock_route_query.assert_not_called()
        self.assertEqual(graph.invoke_count, 1)
        self.assertEqual(
            graph.last_state["category"],
            "car_insurance",
        )
        self.assertEqual(graph.last_state["question"],"ประกันรถยนต์ คุ้มครอง",)




    @patch("chat_service.route_query")
    def test_explicit_life_question_overrides_car_context(
        self,
        mock_route_query,
    ):
        graph = FakeGraph()
        cache = {}
        conversation = {"category": "car_insurance"}

        answer_question(
            "ประกันชีวิตคุ้มครองอะไร",
            graph,
            cache,
            conversation,
        )

        self.assertEqual(
            conversation["category"],
            "life_insurance",
        )
        self.assertEqual(
            graph.last_state["category"],
            "life_insurance",
        )
        self.assertEqual(
            graph.last_state["question"],
            "ประกันชีวิตคุ้มครองอะไร",
        )
        mock_route_query.assert_not_called()

    @patch("chat_service.route_query")
    def test_document_followup_after_life_context_skips_offline_gate(
        self,
        mock_route_query,
    ):
        """
        จำลองเคส UAT: บริบทประกันชีวิต → "ต้องใช้เอกสารอะไรบ้าง"
        เดิม Offline Gate ตอบนอกเรื่องก่อนเช็ค context ทั้งที่ไฟล์มีรายการเอกสารเคลม
        """
        graph = FakeGraph()
        cache = {}
        conversation = {"category": "life_insurance"}

        answer = answer_question(
            "ต้องใช้เอกสารอะไรบ้าง",
            graph,
            cache,
            conversation,
        )

        self.assertNotIn("เฉพาะเรื่องประกัน", answer)
        self.assertEqual(graph.invoke_count, 1)
        self.assertEqual(
            graph.last_state["category"],
            "life_insurance",
        )
        self.assertEqual(
            graph.last_state["question"],
            "ประกันชีวิต ต้องใช้เอกสารอะไรบ้าง",
        )
        mock_route_query.assert_not_called()

    def test_document_followup_without_prior_context_stays_offline(self):
        """ไม่มีบริบทก่อนหน้า คำถามลอยๆ ควรยังถูก Offline Gate ปัดตามปกติ"""
        graph = FakeGraph()
        cache = {}
        conversation = {}

        answer = answer_question(
            "ต้องใช้เอกสารอะไรบ้าง",
            graph,
            cache,
            conversation,
        )

        self.assertIn("เฉพาะเรื่องประกัน", answer)
        self.assertEqual(graph.invoke_count, 0)


if __name__ == "__main__":
    unittest.main()
