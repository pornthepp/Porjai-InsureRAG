import unittest

from offline_gate import check_offline_gate


class OfflineGateTest(unittest.TestCase):

    def test_greeting_is_answered_offline(self):
        answer = check_offline_gate("สวัสดีครับ")
        self.assertIsNotNone(answer)

    def test_off_topic_question_is_answered_offline(self):
        answer = check_offline_gate("วันนี้ฝนจะตกไหม")
        self.assertIsNotNone(answer)

    def test_car_insurance_question_goes_to_rag(self):
        answer = check_offline_gate("ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง")
        self.assertIsNone(answer)

    def test_car_accident_question_goes_to_rag(self):
        answer = check_offline_gate("รถชนต้องทำอย่างไร")
        self.assertIsNone(answer)

    def test_life_insurance_question_goes_to_rag(self):
        answer = check_offline_gate("ประกันชีวิตเวนคืนกรมธรรม์ได้ไหม")
        self.assertIsNone(answer)

    def test_promotion_question_goes_to_rag(self):
        answer = check_offline_gate("มีโปรโมชั่นอะไรบ้างช่วงนี้")
        self.assertIsNone(answer)
    def test_repair_shop_question_goes_to_rag(self):
        answer = check_offline_gate("ซ่อมห้างกับซ่อมอู่ต่างกันยังไง")
        self.assertIsNone(answer)

    def test_beneficiary_question_goes_to_rag(self):
        """
        จำลองเคสจริงจากผู้ใช้: กดปุ่ม "ผู้รับประโยชน์" ใน LIFE_CLARIFY_RESPONSE
        ต้องผ่าน Offline Gate เข้า RAG ได้ ไม่ใช่ถูกปัดเป็นคำถามนอกเรื่อง
        (ข้อมูลเรื่องผู้รับประโยชน์มีอยู่จริงใน data/life_insurance.txt)
        """
        answer = check_offline_gate("ผู้รับประโยชน์")
        self.assertIsNone(answer)

if __name__ == "__main__":
    unittest.main()