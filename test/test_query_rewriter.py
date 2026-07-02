import unittest
from unittest.mock import patch

from query_rewriter import rewrite_query


class QueryRewriterTest(unittest.TestCase):

    @patch("query_rewriter.client.chat.completions.create")
    def test_short_question_does_not_call_llm(
        self,
        mock_create,
    ):
        result = rewrite_query("มีอะไรบ้าง")

        self.assertEqual(result, "มีอะไรบ้าง")
        mock_create.assert_not_called()

    @patch("query_rewriter.client.chat.completions.create")
    def test_clear_question_can_call_llm(
        self,
        mock_create,
    ):
        mock_create.return_value.choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Message",
                        (),
                        {
                            "content": "ประกันภัยรถยนต์กรณีผู้ขับขี่ขณะมึนเมาสามารถเคลมค่าสินไหมได้หรือไม่"
                        },
                    )()
                },
            )()
        ]

        result = rewrite_query("รถเมาขับชนเคลมได้ป่าวคะ")

        self.assertIn("เคลม", result)
        mock_create.assert_called_once()

    @patch("query_rewriter.client.chat.completions.create")
    def test_none_content_falls_back_to_original_question(
        self,
        mock_create,
    ):
        mock_create.return_value.choices[0].message.content = None

        question = "รถเมาขับชนเคลมประกันได้ไหมคะพี่"
        result = rewrite_query(question)

        self.assertEqual(result, question)

    @patch("query_rewriter.client.chat.completions.create")
    def test_api_error_falls_back_to_original_question(
        self,
        mock_create,
    ):
        mock_create.side_effect = Exception("openrouter down")

        question = "รถเมาขับชนเคลมประกันได้ไหมคะพี่"
        result = rewrite_query(question)

        self.assertEqual(result, question)


if __name__ == "__main__":
    unittest.main()