import unittest

from hallucination_grader import HALLUCINATION_GRADER_MODEL
from query_rewriter import REWRITER_MODEL
from retrieval_grader import GRADER_MODEL


class ModelConfigTest(unittest.TestCase):

    def test_pipeline_does_not_use_gpt_4o_mini(self):
        models = {
            REWRITER_MODEL,
            GRADER_MODEL,
            HALLUCINATION_GRADER_MODEL,
        }

        self.assertNotIn("openai/gpt-4o-mini", models)
        self.assertEqual(models, {"google/gemma-3-4b-it"})


if __name__ == "__main__":
    unittest.main()
