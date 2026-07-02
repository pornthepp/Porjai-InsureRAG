import unittest
from unittest.mock import patch

from retrieval_grader import grade_documents


class RetrievalGraderBatchTest(unittest.TestCase):

    @patch("retrieval_grader.client.chat.completions.create")
    def test_multiple_documents_use_one_llm_call(self, mock_create):
        mock_create.return_value.choices[0].message.content = "0,2"

        documents = [
            {"id": "CAR-001", "text": "เอกสารหนึ่ง", "metadata": {}},
            {"id": "CAR-002", "text": "เอกสารสอง", "metadata": {}},
            {"id": "CAR-003", "text": "เอกสารสาม", "metadata": {}},
        ]

        result = grade_documents(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            documents,
        )

        self.assertEqual(
            [doc["id"] for doc in result],
            ["CAR-001", "CAR-003"],
        )
        mock_create.assert_called_once()

    @patch("retrieval_grader.client.chat.completions.create")
    def test_none_content_does_not_crash_and_returns_no_documents(
        self,
        mock_create,
    ):
        # จำลองเคส UAT: Gemma คืน content=None แล้วเดิมโค้ดเรียก .strip() จน AttributeError
        mock_create.return_value.choices[0].message.content = None

        documents = [
            {"id": "CAR-001", "text": "เอกสารหนึ่ง", "metadata": {}},
        ]

        result = grade_documents(
            "ประกันรถยนต์ 2+ กับ 3+ ต่างกันอย่างไร",
            documents,
        )

        self.assertEqual(result, [])

    @patch("retrieval_grader.client.chat.completions.create")
    def test_api_error_does_not_crash_and_returns_no_documents(
        self,
        mock_create,
    ):
        mock_create.side_effect = Exception("openrouter down")

        documents = [
            {"id": "CAR-001", "text": "เอกสารหนึ่ง", "metadata": {}},
        ]

        result = grade_documents(
            "ประกันรถยนต์ 2+ กับ 3+ ต่างกันอย่างไร",
            documents,
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()