import unittest
from unittest.mock import patch

from hallucination_grader import check_hallucination


class HallucinationGraderTest(unittest.TestCase):

    @patch("hallucination_grader.client.chat.completions.create")
    def test_grounded_verdict_returns_true(self, mock_create):
        mock_create.return_value.choices[0].message.content = "grounded"

        result = check_hallucination(
            "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 200,000 บาทต่อครั้งค่ะ",
            "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 200,000 บาทต่อครั้ง",
        )

        self.assertTrue(result)

    @patch("hallucination_grader.client.chat.completions.create")
    def test_hallucinated_verdict_returns_false(self, mock_create):
        mock_create.return_value.choices[0].message.content = "hallucinated"

        result = check_hallucination(
            "สามารถเปลี่ยนผู้รับประโยชน์ได้ทุกเมื่อค่ะ",
            "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 200,000 บาทต่อครั้ง",
        )

        self.assertFalse(result)

    @patch("hallucination_grader.client.chat.completions.create")
    def test_none_content_is_treated_as_not_grounded(self, mock_create):
        mock_create.return_value.choices[0].message.content = None

        result = check_hallucination(
            "สามารถเปลี่ยนผู้รับประโยชน์ได้ทุกเมื่อค่ะ",
            "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 200,000 บาทต่อครั้ง",
        )

        self.assertFalse(result)

    @patch("hallucination_grader.client.chat.completions.create")
    def test_api_error_is_treated_as_not_grounded(self, mock_create):
        mock_create.side_effect = Exception("openrouter down")

        result = check_hallucination(
            "สามารถเปลี่ยนผู้รับประโยชน์ได้ทุกเมื่อค่ะ",
            "วงเงินคุ้มครองค่าซ่อมรถสูงสุด 200,000 บาทต่อครั้ง",
        )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
