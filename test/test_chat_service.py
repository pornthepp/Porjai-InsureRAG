import unittest

from chat_service import (
    CAR_CLARIFY_RESPONSE,
    LIFE_CLARIFY_RESPONSE,
    answer_question,
)


class FakeGraph:
    def __init__(self):
        self.invoke_count = 0

    def invoke(self, state):
        self.invoke_count += 1
        return {"answer": "คำตอบจาก RAG"}


class ChatServiceTest(unittest.TestCase):

    def test_off_topic_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("วันนี้ฝนตกไหม", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertIn("เฉพาะเรื่องประกัน", answer)

    def test_insurance_question_invokes_graph_once(self):
        graph = FakeGraph()

        answer = answer_question(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            graph,
        )

        self.assertEqual(graph.invoke_count, 1)
        self.assertEqual(answer, "คำตอบจาก RAG")

    def test_general_insurance_question_does_not_invoke_graph(self):
        """
        เดิม GENERAL_CLARIFY_RESPONSE ถามกลับเฉยๆ ("สนใจรถยนต์หรือชีวิตคะ") ทั้งที่
        ลูกค้าถามตรงๆ ว่ามีแบบไหนบ้าง — เปลี่ยนให้บอกตรงก่อนว่ามีอะไรบ้าง แล้วค่อยชวนเลือก
        """
        graph = FakeGraph()

        answer = answer_question("มีประกันแบบไหนบ้าง", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertIn("ประกันรถยนต์", answer)
        self.assertIn("ประกันชีวิต", answer)

    def test_broad_life_question_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("ประกันชีวิต", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertEqual(answer, LIFE_CLARIFY_RESPONSE)

    def test_broad_car_question_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("ประกันรถยนต์", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertEqual(answer, CAR_CLARIFY_RESPONSE)

    def test_misspelled_broad_life_question_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("ปะกันชีวิต", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertEqual(answer, LIFE_CLARIFY_RESPONSE)

    def test_broad_car_alias_question_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("ประกันรถ", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertEqual(answer, CAR_CLARIFY_RESPONSE)

    def test_short_misspelled_car_word_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("รถยน", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertEqual(answer, CAR_CLARIFY_RESPONSE)        
        
    def test_broad_life_question_does_not_use_no_data_fallback(self):
        graph = FakeGraph()

        answer = answer_question("ประกันชีวิต", graph)

        self.assertNotIn("ไม่พบข้อมูล", answer)
        self.assertEqual(answer, LIFE_CLARIFY_RESPONSE)

    def test_short_car_word_does_not_invoke_graph(self):
        graph = FakeGraph()

        answer = answer_question("รถ", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertEqual(answer, CAR_CLARIFY_RESPONSE)
    def test_general_insurance_shows_only_category_options(self):
        graph = FakeGraph()

        answer = answer_question("ประกัน", graph)

        self.assertEqual(graph.invoke_count, 0)
        self.assertIn(
            "[OPTIONS:ประกันรถยนต์:🚗 ประกันรถยนต์|ประกันชีวิต:❤️ ประกันชีวิต]",
            answer,
        )
        self.assertNotIn("ความคุ้มครอง", answer)
        self.assertNotIn("ราคา", answer)
        self.assertNotIn("การเคลม", answer)
if __name__ == "__main__":
    unittest.main()