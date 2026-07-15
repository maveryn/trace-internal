from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
EXTENSION_SOURCE = REPO_ROOT / "rlvr" / "vlmevalkit_extensions" / "mirage.py"
if str(VLMEVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(VLMEVAL_ROOT))


from scripts.apply_vlmevalkit_trace_extensions import apply_extensions  # noqa: E402
from vlmeval.dataset import SUPPORTED_DATASETS  # noqa: E402
from vlmeval.dataset.mirage import (MIRAGE, _strip_image_placeholders,  # noqa: E402
                                    mirage_answers_match, mirage_auxeval)


class MIRAGEVLMEvalExtensionTests(unittest.TestCase):

    def test_extension_source_matches_live_checkout(self):
        live = VLMEVAL_ROOT / "vlmeval" / "dataset" / "mirage.py"
        self.assertEqual(EXTENSION_SOURCE.read_bytes(), live.read_bytes())

    def test_extension_installer_is_idempotent(self):
        live_init = (VLMEVAL_ROOT / "vlmeval" / "dataset" / "__init__.py").read_text()
        clean_init = live_init.replace("from .mirage import MIRAGE\n", "")
        clean_init = clean_init.replace("VisionGraphQ3, MIRAGE,", "VisionGraphQ3,")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_root = root / "vlmeval" / "dataset"
            scripts_root = root / "scripts"
            dataset_root.mkdir(parents=True)
            scripts_root.mkdir(parents=True)
            init_path = dataset_root / "__init__.py"
            init_path.write_text(clean_init)

            apply_extensions(root)
            first = init_path.read_text()
            apply_extensions(root)
            second = init_path.read_text()

            self.assertEqual(first, second)
            self.assertIn("from .mirage import MIRAGE", second)
            self.assertIn("VisionGraphQ3, MIRAGE,", second)
            self.assertEqual((dataset_root / "mirage.py").read_bytes(), EXTENSION_SOURCE.read_bytes())

    def test_alias_prompt_and_primary_metric_contracts(self):
        self.assertIn("MIRAGE", SUPPORTED_DATASETS)
        self.assertEqual(MIRAGE.DEFAULT_JUDGE, "qwen3-32b-judge")
        dataset = MIRAGE.__new__(MIRAGE)
        messages = dataset.build_prompt(
            pd.Series(
                {
                    "image_path": "/tmp/mirage_images/7.jpg",
                    "prompt": "Compare the panels.\n<image1>\n<image2>\nAnswer with a number.",
                }
            )
        )
        self.assertEqual(messages[0], {"type": "image", "value": "/tmp/mirage_images/7.jpg"})
        self.assertNotIn("<image", messages[1]["value"])
        self.assertEqual(
            MIRAGE.report_primary_metric(
                {
                    "split=Overall|accuracy": 61.25,
                    "split=Geometry|accuracy": 64.0,
                }
            ),
            {"Overall Accuracy": 61.25},
        )

    def test_answer_matching_covers_all_released_question_types(self):
        self.assertTrue(mirage_answers_match("The final answer is (E).", "E", "multi_choice"))
        self.assertTrue(mirage_answers_match("<answer>12</answer>", "12", "free_form"))
        self.assertTrue(mirage_answers_match("104.9", "100", "approx"))
        self.assertFalse(mirage_answers_match("105.3", "100", "approx"))
        self.assertTrue(mirage_answers_match("Teal Blue or Green", "Teal Blue or Green", "approx"))

    def test_short_reasoning_sentence_uses_extraction_judge(self):
        class Judge:
            calls = 0

            def generate(self, prompt, temperature=0.0):
                self.calls += 1
                return "12"

        judge = Judge()
        result = mirage_auxeval(
            judge,
            {
                "prediction": "Adding 5 and 7 gives a final result of 12.",
                "question_type": "free_form",
                "prompt": "What is 5 + 7?",
            },
        )
        self.assertEqual(judge.calls, 1)
        self.assertEqual(result["parsed_answer"], "12")
        self.assertEqual(result["judge_output"], "12")

    def test_exact_matching_evaluation_persists_details_and_scores(self):
        dataset = MIRAGE.__new__(MIRAGE)
        frame = pd.DataFrame(
            [
                {
                    "index": 0,
                    "answer": "B",
                    "prediction": "<answer>B</answer>",
                    "question_type": "multi_choice",
                    "answer_type": "multi_choice",
                    "normalized_classification": "Logical",
                    "prompt": "Choose A or B.",
                },
                {
                    "index": 1,
                    "answer": "12",
                    "prediction": "The final answer is 12.",
                    "question_type": "free_form",
                    "answer_type": "free_form",
                    "normalized_classification": "Arithmetic",
                    "prompt": "Compute the value.",
                },
                {
                    "index": 2,
                    "answer": "100",
                    "prediction": "<answer>104.9</answer>",
                    "question_type": "approx",
                    "answer_type": "approx",
                    "normalized_classification": "Statistical",
                    "prompt": "Estimate the value.",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            eval_file = Path(tmp) / "MIRAGE_predictions.xlsx"
            frame.to_excel(eval_file, index=False)
            score = dataset.evaluate(str(eval_file), model="exact_matching", nproc=1)

            overall = score[score["split"] == "Overall"].iloc[0]
            self.assertEqual(int(overall["total"]), 3)
            self.assertEqual(int(overall["correct"]), 3)
            self.assertEqual(float(overall["accuracy"]), 100.0)
            detail = Path(tmp) / "MIRAGE_predictions_exact_matching.xlsx"
            self.assertTrue(detail.exists())
            detail_frame = pd.read_excel(detail)
            self.assertEqual(list(detail_frame["hit"]), [1, 1, 1])
            self.assertIn("judge_output", detail_frame)
            self.assertEqual(set(detail_frame["judge_model"]), {"exact_matching"})
            self.assertEqual(set(detail_frame["judge_api_model"]), {"exact_matching"})
            self.assertTrue((Path(tmp) / "MIRAGE_predictions_exact_matching_score.csv").exists())

    def test_image_placeholders_preserve_prompt_structure(self):
        prompt = "Question text\n\n<image1>\n\n<image2>\n\nFinal instruction"
        self.assertEqual(_strip_image_placeholders(prompt), "Question text\n\nFinal instruction")


if __name__ == "__main__":
    unittest.main()
