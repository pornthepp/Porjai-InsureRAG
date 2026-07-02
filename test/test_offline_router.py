import unittest
from unittest.mock import patch

from query_router import route_query


class OfflineRouterTest(unittest.TestCase):

    @patch("query_router.client.chat.completions.create")
    def test_car_question_does_not_call_llm(self, mock_create):
        category = route_query(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง"
        )

        self.assertEqual(category, "car_insurance")
        mock_create.assert_not_called()

    @patch("query_router.client.chat.completions.create")
    def test_life_question_does_not_call_llm(self, mock_create):
        category = route_query(
            "เวนคืนกรมธรรม์ประกันชีวิตได้ไหม"
        )

        self.assertEqual(category, "life_insurance")
        mock_create.assert_not_called()

    @patch("query_router.client.chat.completions.create")
    def test_unclear_insurance_question_is_general(
        self,
        mock_create,
    ):
        category = route_query("มีประกันแบบไหนบ้าง")

        self.assertEqual(category, "general")
        mock_create.assert_not_called()
    @patch("query_router.client.chat.completions.create")
    def test_ambiguous_car_question_uses_llm_router(self, mock_create):
        mock_create.return_value.choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Message",
                        (),
                        {"content": "car_insurance"},
                    )()
                },
            )()
        ]

        category = route_query("ประกัน 2+ กับ 3+ ต่างกันยังไง")

        self.assertEqual(category, "car_insurance")
        mock_create.assert_called_once()


    @patch("query_router.client.chat.completions.create")
    def test_invalid_llm_label_falls_back_to_general(self, mock_create):
        mock_create.return_value.choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Message",
                        (),
                        {"content": "other_category"},
                    )()
                },
            )()
        ]

        category = route_query("ประกัน 2+ กับ 3+ ต่างกันยังไง")

        self.assertEqual(category, "general")


    @patch("query_router.client.chat.completions.create")
    def test_llm_router_error_falls_back_to_general(self, mock_create):
        mock_create.side_effect = Exception("router failed")

        category = route_query("ประกัน 2+ กับ 3+ ต่างกันยังไง")

        self.assertEqual(category, "general")

if __name__ == "__main__":
    unittest.main()