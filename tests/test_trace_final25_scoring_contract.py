from __future__ import annotations

import os
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
TEST_LMU_ROOT = Path("/tmp/trace-final25-tests-lmudata")
TEST_LMU_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["LMUData"] = str(TEST_LMU_ROOT)
for path in (SCRIPTS_ROOT, VLMEVAL_ROOT, VLMEVAL_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from benchmark_queue_lib import (  # noqa: E402
    BENCHMARK_RUN_SETS,
    MME_REASONING_MD5,
    MME_REASONING_TSV_URL,
    TRACE_FINAL25_BENCHMARKS,
    TRACE_FINAL25_BENCHMARK_CATEGORIES,
    _repair_treebench_options,
    build_vlmeval_dataset,
    spec_by_key,
)
from run_external_benchmark_score_queue import (  # noqa: E402
    _parse_chartmuseum_judgement_output,
    _patch_screenspot_point_parser,
    _resolve_charxiv_extracted_answer,
    _resolve_evochart_judgement,
    _run_score_for_spec,
    _run_tablevqabench_local_score,
)
from run_llm_extracted_benchmark_score_queue import (  # noqa: E402
    _inline_dot_option_columns,
    _inline_option_columns,
    _literal_options,
    _validate_required_choice_contract,
    _valid_letters_for,
    build_parser as build_llm_extract_parser,
)
from run_mme_reasoning_eval import _validate_extraction  # noqa: E402
from reuse_trace_final25_generation_rows import (  # noqa: E402
    _candidate_from_summary,
    _link_candidate,
)
from trace_benchmark_answer_parsing import (  # noqa: E402
    extract_click_point,
    extract_final_answer,
    parse_binary_score,
)
from trace_final25_contract import (  # noqa: E402
    CONTRACTS,
    CONTRACT_BY_KEY,
    DEDICATED_SCORE_KEYS,
    DIRECT_SCORE_KEYS,
    LLM_EXTRACT_SCORE_KEYS,
    OPTION_TEXT_REQUIRED_KEYS,
)


class TraceFinal25ContractTests(unittest.TestCase):
    def test_suite_has_exactly_25_unique_registered_contracts(self):
        self.assertEqual(len(TRACE_FINAL25_BENCHMARKS), 25)
        self.assertEqual(len(set(TRACE_FINAL25_BENCHMARKS)), 25)
        self.assertEqual(set(CONTRACT_BY_KEY), set(TRACE_FINAL25_BENCHMARKS))
        self.assertEqual(len(CONTRACTS), 25)
        for key in TRACE_FINAL25_BENCHMARKS:
            self.assertEqual(spec_by_key(key).key, key)

    def test_final25_category_counts_match_frozen_suite(self):
        self.assertEqual(
            {category: len(keys) for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items()},
            {
                "Charts, Tables & Structured Figures": 5,
                "Visual Mathematics": 4,
                "Science & Academic Reasoning": 4,
                "Spatial, 3D, Embodied & UI Grounding": 4,
                "Visual Perception, Counting & Evidence Grounding": 4,
                "Puzzles & Abstract Logic": 4,
            },
        )

    def test_score_routes_are_disjoint_and_exhaustive(self):
        routes = [set(DIRECT_SCORE_KEYS), set(LLM_EXTRACT_SCORE_KEYS), set(DEDICATED_SCORE_KEYS)]
        self.assertFalse(routes[0] & routes[1])
        self.assertFalse(routes[0] & routes[2])
        self.assertFalse(routes[1] & routes[2])
        self.assertEqual(set.union(*routes), set(TRACE_FINAL25_BENCHMARKS))

    def test_final25_is_a_selectable_canonical_run_set(self):
        self.assertIn("trace_final25", BENCHMARK_RUN_SETS)
        parsed = build_llm_extract_parser().parse_args(["--queue-name", "test", "--final25"])
        self.assertTrue(parsed.final25)

    def test_required_option_text_contracts_are_llm_extraction_routes(self):
        self.assertTrue(set(OPTION_TEXT_REQUIRED_KEYS) <= set(LLM_EXTRACT_SCORE_KEYS))

    def test_erqa_builder_pins_easi_erqabench_class(self):
        built = SimpleNamespace(data=pd.DataFrame())
        erqabench_module = types.ModuleType("vlmeval.dataset.erqabench")
        erqabench_module.ERQABench = mock.Mock(return_value=built)
        vlmeval_module = types.ModuleType("vlmeval")
        vlmeval_module.__path__ = []
        dataset_module = types.ModuleType("vlmeval.dataset")
        dataset_module.__path__ = []
        with mock.patch.dict(
            sys.modules,
            {
                "vlmeval": vlmeval_module,
                "vlmeval.dataset": dataset_module,
                "vlmeval.dataset.erqabench": erqabench_module,
            },
        ):
            result = build_vlmeval_dataset(spec_by_key("erqa"))
        self.assertIs(result, built)
        erqabench_module.ERQABench.assert_called_once_with(dataset="ERQA")

    def test_mme_builder_installs_pinned_release_url_and_checksum(self):
        built = SimpleNamespace(data=pd.DataFrame())

        class FakeMMEReasoning:
            DATASET_URL = {}
            DATASET_MD5 = {}

        vlmeval_module = types.ModuleType("vlmeval")
        vlmeval_module.__path__ = []
        dataset_module = types.ModuleType("vlmeval.dataset")
        dataset_module.__path__ = []
        dataset_module.build_dataset = mock.Mock(return_value=built)
        image_vqa_module = types.ModuleType("vlmeval.dataset.image_vqa")
        image_vqa_module.MMEReasoning = FakeMMEReasoning
        with mock.patch.dict(
            sys.modules,
            {
                "vlmeval": vlmeval_module,
                "vlmeval.dataset": dataset_module,
                "vlmeval.dataset.image_vqa": image_vqa_module,
            },
        ):
            result = build_vlmeval_dataset(spec_by_key("mme_reasoning"))
        self.assertIs(result, built)
        self.assertEqual(FakeMMEReasoning.DATASET_URL["MME-Reasoning"], MME_REASONING_TSV_URL)
        self.assertEqual(FakeMMEReasoning.DATASET_MD5, {"MME-Reasoning": MME_REASONING_MD5})

    def test_treebench_repairs_shifted_option_row(self):
        dataset = SimpleNamespace(
            data=pd.DataFrame(
                [
                    {
                        "index": 330,
                        "question": "What is the boy doing?",
                        "answer": "D",
                        "A": "He is standing. B. He is lying down.",
                        "B": "He is running.",
                        "C": "He is sitting.",
                    }
                ]
            )
        )
        repairs = _repair_treebench_options(dataset)
        row = dataset.data.iloc[0]
        self.assertEqual(row["A"], "He is standing.")
        self.assertEqual(row["B"], "He is lying down.")
        self.assertEqual(row["C"], "He is running.")
        self.assertEqual(row["D"], "He is sitting.")
        self.assertEqual(repairs[0]["index"], "330")

    def test_treebench_accepts_image_embedded_options_without_changing_prompt(self):
        option_blob = "A. first choice\nB. second choice\nC. third choice\nD. fourth choice"
        dataset = SimpleNamespace(
            data=pd.DataFrame(
                [
                    {
                        "index": 142,
                        "question": "Recognize the question and options in the image and answer it.",
                        "answer": "D",
                        "multi-choice options": option_blob,
                    }
                ]
            )
        )
        repairs = _repair_treebench_options(dataset)
        self.assertEqual(repairs, [])
        self.assertNotIn("A", dataset.data.columns)

    def test_treebench_metadata_options_are_available_to_extractor(self):
        row = {
            "multi-choice options": "A. first choice\nB. second choice\nC. third choice\nD. fourth choice"
        }
        self.assertEqual(
            _literal_options(row),
            {"A": "first choice", "B": "second choice", "C": "third choice", "D": "fourth choice"},
        )

    def test_treebench_metadata_options_support_source_label_quirks(self):
        row = {
            "multi-choice options": (
                "A First choice\nB Second choice\n C First C choice\nC. Duplicate C choice"
            )
        }
        self.assertEqual(
            _literal_options(row),
            {"A": "First choice", "B": "Second choice", "C": "First C choice"},
        )
        self.assertEqual(_valid_letters_for("treebench", row), "ABC")

    def test_treebench_refuses_missing_unrepairable_ground_truth(self):
        dataset = SimpleNamespace(
            data=pd.DataFrame([{"index": 7, "answer": "D", "A": "one", "B": "two", "C": "three"}])
        )
        with self.assertRaisesRegex(ValueError, "ground-truth option missing"):
            _repair_treebench_options(dataset)

    def test_phyx_inline_option_block_wins_over_prose_prefix(self):
        question = (
            "A. H. Pfund's method is discussed in the stem. "
            "OPTION: A: alpha B: beta C: gamma D: delta"
        )
        row = {"question": question, "answer": "C"}
        self.assertEqual(_inline_option_columns(question), {"A": "alpha", "B": "beta", "C": "gamma", "D": "delta"})
        self.assertEqual(_valid_letters_for("phyx_mini_mc", row), "ABCD")

    def test_erqa_inline_dot_choices_are_parsed(self):
        question = "Choose one. Choices: A. left B. right C. above D. below"
        self.assertEqual(
            _inline_dot_option_columns(question),
            {"A": "left", "B": "right", "C": "above", "D": "below"},
        )

    def test_valid_letters_do_not_inject_missing_ground_truth(self):
        row = {"question": "Question", "answer": "D", "A": "one", "B": "two"}
        self.assertEqual(_valid_letters_for("generic", row), "AB")

    def test_required_mcq_contract_rejects_missing_ground_truth_option(self):
        item = {
            "benchmark": "blink",
            "index": "bad-row",
            "answer": "D",
            "answer_kind": "option",
            "valid_letters": list("AB"),
            "options": {"A": "one", "B": "two"},
        }
        with self.assertRaisesRegex(ValueError, "missing ground-truth choice"):
            _validate_required_choice_contract(item)

    def test_fixed_mcq_contract_requires_every_expected_choice(self):
        item = {
            "benchmark": "mmstar",
            "index": "bad-row",
            "answer": "B",
            "answer_kind": "option",
            "valid_letters": list("ABCD"),
            "options": {"A": "one", "B": "two", "C": "three"},
        }
        with self.assertRaisesRegex(ValueError, "fixed option contract"):
            _validate_required_choice_contract(item)

    def test_final25_direct_scorer_rejects_non_direct_routes(self):
        args = SimpleNamespace(run_set="trace_final25", run_root=Path("/tmp/unused"))
        with self.assertRaisesRegex(RuntimeError, "run_llm_extracted"):
            _run_score_for_spec(args, spec_by_key("mmstar"), "model", "slug", None)
        with self.assertRaisesRegex(RuntimeError, "run_mme_reasoning_eval"):
            _run_score_for_spec(args, spec_by_key("mme_reasoning"), "model", "slug", None)

    def test_binary_judge_parser_rejects_fuzzy_or_negated_text(self):
        self.assertEqual(parse_binary_score('{"score": 1}'), None)
        self.assertIsNone(parse_binary_score("The answers are not equivalent"))
        self.assertIsNone(parse_binary_score("This looks correct to me"))
        self.assertEqual(parse_binary_score("Judgement: 1"), 1.0)
        self.assertEqual(parse_binary_score("score=0"), 0.0)

    def test_chartmuseum_parser_accepts_explicit_markdown_or_final_decision(self):
        self.assertEqual(_parse_chartmuseum_judgement_output("**Yes**"), 1)
        self.assertEqual(_parse_chartmuseum_judgement_output("**No**\n\nThe answers differ."), 0)
        self.assertEqual(_parse_chartmuseum_judgement_output("Reasoning\nFinal Answer: Yes"), 1)
        self.assertIsNone(_parse_chartmuseum_judgement_output("The answers are not equivalent"))

    def test_charxiv_empty_judge_extraction_falls_back_to_canonical_prediction(self):
        self.assertEqual(
            _resolve_charxiv_extracted_answer(
                {},
                {"score": 0, "extract_answer": ""},
                r"reasoning \boxed{RCU}",
            ),
            ("RCU", "deterministic_boxed"),
        )
        self.assertEqual(
            _resolve_charxiv_extracted_answer({}, {"score": 0, "extract_answer": ""}, None),
            ("", "empty_prediction"),
        )

    def test_evochart_recovers_explicit_score_from_invalid_latex_json(self):
        output = (
            '```json\n{"score": 1, "extracted_answer": '
            '"There are 5 dots after $ \\text{Living Area} = 4000 $."}\n```'
        )
        self.assertEqual(
            _resolve_evochart_judgement(output, r"reasoning \boxed{5}"),
            (1.0, "5", "deterministic_boxed"),
        )

    def test_final_answer_parser_supports_all_canonical_wrappers(self):
        self.assertEqual(extract_final_answer("<answer>42</answer>"), ("42", "answer_tag"))
        self.assertEqual(extract_final_answer(r"reasoning \\boxed{A}"), ("A", "boxed"))
        self.assertEqual(extract_final_answer('text {"answer": "yes"}'), ("yes", "json_answer"))
        self.assertEqual(extract_final_answer("Final answer: blue"), ("blue", "answer_marker"))

    def test_click_parser_supports_named_positional_and_pair_formats(self):
        self.assertEqual(extract_click_point("pyautogui.click(x=12, y=34)"), (12.0, 34.0))
        self.assertEqual(extract_click_point("pyautogui.click(12, 34)"), (12.0, 34.0))
        self.assertEqual(extract_click_point(r"\\boxed{[0.25, 0.75]}"), (0.25, 0.75))

    def test_screenspot_patch_raises_instead_of_scoring_unparsed_as_zero_zero(self):
        _patch_screenspot_point_parser(spec_by_key("screenspot"))
        from vlmeval.dataset.GUI import screenspot

        self.assertEqual(screenspot.parse_bbox_aguvis("pyautogui.click(12, 34)"), [12.0, 34.0])
        with self.assertRaises(ValueError):
            screenspot.parse_bbox_aguvis("I cannot find the target")

    def test_tablevqabench_route_uses_wrapper_parser_and_official_split_scorers(self):
        rows = [
            {"index": 0, "split": "fintabnetqa", "prediction": "<answer>100</answer>", "answer": "100"},
            {"index": 1, "split": "vtabfact", "prediction": r"\\boxed{True}", "answer": "1"},
            {"index": 2, "split": "vwtq", "prediction": '{"answer": "Apple"}', "answer": "Apple"},
            {"index": 3, "split": "vwtq_syn", "prediction": "Final answer: Banana", "answer": "Banana"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame(rows).to_excel(output_dir / "TableVQABench_predictions.xlsx", index=False)
            with mock.patch("run_external_benchmark_score_queue._import_vlmeval_runner", return_value=(None, None)):
                summary = _run_tablevqabench_local_score(
                    spec_by_key("tablevqabench"),
                    "test-model",
                    output_dir,
                )
        self.assertAlmostEqual(summary["score"], 100.0)
        self.assertEqual(summary["rows"], 4)

    def test_mme_extraction_rejects_empty_judge_output(self):
        self.assertEqual(_validate_extraction("choice_prompt", ""), (False, ""))
        self.assertEqual(_validate_extraction("choice_prompt", "A"), (True, "A"))
        self.assertEqual(_validate_extraction("choice_prompt", "[A, C]"), (True, "A,C"))
        self.assertEqual(_validate_extraction("choice_prompt", "The answer is A"), (False, "The answer is A"))

    def test_reuse_campaign_accepts_only_matching_complete_generation_and_hardlinks_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "old" / "runs" / "blink" / "qwen25vl3b-base" / "vlmevalkit_defaults"
            row_dir = source_dir / "api_row_results"
            row_dir.mkdir(parents=True)
            for index in range(2):
                (row_dir / f"{index}.json").write_text(
                    json.dumps({"index": str(index), "row_key": f"0000000{index}:{index}:0123456789abcdef", "prediction": "A"}),
                    encoding="utf-8",
                )
            summary_path = source_dir / "generation_summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "model_slug": "qwen25vl3b-base",
                        "rows": 2,
                        "expected_rows": 2,
                        "generation": {
                            "seed": 42,
                            "temperature": 0.6,
                            "top_p": 1.0,
                            "top_k": -1,
                            "presence_penalty": 0.0,
                            "repetition_penalty": 1.0,
                            "max_tokens": 4096,
                        },
                    }
                ),
                encoding="utf-8",
            )
            candidate = _candidate_from_summary(
                summary_path,
                model_slugs={"qwen25vl3b-base"},
                seeds={42},
                temperature=0.6,
                top_p=1.0,
                top_k=-1,
                presence_penalty=0.0,
                repetition_penalty=1.0,
                max_tokens=4096,
            )
            self.assertIsNotNone(candidate)
            campaign_root = root / "campaign"
            linked = _link_candidate(candidate, campaign_root, dry_run=False)
            self.assertEqual(linked["linked"], 2)
            targets = list((campaign_root / "seed_42" / "runs" / "blink" / "qwen25vl3b-base" / "vlmevalkit_defaults" / "api_row_results").glob("*.json"))
            self.assertEqual(len(targets), 2)
            self.assertEqual(targets[0].stat().st_ino, (row_dir / targets[0].name).stat().st_ino)


if __name__ == "__main__":
    unittest.main()
