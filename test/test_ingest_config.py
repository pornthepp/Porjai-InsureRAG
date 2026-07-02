import unittest

from ingest import COLLECTION_METADATA


class IngestConfigTest(unittest.TestCase):

    def test_collection_uses_cosine_distance(self):
        self.assertEqual(COLLECTION_METADATA, {"hnsw:space": "cosine"})


if __name__ == "__main__":
    unittest.main()