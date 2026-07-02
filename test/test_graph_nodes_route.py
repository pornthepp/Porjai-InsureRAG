import unittest
from unittest.mock import patch

from graph_nodes import route_node


class RouteNodeTest(unittest.TestCase):

    @patch("graph_nodes.route_query")
    def test_route_node_uses_existing_category_without_rerouting(
        self,
        mock_route_query,
    ):
        state = {
            "question": "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            "current_question": "",
            "category": "car_insurance",
            "documents": [],
            "search_attempts": 99,
            "answer": "",
            "generation_attempts": 99,
            "is_grounded": False,
        }

        result = route_node(state)

        self.assertEqual(result["category"], "car_insurance")
        self.assertEqual(
            result["current_question"],
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
        )
        self.assertEqual(result["search_attempts"], 0)
        self.assertEqual(result["generation_attempts"], 0)
        mock_route_query.assert_not_called()

    @patch("graph_nodes.route_query")
    def test_route_node_routes_when_category_is_missing(
        self,
        mock_route_query,
    ):
        mock_route_query.return_value = "life_insurance"

        state = {
            "question": "เวนคืนกรมธรรม์ประกันชีวิตได้ไหม",
            "current_question": "",
            "category": "",
            "documents": [],
            "search_attempts": 0,
            "answer": "",
            "generation_attempts": 0,
            "is_grounded": False,
        }

        result = route_node(state)

        self.assertEqual(result["category"], "life_insurance")
        mock_route_query.assert_called_once_with(
            "เวนคืนกรมธรรม์ประกันชีวิตได้ไหม"
        )


if __name__ == "__main__":
    unittest.main()