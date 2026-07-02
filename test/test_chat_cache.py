import unittest
from unittest.mock import patch
from chat_service import answer_question


class FakeGraph:
    def __init__(self):
        self.invoke_count = 0

    def invoke(self, state):
        self.invoke_count += 1
        return {"answer": "คุ้มครองตามเงื่อนไขกรมธรรม์ค่ะ"}


class ChatCacheTest(unittest.TestCase):

    def test_same_question_invokes_graph_once(self):
        graph = FakeGraph()
        cache = {}

        first_answer = answer_question(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            graph,
            cache,
        )

        second_answer = answer_question(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            graph,
            cache,
        )

        self.assertEqual(first_answer, second_answer)
        self.assertEqual(graph.invoke_count, 1)
        
    @patch("chat_service.route_query", return_value="car_insurance")
    def test_same_question_routes_only_once(self, mock_route_query):
        graph = FakeGraph()
        cache = {}
        question = "ซ่อมห้างกับซ่อมอู่ต่างกันยังไง"

        answer_question(question, graph, cache)
        answer_question(question, graph, cache)

        mock_route_query.assert_called_once_with(question)
        self.assertEqual(graph.invoke_count, 1)

if __name__ == "__main__":
    unittest.main()