import unittest
from unittest.mock import patch

from generator import FALLBACK_RESPONSE
from graph_builder import MAX_GENERATION_RETRY, build_graph


class GraphHallucinationFallbackTest(unittest.TestCase):
    """
    จำลองเคส UAT: "ประกันชีวิตเปลี่ยนผู้รับประโยชน์ได้ไหม"
    ไฟล์ไม่มีข้อมูลเรื่องนี้ hallucination grader ตัดสินไม่ grounded ทุกรอบ
    ระบบต้องคืน fallback response แทนคำตอบล่าสุดที่ไม่ grounded
    """

    @patch("graph_nodes.check_hallucination")
    @patch("graph_nodes.generate_answer")
    @patch("graph_nodes._search_and_grade")
    @patch("graph_nodes.route_query")
    def test_exhausted_retries_return_fallback_not_last_answer(
        self,
        mock_route_query,
        mock_search_and_grade,
        mock_generate_answer,
        mock_check_hallucination,
    ):
        mock_route_query.return_value = "life_insurance"
        mock_search_and_grade.return_value = [
            {"id": "LIFE-001", "text": "วงเงินคุ้มครองเสียชีวิต 1,000,000 บาท"},
        ]
        mock_generate_answer.return_value = "สามารถเปลี่ยนผู้รับประโยชน์ได้ทุกเมื่อค่ะ"
        mock_check_hallucination.return_value = False  # ไม่ grounded ทุกรอบ

        graph = build_graph()

        initial_state = {
            "question": "ประกันชีวิตเปลี่ยนผู้รับประโยชน์ได้ไหม",
            "current_question": "",
            "category": "life_insurance",
            "documents": [],
            "search_attempts": 0,
            "answer": "",
            "generation_attempts": 0,
            "is_grounded": False,
        }

        final_state = graph.invoke(initial_state)

        self.assertEqual(final_state["answer"], FALLBACK_RESPONSE)
        self.assertNotEqual(
            final_state["answer"],
            "สามารถเปลี่ยนผู้รับประโยชน์ได้ทุกเมื่อค่ะ",
        )
        self.assertEqual(
            final_state["generation_attempts"],
            MAX_GENERATION_RETRY,
        )
        self.assertFalse(final_state["is_grounded"])

    @patch("graph_nodes.check_hallucination")
    @patch("graph_nodes.generate_answer")
    @patch("graph_nodes._search_and_grade")
    @patch("graph_nodes.route_query")
    def test_grounded_on_first_try_skips_fallback(
        self,
        mock_route_query,
        mock_search_and_grade,
        mock_generate_answer,
        mock_check_hallucination,
    ):
        mock_route_query.return_value = "car_insurance"
        mock_search_and_grade.return_value = [
            {"id": "CAR-001", "text": "วงเงินคุ้มครองค่าซ่อม 200,000 บาท"},
        ]
        mock_generate_answer.return_value = "วงเงินคุ้มครองค่าซ่อม 200,000 บาทค่ะ"
        mock_check_hallucination.return_value = True

        graph = build_graph()

        initial_state = {
            "question": "ประกันรถยนต์คุ้มครองค่าซ่อมเท่าไหร่",
            "current_question": "",
            "category": "car_insurance",
            "documents": [],
            "search_attempts": 0,
            "answer": "",
            "generation_attempts": 0,
            "is_grounded": False,
        }

        final_state = graph.invoke(initial_state)

        self.assertEqual(
            final_state["answer"],
            "วงเงินคุ้มครองค่าซ่อม 200,000 บาทค่ะ",
        )
        self.assertTrue(final_state["is_grounded"])
        self.assertEqual(final_state["generation_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
