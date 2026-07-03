import unittest
from unittest.mock import MagicMock, patch

import retrieval_pipeline
from retrieval_pipeline import _search_and_grade


class RetrievalPipelineTest(unittest.TestCase):

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_empty_search_results_do_not_call_grader(
        self,
        mock_model,
        mock_collection,
        mock_grade_documents,
    ):
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        result = _search_and_grade(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            "car_insurance",
        )

        self.assertEqual(result, [])
        mock_grade_documents.assert_not_called()

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_far_results_do_not_call_grader(
        self,
        mock_model,
        mock_collection,
        mock_grade_documents,
    ):
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection.query.return_value = {
            "ids": [["CAR-001", "CAR-002"]],
            "documents": [["doc 1", "doc 2"]],
            "metadatas": [[
                {"category": "car_insurance"},
                {"category": "car_insurance"},
            ]],
            "distances": [[1.8, 1.9]],
        }

        result = _search_and_grade(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            "car_insurance",
        )

        self.assertEqual(result, [])
        mock_grade_documents.assert_not_called()

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_near_results_are_sent_to_grader(
        self,
        mock_model,
        mock_collection,
        mock_grade_documents,
    ):
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection.query.return_value = {
            "ids": [["CAR-001", "CAR-002"]],
            "documents": [["doc 1", "doc 2"]],
            "metadatas": [[
                {"category": "car_insurance"},
                {"category": "car_insurance"},
            ]],
            "distances": [[0.2, 0.4]],
        }

        mock_grade_documents.return_value = [
            {
                "id": "CAR-001",
                "text": "doc 1",
                "metadata": {"category": "car_insurance"},
            }
        ]

        result = _search_and_grade(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            "car_insurance",
        )

        self.assertEqual(len(result), 1)
        mock_grade_documents.assert_called_once()

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_only_near_documents_are_sent_to_grader(
        self,
        mock_model,
        mock_collection,
        mock_grade_documents,
    ):
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection.query.return_value = {
            "ids": [["CAR-001", "CAR-002", "CAR-003"]],
            "documents": [["doc 1", "doc 2", "doc 3"]],
            "metadatas": [[
                {"category": "car_insurance"},
                {"category": "car_insurance"},
                {"category": "car_insurance"},
            ]],
            "distances": [[0.2, 0.7, 1.3]],
        }

        mock_grade_documents.return_value = [
            {
                "id": "CAR-001",
                "text": "doc 1",
                "metadata": {"category": "car_insurance"},
            }
        ]

        result = _search_and_grade(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            "car_insurance",
        )

        self.assertEqual(len(result), 1)
        mock_grade_documents.assert_called_once()

        graded_docs = mock_grade_documents.call_args[0][1]
        self.assertEqual(len(graded_docs), 1)
        self.assertEqual(graded_docs[0]["id"], "CAR-001")

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_very_close_top_match_survives_even_if_grader_rejects_it(
        self,
        mock_model,
        mock_collection,
        mock_grade_documents,
    ):
        """
        จำลอง bug จริงที่เจอ: AI grader (โมเดลเล็ก) ตัดสินไม่เสถียร บางครั้งปัดตก
        เอกสารที่จริงๆ เกี่ยวข้องมาก (พิสูจน์แล้วว่าคำถามความหมายเดียวกัน แค่เรียงประโยค
        ต่างกันเล็กน้อย grader ให้ผลต่างกันได้) เอกสารอันดับ 1 ที่ระยะห่าง embedding
        ใกล้มาก (<= HIGH_CONFIDENCE_DISTANCE_THRESHOLD) ต้องไม่ถูกปัดตกไปทั้งที่ grader
        ปฏิเสธ
        """
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection.query.return_value = {
            "ids": [["CAR-008", "CAR-001"]],
            "documents": [["doc เบี้ยประกัน", "doc อื่น"]],
            "metadatas": [[
                {"category": "car_insurance"},
                {"category": "car_insurance"},
            ]],
            "distances": [[0.22, 0.33]],
        }

        mock_grade_documents.return_value = []

        result = _search_and_grade(
            "อัตราเบี้ยประกันภัยรถยนต์",
            "car_insurance",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "CAR-008")

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_moderately_close_top_match_is_not_forced_when_grader_rejects_it(
        self,
        mock_model,
        mock_collection,
        mock_grade_documents,
    ):
        """ระยะห่างไม่ถึงระดับ "มั่นใจสูง" (เกิน threshold) ต้องยังเชื่อ grader ตามปกติ"""
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection.query.return_value = {
            "ids": [["CAR-012"]],
            "documents": [["doc ไม่เกี่ยวข้อง"]],
            "metadatas": [[{"category": "car_insurance"}]],
            "distances": [[0.4]],
        }

        mock_grade_documents.return_value = []

        result = _search_and_grade(
            "คำถามกำกวม",
            "car_insurance",
        )

        self.assertEqual(result, [])

    @patch("retrieval_pipeline.grade_documents")
    @patch("retrieval_pipeline._client")
    @patch("retrieval_pipeline._collection")
    @patch("retrieval_pipeline._model")
    def test_stale_collection_reference_recovers_by_refetching_once(
        self,
        mock_model,
        mock_collection,
        mock_client,
        mock_grade_documents,
    ):
        """
        จำลองเคสจริง: รัน ingest.py ใหม่ (ลบ+สร้าง collection ใหม่) ระหว่างที่ backend
        ยังถือ reference ของ collection เก่าอยู่ ChromaDB จะโยน error
        "Collection [uuid] does not exist" เมื่อ query ด้วย reference เก่า
        ต้องจับ error นี้แล้วขอ reference ใหม่จาก _client มา query ซ้ำอีกครั้งหนึ่งครั้ง
        โดยไม่ต้อง restart process
        """
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        fresh_collection = MagicMock()
        fresh_collection.query.return_value = {
            "ids": [["CAR-001"]],
            "documents": [["doc 1"]],
            "metadatas": [[{"category": "car_insurance"}]],
            "distances": [[0.2]],
        }
        mock_client.get_collection.return_value = fresh_collection

        mock_collection.query.side_effect = Exception(
            "Error getting collection: Collection [00e85983-6c61-4d95-96a7-a6c35ffd8b48] does not exist."
        )

        mock_grade_documents.return_value = [
            {
                "id": "CAR-001",
                "text": "doc 1",
                "metadata": {"category": "car_insurance"},
            }
        ]

        result = _search_and_grade(
            "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง",
            "car_insurance",
        )

        self.assertEqual(len(result), 1)
        mock_client.get_collection.assert_called_once_with(
            retrieval_pipeline.COLLECTION_NAME
        )
        fresh_collection.query.assert_called_once()


if __name__ == "__main__":
    unittest.main()