import unittest
from unittest.mock import patch

from chat_service import CAR_CLARIFY_RESPONSE, answer_question
from ui.components import get_pipeline_logs_html


class FailingGraph:
    def invoke(self, state):
        raise AssertionError("offline flow must not invoke graph")


class ProcessLogTest(unittest.TestCase):

    @patch("builtins.print")
    def test_broad_car_question_emits_offline_menu_log(self, mock_print):
        answer = answer_question(
            "ประกันรถยนต์",
            FailingGraph(),
            {},
            {},
        )

        self.assertEqual(answer, CAR_CLARIFY_RESPONSE)
        mock_print.assert_any_call(
            "[offline_menu] category: car_insurance"
        )

    def test_pipeline_parser_renders_offline_context_and_cache(self):
        logs = "\n".join([
            "[offline_menu] category: car_insurance",
            "🧩 [context] ใช้หมวดล่าสุด: car_insurance",
            "⚡ [cache_hit] ใช้คำตอบเดิมจาก cache",
        ])

        html = get_pipeline_logs_html(logs)

        self.assertIn("Offline", html)
        self.assertIn("Context", html)
        self.assertIn("Cache", html)
        self.assertIn("ประกันรถยนต์", html)


if __name__ == "__main__":
    unittest.main()