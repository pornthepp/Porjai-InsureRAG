import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()