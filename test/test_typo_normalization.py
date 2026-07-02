import unittest
from text_normalizer import normalize_text
from offline_gate import check_offline_gate
from query_router import route_query


class TypoNormalizationTest(unittest.TestCase):
    def test_misspelled_coverage_word_is_normalized(self):
        self.assertEqual(normalize_text("ค้มคอง"), "คุ้มครอง")
        self.assertIsNone(check_offline_gate("ค้มคอง"))
    def test_misspelled_insurance_word_asks_for_clarification(self):
        self.assertIsNone(check_offline_gate("ปะกัน"))
        self.assertEqual(route_query("ปะกัน"), "general")

    def test_short_misspelled_car_word_asks_for_clarification(self):
        self.assertIsNone(check_offline_gate("รถยน"))
        self.assertEqual(route_query("รถยน"), "general")

    def test_misspelled_car_word_inside_question_routes_to_car(self):
        question = "รถยนคุ้มครองน้ำท่วมไหม"
        self.assertIsNone(check_offline_gate(question))
        self.assertEqual(route_query(question), "car_insurance")


if __name__ == "__main__":
    unittest.main()
