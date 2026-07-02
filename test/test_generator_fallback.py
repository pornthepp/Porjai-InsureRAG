import unittest
from unittest.mock import patch

from generator import FALLBACK_RESPONSE, generate_answer


class GeneratorFallbackTest(unittest.TestCase):

    @patch("generator.client.chat.completions.create")
    def test_empty_documents_do_not_call_llm(self, mock_create):
        answer = generate_answer(
            "มีประกันสำหรับสัตว์เลี้ยงไหม",
            [],
        )

        self.assertEqual(answer, FALLBACK_RESPONSE)
        mock_create.assert_not_called()

    @patch("generator.client.chat.completions.create")
    def test_empty_documents_use_no_data_fallback(self, mock_create):
        answer = generate_answer(
            "ประกันชีวิตเคลมยังไง",
            [],
        )

        self.assertIn("ไม่พบข้อมูล", answer)
        mock_create.assert_not_called()

    @patch("generator.client.chat.completions.create")
    def test_none_content_from_llm_uses_fallback(self, mock_create):
        mock_create.return_value.choices[0].message.content = None

        documents = [
            {"id": "LIFE-001", "text": "วงเงินคุ้มครอง 1,000,000 บาท"},
        ]

        answer = generate_answer("ประกันชีวิตคุ้มครองเท่าไหร่", documents)

        self.assertEqual(answer, FALLBACK_RESPONSE)

    @patch("generator.client.chat.completions.create")
    def test_api_error_uses_fallback(self, mock_create):
        mock_create.side_effect = Exception("openrouter down")

        documents = [
            {"id": "LIFE-001", "text": "วงเงินคุ้มครอง 1,000,000 บาท"},
        ]

        answer = generate_answer("ประกันชีวิตคุ้มครองเท่าไหร่", documents)

        self.assertEqual(answer, FALLBACK_RESPONSE)


if __name__ == "__main__":
    unittest.main()