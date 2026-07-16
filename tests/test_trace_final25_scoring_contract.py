from __future__ import annotations

import concurrent.futures
import hashlib
import importlib.util
import os
import json
import sys
import tempfile
import types
import unittest
from collections import Counter
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
    score_path,
    spec_by_key,
)
from run_external_benchmark_score_queue import (  # noqa: E402
    _judge_cache_entry_needs_retry,
    _judge_retry_token_limits,
    _normalize_logicvista_judgement,
    _parse_chartmuseum_judgement_output,
    _patch_screenspot_point_parser,
    _resolve_charxiv_extracted_answer,
    _resolve_evochart_judgement,
    _restore_screenspot_prediction_metadata,
    _run_score_for_spec,
    _run_tablevqabench_local_score,
    _validate_math_like_judged_table,
)
from run_external_benchmark_score_multi_model_queue import _terminal_failed_jobs  # noqa: E402
from run_llm_extracted_benchmark_score_queue import (  # noqa: E402
    EXTRACTION_CONTRACT_VERSION,
    JudgeOutputValidationError,
    _answer_kind,
    _build_prompt,
    _countqa_needs_combined_total_instruction,
    _done_path,
    _done_result_is_current,
    _failure_path,
    _legacy_raw_output_from_error,
    _inline_dot_option_columns,
    _inline_option_columns,
    _iter_api_batches,
    _job_id_for_row,
    _literal_options,
    _normalize_option,
    _parse_json_object,
    _recover_failed_outputs,
    _request_hash_for_item,
    _result_from_judge_output,
    _score_binary_judge,
    _ordered_fixed_option_columns,
    _ordered_source_option_columns,
    _source_row_exclusion_reason,
    _validate_required_choice_contract,
    _valid_letters_for,
    build_parser as build_llm_extract_parser,
    finalize as finalize_llm_extracted,
    mark_failed,
    run_api_pool,
    write_done_result,
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
    ALL26_CONTRACTS,
    ALL26_CONTRACT_BY_KEY,
    CONTRACTS,
    CONTRACT_BY_KEY,
    DEDICATED_SCORE_KEYS,
    DIRECT_SCORE_KEYS,
    FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS,
    LLM_EXTRACT_SCORE_KEYS,
    OFFICIAL_VLMEVAL_SCORE_KEYS,
    OPTION_TEXT_REQUIRED_KEYS,
)


def _judge_extraction_item(kind: str = "option") -> dict:
    prediction = "The model selected B."
    return {
        "job_id": f"synthetic__{kind}",
        "benchmark": "synthetic",
        "model_slug": "test-model",
        "index": "0",
        "ordinal": 0,
        "answer": "B",
        "answer_kind": kind,
        "valid_letters": list("ABCD"),
        "options": {"A": "circle", "B": "triangle", "C": "square", "D": "star"},
        "prediction": prediction,
        "prompt": "Return strict JSON.",
        "request_hash": "a" * 64,
        "response_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
    }


class TraceFinal25ContractTests(unittest.TestCase):
    def test_suite_has_exactly_25_unique_registered_contracts(self):
        self.assertEqual(len(TRACE_FINAL25_BENCHMARKS), 25)
        self.assertEqual(len(set(TRACE_FINAL25_BENCHMARKS)), 25)
        self.assertEqual(set(CONTRACT_BY_KEY), set(TRACE_FINAL25_BENCHMARKS))
        self.assertEqual(len(CONTRACTS), 25)
        for key in TRACE_FINAL25_BENCHMARKS:
            self.assertEqual(spec_by_key(key).key, key)

    def test_all26_adds_one_explicit_mmvp_contract(self):
        self.assertEqual(len(ALL26_CONTRACTS), 26)
        self.assertEqual(set(ALL26_CONTRACT_BY_KEY), set(CONTRACT_BY_KEY) | {"mmvp"})
        self.assertEqual(
            ALL26_CONTRACT_BY_KEY["mmvp"].runner,
            "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
        )

    def test_final25_category_counts_match_frozen_suite(self):
        self.assertEqual(
            {category: len(keys) for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items()},
            {
                "Charts & Tables": 5,
                "Visual Math": 4,
                "Science & General": 4,
                "Spatial & Grounding": 4,
                "Perception & Counting": 4,
                "Puzzles & Logic": 4,
            },
        )

    def test_score_routes_are_disjoint_and_exhaustive(self):
        official_frozen = set(FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS)
        routes = [set(DIRECT_SCORE_KEYS), official_frozen, set(DEDICATED_SCORE_KEYS)]
        self.assertFalse(routes[0] & routes[1])
        self.assertFalse(routes[0] & routes[2])
        self.assertFalse(routes[1] & routes[2])
        self.assertEqual(set.union(*routes), set(TRACE_FINAL25_BENCHMARKS))
        self.assertEqual(len(OFFICIAL_VLMEVAL_SCORE_KEYS), 15)
        self.assertEqual(set(LLM_EXTRACT_SCORE_KEYS), official_frozen)
        self.assertEqual(
            set(DIRECT_SCORE_KEYS)
            | set(OFFICIAL_VLMEVAL_SCORE_KEYS)
            | set(DEDICATED_SCORE_KEYS),
            set(ALL26_CONTRACT_BY_KEY),
        )

    def test_final25_is_a_selectable_canonical_run_set(self):
        self.assertIn("trace_final25", BENCHMARK_RUN_SETS)
        parsed = build_llm_extract_parser().parse_args(["--queue-name", "test", "--final25"])
        self.assertTrue(parsed.final25)

    def test_legacy_option_text_contracts_are_official_vlmeval_routes(self):
        self.assertTrue(set(OPTION_TEXT_REQUIRED_KEYS) <= set(OFFICIAL_VLMEVAL_SCORE_KEYS))

    def test_official_routes_call_pinned_dataset_evaluate(self):
        for key in OFFICIAL_VLMEVAL_SCORE_KEYS:
            self.assertEqual(
                ALL26_CONTRACT_BY_KEY[key].runner,
                "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
            )

    def test_special_official_route_selections_are_explicit(self):
        self.assertIn("The answer is X", CONTRACT_BY_KEY["chartqapro"].extraction)
        self.assertIn("Score (Strict)", CONTRACT_BY_KEY["wemath"].scoring)
        self.assertIn("EASI ERQABench", CONTRACT_BY_KEY["erqa"].scoring)

    def test_mathvision_validator_preserves_literal_none_extraction(self):
        spec = spec_by_key("mathvision")
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame({"index": [957], "res": ["None"]}).to_excel(
                output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx", index=False
            )
            _validate_math_like_judged_table(spec, output_dir)

    def test_mathvision_validator_rejects_truly_empty_extraction(self):
        spec = spec_by_key("mathvision")
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame({"index": [957], "res": [""]}).to_excel(
                output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx", index=False
            )
            with self.assertRaisesRegex(RuntimeError, "1 empty extractions"):
                _validate_math_like_judged_table(spec, output_dir)

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

    def test_visualpuzzles_numpy_style_option_array_is_parsed(self):
        self.assertEqual(
            _literal_options({"options": "['32' '35' '37' '40']"}),
            {"A": "32", "B": "35", "C": "37", "D": "40"},
        )

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

    def test_erqa_ordered_parser_preserves_letter_valued_choices(self):
        question = (
            "Which point is on the mushroom cap? "
            "Choices: A. A. B. B. C. C. D. D. "
            "Please answer directly with only the letter of the correct option and nothing else."
        )
        self.assertEqual(
            _ordered_fixed_option_columns(question),
            {"A": "A", "B": "B", "C": "C", "D": "D"},
        )

    def test_erqa_ordered_parser_supports_binary_and_coordinate_layouts(self):
        self.assertEqual(
            _ordered_source_option_columns(
                "Question? Choices: A. Yes. B. No. Please answer directly with only the letter."
            ),
            {"A": "Yes", "B": "No"},
        )
        self.assertEqual(
            _ordered_source_option_columns(
                "Which point? A) [1 2] B) [3 4] C) [5 6] D) [7 8] "
                "Please answer directly with only the letter."
            ),
            {"A": "[1 2]", "B": "[3 4]", "C": "[5 6]", "D": "[7 8]"},
        )

    def test_erqa_malformed_but_scoreable_source_row_uses_visible_choices(self):
        row = {
            "index": 271,
            "question": "Choices: A. B. No. C. Yes. D. Please answer directly with only the letter.",
            "answer": "B",
        }
        self.assertEqual(_valid_letters_for("erqa", row), "BC")

    def test_valid_letters_do_not_inject_missing_ground_truth(self):
        row = {"question": "Question", "answer": "D", "A": "one", "B": "two"}
        self.assertEqual(_valid_letters_for("generic", row), "AB")

    def test_duplicate_source_indices_get_stable_ordinal_job_ids(self):
        counts = Counter({"6710": 2})
        last = {"6710": 1010}
        self.assertEqual(
            _job_id_for_row("countqa", "model", "6710", 103, counts, last),
            "countqa__model__6710__ordinal103",
        )
        self.assertEqual(
            _job_id_for_row("countqa", "model", "6710", 1010, counts, last),
            "countqa__model__6710",
        )

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

    def test_mmstar_accepts_source_variable_prefix_choices(self):
        item = {
            "benchmark": "mmstar",
            "index": "binary-row",
            "answer": "B",
            "answer_kind": "option",
            "valid_letters": list("AB"),
            "options": {"A": "first image", "B": "second image"},
        }
        _validate_required_choice_contract(item)

    def test_mmstar_accepts_nonprefix_source_choice_labels(self):
        item = {
            "benchmark": "mmstar",
            "index": "391",
            "answer": "D",
            "answer_kind": "option",
            "valid_letters": list("ABD"),
            "options": {"A": "Two", "B": "One", "D": "Three"},
        }
        _validate_required_choice_contract(item)

    def test_mmstar_rejects_fewer_than_two_choices(self):
        item = {
            "benchmark": "mmstar",
            "index": "bad-row",
            "answer": "A",
            "answer_kind": "option",
            "valid_letters": list("A"),
            "options": {"A": "only choice"},
        }
        with self.assertRaisesRegex(ValueError, "variable source option contract"):
            _validate_required_choice_contract(item)

    def test_mmstar_known_missing_gold_source_rows_are_excluded(self):
        self.assertEqual(
            _source_row_exclusion_reason(
                "mmstar",
                "268",
                "A",
                {"B": "Three", "C": "Two", "D": "One"},
            ),
            "official source omits the gold A option text",
        )
        self.assertEqual(
            _source_row_exclusion_reason(
                "mmstar",
                "268",
                "A",
                {"A": "Four", "B": "Three", "C": "Two", "D": "One"},
            ),
            "",
        )

    def test_final25_direct_scorer_rejects_non_direct_routes(self):
        args = SimpleNamespace(run_set="trace_final25", run_root=Path("/tmp/unused"))
        with self.assertRaisesRegex(RuntimeError, "run_llm_extracted"):
            _run_score_for_spec(args, spec_by_key("mmstar"), "model", "slug", None)
        with self.assertRaisesRegex(RuntimeError, "run_mme_reasoning_eval"):
            _run_score_for_spec(args, spec_by_key("mme_reasoning"), "model", "slug", None)

    def test_llm_extraction_finalizer_writes_canonical_and_analysis_score_paths(self):
        item = {
            "job_id": "countbenchqa__test-model__0",
            "benchmark": "countbenchqa",
            "model_slug": "test-model",
            "index": "0",
            "ordinal": 0,
            "answer": "4",
            "answer_kind": "number",
            "valid_letters": [],
            "options": {},
            "prediction": "The final answer is 4.",
            "extracted": "4",
            "extraction_status": "resolved",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "llm_extracted",
                queue_name="queue",
                benchmarks=["countbenchqa"],
                model_entries=[("test-model", "/models/test-model")],
                benchmark_root=root / "benchmark",
                run_root=root / "runs",
                judge_model="/models/qwen3-32b-judge",
                seed=42,
            )
            with (
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.load_manifest",
                    return_value=[item],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._load_results",
                    return_value=[item],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._score_with_category_breakdowns",
                    return_value={"Overall": 100.0},
                ),
                mock.patch.dict(os.environ, {"TRACE_FINAL25_HF_SPOOL_ROOT": ""}),
            ):
                finalize_llm_extracted(args)

            canonical = score_path(spec_by_key("countbenchqa"), "test-model", args.benchmark_root)
            analysis = (
                args.benchmark_root
                / "countbenchqa"
                / "test-model"
                / "llm_extracted"
                / "scores.json"
            )
            self.assertNotEqual(canonical, analysis)
            self.assertTrue(canonical.is_file())
            self.assertTrue(analysis.is_file())
            canonical_payload = json.loads(canonical.read_text(encoding="utf-8"))
            analysis_payload = json.loads(analysis.read_text(encoding="utf-8"))
            self.assertEqual(canonical_payload, analysis_payload)
            self.assertEqual(canonical_payload["score"], 100.0)
            self.assertEqual(canonical_payload["rows"], 1)
            self.assertEqual(canonical_payload["benchmark_score_path"], str(canonical))
            self.assertEqual(
                canonical_payload["llm_extracted_benchmark_score_path"],
                str(analysis),
            )

    def test_multi_model_queue_reports_exhausted_failed_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "queue.json"
            queue.write_text(
                json.dumps(
                    {
                        "jobs": {
                            "mathverse": {
                                "status": "failed",
                                "attempts": 2,
                                "error": "malformed decision",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                _terminal_failed_jobs(queue, [("mathverse", root / "missing.json")], 2),
                [("mathverse", "malformed decision")],
            )

    def test_binary_judge_parser_rejects_fuzzy_or_negated_text(self):
        self.assertEqual(parse_binary_score('{"score": 1}'), 1.0)
        self.assertIsNone(parse_binary_score("The answers are not equivalent"))
        self.assertIsNone(parse_binary_score("This looks correct to me"))
        self.assertEqual(parse_binary_score("Judgement: 1"), 1.0)
        self.assertEqual(parse_binary_score("Final Judgement: **1**"), 1.0)
        self.assertEqual(parse_binary_score("Final Judgement:\n_0_"), 0.0)
        self.assertEqual(parse_binary_score("Judge output: 0"), 0.0)
        self.assertEqual(parse_binary_score("score=0"), 0.0)
        self.assertEqual(parse_binary_score('{"score": 0, "answer": "wrong"}'), 0.0)

    def test_fenced_json_decoder_handles_latex_braces_inside_answer(self):
        raw = '```json\n{"score": 0, "answer": "E = \\\\frac{a}{b}"}\n```'
        self.assertEqual(_parse_json_object(raw), {"score": 0, "answer": r"E = \frac{a}{b}"})

    def test_strict_judge_envelope_preserves_valid_legacy_forms(self):
        cases = (
            ("option", '{"answer":"B"}', "B", "judge_json", False, None),
            ("option", '```json\n{"answer":"B"}\n```', "B", "judge_fenced_json", False, None),
            ("option", 'Result follows: {"extracted_answer":"B"}', "B", "judge_embedded_json", False, None),
            ("option", '{"answer":"B"}\n{"extracted_answer":"B"}', "B", "judge_embedded_json", False, None),
            ("option", '{"answer":"E"}', "Z", "judge_json", True, None),
            ("option_value", '{"answer":"B"}', "B", "judge_json", False, None),
            ("number", '{"answer":4}', "4", "judge_json", False, None),
            ("number", '{"answer":""}', "", "judge_json", True, None),
            ("short", '{"answer":12.5}', "12.5", "judge_json", False, None),
            ("short", '{"answer":""}', "", "judge_json", True, None),
            ("braced", '{"answer":"{Yes}"}', "yes", "judge_json", False, None),
            ("judge_binary", '{"score":0,"answer":""}', "", "judge_json", True, 0.0),
            (
                "judge_binary",
                '```json\n{"score":0,"answer":"E = \\\\frac{a}{b}"}\n```',
                r"E = \frac{a}{b}",
                "judge_fenced_json",
                False,
                0.0,
            ),
            ("judge_binary", "Final Judgement: **1**", "", "judge_atomic_binary", True, 1.0),
        )
        for kind, raw, expected, method, abstention, score in cases:
            with self.subTest(kind=kind, raw=raw):
                result = _result_from_judge_output(_judge_extraction_item(kind), raw)
                self.assertEqual(result["extracted"], expected)
                self.assertEqual(result["extraction_status"], "resolved")
                self.assertEqual(result["extraction_method"], method)
                self.assertEqual(result["explicit_abstention"], abstention)
                self.assertEqual(result.get("judge_score"), score)
                self.assertEqual(result["validation_contract_version"], EXTRACTION_CONTRACT_VERSION)

    def test_strict_judge_envelope_rejects_malformed_or_conflicting_output(self):
        cases = (
            ("option", "B", "missing_json"),
            ("option", "answer: B", "missing_json"),
            ("option", '{"foo":"B"}', "missing_answer"),
            ("option", '{"answer":"B"', "malformed_json"),
            ("option", '[{"answer":"B"}]', "malformed_json"),
            ("option", '{"answer":["B"]}', "answer_type"),
            ("option", '{"answer":"A","extracted_answer":"B"}', "conflicting_answers"),
            ("option", '{"answer":"A","answer":"B"}', "duplicate_json_field"),
            ("option", '{"answer":"A or B"}', "conflicting_answers"),
            ("option", '{"answer":"a or b"}', "conflicting_answers"),
            ("option", '{"answer":"Either C, maybe D"}', "conflicting_answers"),
            ("option", '{"answer":"AB"}', "conflicting_answers"),
            ("option", 'Final answer: A\n{"answer":"B"}', "conflicting_answers"),
            ("option", '{"answer":"B"}\nFinal answer: A', "conflicting_answers"),
            ("option", '{"answer":"yellow"}', "answer_value"),
            ("number", '{"answer":"none"}', "answer_value"),
            ("number", '{"answer":"4 or 5"}', "conflicting_answers"),
            ("judge_binary", "This looks correct to me", "missing_binary_score"),
            ("judge_binary", "Score: 1. Judgment: 0.", "missing_binary_score"),
            ("judge_binary", '{"score":1', "malformed_json"),
            ("judge_binary", '{"score":2}', "binary_score_value"),
            ("judge_binary", '{"score":"Score: 1. Judgment: 0."}', "binary_score_value"),
            ("judge_binary", '{"score":0} {"judgement":1}', "conflicting_binary_scores"),
            ("judge_binary", '{"score":1,"score":0}', "duplicate_json_field"),
            ("judge_binary", 'Score: 1\n{"score":0}', "conflicting_binary_scores"),
        )
        for kind, raw, code in cases:
            with self.subTest(kind=kind, raw=raw):
                with self.assertRaises(JudgeOutputValidationError) as raised:
                    _result_from_judge_output(_judge_extraction_item(kind), raw)
                self.assertEqual(raised.exception.code, code)

    def test_chartqapro_conversational_extraction_targets_only_final_turn(self):
        questions = [
            "who is ranked as the highest-paid athlete in 2023?",
            "how many soccer players are in the top 50?",
            "is this more than the number of baseball players?",
            "which sport has the most athletes in the top 50 list?",
            "is serena ahead of most other athletes on the list?",
        ]
        answers = ["Cristiano Ronaldo", "10", "Yes", "Basketball", "No"]
        item = {
            **_judge_extraction_item("short"),
            "benchmark": "chartqapro",
            "question": repr(questions),
            "answer": repr(answers),
            "prediction": "The answer is: no",
        }

        self.assertEqual(_answer_kind("chartqapro", item), "short")
        prompt = _build_prompt(item)
        question_section = prompt.split("Question:\n", 1)[1].split("\n\nModel response:", 1)[0]
        self.assertEqual(question_section, questions[-1])
        self.assertIn("scores only the final turn", prompt)
        self.assertIn("ignore answers to earlier turns", prompt)

        result = _result_from_judge_output(item, '{"answer":"no"}')
        self.assertEqual(result["extracted"], "no")

        conflicting = "\n".join(
            f'{{"answer": {json.dumps(answer)}}}' for answer in answers
        )
        with self.assertRaises(JudgeOutputValidationError) as raised:
            _result_from_judge_output(item, conflicting)
        self.assertEqual(raised.exception.code, "conflicting_answers")
        self.assertEqual(raised.exception.status, "ambiguous")

    def test_pinned_chartqapro_scorer_uses_only_final_conversational_answer(self):
        module_path = VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "chartqapro.py"
        spec = importlib.util.spec_from_file_location("pinned_chartqapro_utils_test", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        anls_module = types.ModuleType("anls")
        anls_module.anls_score = lambda prediction, gold_labels, threshold: float(
            prediction in gold_labels
        )
        row = {
            "Answer": ["Cristiano Ronaldo", "10", "Yes", "Basketball", "No"],
            "Question Type": "Conversational",
            "Year": ["NO", "NO", "NO", "NO", "NO"],
        }
        with mock.patch.dict(sys.modules, {"anls": anls_module}):
            final_only = module.evaluate_predictions_chartqapro(
                [{**row, "prediction": "No"}]
            )
            all_turns = module.evaluate_predictions_chartqapro(
                [{**row, "prediction": repr(row["Answer"])}]
            )

        self.assertEqual(final_only["Overall"], 1.0)
        self.assertEqual(all_turns["Overall"], 0.0)

    def test_countqa_prompt_requests_combined_total_without_relaxing_validation(self):
        item = {
            **_judge_extraction_item("number"),
            "benchmark": "countqa",
            "question": "How many chairs, tables, and heaters are there?",
            "answer": "13",
            "prediction": "Final answer: 6 chairs, 2 tables, and 2 heaters.",
        }

        prompt = _build_prompt(item)
        self.assertIn("CountQA expects one combined total", prompt)
        self.assertIn("one labeled count for every requested category", prompt)
        self.assertIn("cover every requested category exactly once", prompt)
        self.assertIn("Do not infer a missing category", prompt)
        self.assertIn("3 cups and 2 plates", prompt)

        result = _result_from_judge_output(item, '{"answer":"10"}')
        self.assertEqual(result["extracted"], "10")

        with self.assertRaises(JudgeOutputValidationError) as raised:
            _result_from_judge_output(
                item,
                '{"answer":"6 chairs, 2 tables, and 2 heaters"}',
            )
        self.assertEqual(raised.exception.code, "conflicting_answers")
        self.assertEqual(raised.exception.status, "ambiguous")

    def test_countqa_combined_total_prompt_is_scoped_to_explicit_component_answers(self):
        self.assertTrue(
            _countqa_needs_combined_total_instruction(
                "How many bananas and kinderjoys are there?",
                r"The final answer is \boxed{7 bananas and 4 Kinder Joy eggs}.",
            )
        )
        self.assertFalse(
            _countqa_needs_combined_total_instruction(
                "How many bananas and kinderjoys are there?",
                r"The final answer is \boxed{11}.",
            )
        )
        self.assertFalse(
            _countqa_needs_combined_total_instruction(
                "How many tiles are on the wall with the shower?",
                r"The final answer is \boxed{18}.",
            )
        )

    def test_countqa_combined_total_instruction_is_not_used_for_countbenchqa(self):
        item = {
            **_judge_extraction_item("number"),
            "benchmark": "countbenchqa",
            "question": "How many chairs are there?",
            "answer": "6",
            "prediction": "Final answer: 6 chairs.",
        }

        prompt = _build_prompt(item)
        self.assertNotIn("combined total", prompt)

    def test_physics_final25_contract_uses_the_dedicated_official_like_scorer(self):
        contract = CONTRACT_BY_KEY["physics"]
        self.assertIn("official VLMEvalKit boxed-answer", contract.extraction)
        self.assertIn("official VLMEvalKit is_equiv", contract.scoring)
        self.assertEqual(contract.runner, "run_external_benchmark_score_queue.py:physics_local_judge")
        self.assertIn("physics", DIRECT_SCORE_KEYS)
        self.assertNotIn("physics", LLM_EXTRACT_SCORE_KEYS)

    def test_strict_judge_envelope_preserves_equivalent_and_json_internal_wrappers(self):
        cases = (
            ("option", 'Final answer: B\n{"answer":"B"}', "B"),
            ("option", '{"answer":"B because C is wrong"}', "B"),
            ("option", '{"answer":"B, a triangle"}', "B"),
            ("number", '{"answer":"1,000"}', "1000"),
            ("number", '{"answer":"about $4.0%"}', "4"),
            ("short", '{"answer":"<answer>B</answer>"}', "<answer>B</answer>"),
            ("short", 'Final answer: \\boxed{42}\n{"answer":"42"}', "42"),
            ("judge_binary", '{"score":1,"answer":"\\\\boxed{42}"}', r"\boxed{42}"),
        )
        for kind, raw, expected in cases:
            with self.subTest(kind=kind, raw=raw):
                result = _result_from_judge_output(_judge_extraction_item(kind), raw)
                self.assertEqual(result["extracted"], expected)

    def test_v2_done_cache_revalidates_the_judge_envelope(self):
        item = _judge_extraction_item("option")
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(output_root=Path(tmp), queue_name="strict-cache")
            write_done_result(args, item, _result_from_judge_output(item, '{"answer":"B"}'))
            self.assertTrue(_done_result_is_current(args, item))

            path = _done_path(args, item["job_id"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["judge_output"] = "B"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(_done_result_is_current(args, item))

            write_done_result(args, item, _result_from_judge_output(item, '{"answer":"B"}'))
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["answer"] = "A"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(_done_result_is_current(args, item))

    def test_extraction_request_hash_binds_backend_and_api_tokenizer(self):
        item = {
            **_judge_extraction_item("option"),
            "model_path": "model",
            "question": "Which option?",
        }
        common = {
            "judge_model": "judge",
            "api_model": "served-judge",
            "api_tokenizer_model": "tokenizer-a",
            "judge_max_tokens": 64,
        }
        api_hash = _request_hash_for_item(
            SimpleNamespace(**common, execution_backend="api"), item
        )
        tokenizer_hash = _request_hash_for_item(
            SimpleNamespace(
                **{**common, "api_tokenizer_model": "tokenizer-b"},
                execution_backend="api",
            ),
            item,
        )
        local_hash = _request_hash_for_item(
            SimpleNamespace(**common, execution_backend="local"), item
        )
        self.assertNotEqual(api_hash, tokenizer_hash)
        self.assertNotEqual(api_hash, local_hash)

    def test_legacy_unbound_failed_output_is_not_promoted(self):
        item = _judge_extraction_item("option")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "out",
                queue_name="strict-recovery",
                queue_root=root / "queue",
                judge_model="judge",
            )
            args.queue_root.mkdir(parents=True)
            (args.queue_root / "llm_extract_strict-recovery.json").write_text(
                json.dumps(
                    {
                        "jobs": {
                            item["job_id"]: {
                                "status": "failed",
                                "error": "legacy failure",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            failure_path = _failure_path(args, item["job_id"])
            failure_path.parent.mkdir(parents=True)
            failure_path.write_text(
                json.dumps({"raw_output": '{"answer":"B"}'}), encoding="utf-8"
            )

            recovered, unrecoverable = _recover_failed_outputs(args, [item])

            self.assertEqual((recovered, unrecoverable), (0, 1))
            self.assertFalse(_done_path(args, item["job_id"]).exists())

            failure_path.write_text(
                json.dumps(
                    {
                        "raw_output": '{"answer":"B"}',
                        "request_hash": item["request_hash"],
                        "response_sha256": item["response_sha256"],
                        "contract_version": EXTRACTION_CONTRACT_VERSION,
                        "validation_failure": {"code": "incomplete_generation"},
                    }
                ),
                encoding="utf-8",
            )
            recovered, unrecoverable = _recover_failed_outputs(args, [item])
            self.assertEqual((recovered, unrecoverable), (0, 1))
            self.assertFalse(_done_path(args, item["job_id"]).exists())

    def test_terminal_validation_failure_keeps_structured_metadata(self):
        item = _judge_extraction_item("option")
        with self.assertRaises(JudgeOutputValidationError) as raised:
            _result_from_judge_output(item, "answer: B")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "out",
                queue_name="strict-failure",
                queue_root=root / "queue",
                worker_id="test-worker",
            )
            mark_failed(
                args,
                item,
                repr(raised.exception),
                raw_output="answer: B",
                validation_failure=raised.exception.as_dict(),
            )
            failure = json.loads(_failure_path(args, item["job_id"]).read_text(encoding="utf-8"))
            self.assertEqual(failure["validation_failure"]["status"], "invalid")
            self.assertEqual(failure["validation_failure"]["code"], "missing_json")
            self.assertEqual(failure["contract_version"], EXTRACTION_CONTRACT_VERSION)

    def test_api_pool_retries_schema_invalid_output_before_writing_done(self):
        item = _judge_extraction_item("option")

        class FakeJudge:
            calls = 0

            def __init__(self, _args):
                self.cleaned = False

            def _get_endpoint_health(self):
                return object()

            def _call_api_completion_batch(self, _health, _start, prompts, **_kwargs):
                type(self).calls += 1
                raw = "B" if type(self).calls == 1 else '{"answer":"B"}'
                return [
                    {
                        "judge_output": raw,
                        "judge_finish_reason": "stop",
                        "judge_output_token_count": 4,
                        "judge_api_endpoint": "http://judge",
                    }
                    for _ in prompts
                ]

            def cleanup(self):
                self.cleaned = True

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "out",
                queue_name="strict-api",
                queue_root=root / "queue",
                worker_id="test-worker",
                api_bases=["http://judge"],
                api_parallelism=1,
                api_batches_per_endpoint=1,
                api_batch_size=1,
                api_max_batch_chars=10_000,
                api_model="judge",
                api_tokenizer_model="judge",
                api_timeout=1.0,
                api_max_retries=1,
                api_endpoint_failure_threshold=1,
                api_endpoint_cooldown_seconds=0.0,
                api_retry_base_delay=0.0,
                judge_model="judge",
                judge_max_tokens=64,
            )
            FakeJudge.calls = 0
            with (
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.load_manifest",
                    return_value=[item],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._request_hash_for_item",
                    return_value=item["request_hash"],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._load_api_tokenizer",
                    return_value=object(),
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._render_api_prompt",
                    return_value="rendered prompt",
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._judge_retry_token_limits",
                    return_value=[64, 128],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.PersistentJudge",
                    FakeJudge,
                ),
            ):
                run_api_pool(args)

            payload = json.loads(_done_path(args, item["job_id"]).read_text(encoding="utf-8"))
            self.assertEqual(FakeJudge.calls, 2)
            self.assertEqual(payload["extracted"], "B")
            self.assertEqual(payload["judge_retry_count"], 1)
            self.assertTrue(_done_result_is_current(args, item))

    def test_api_batch_iterator_is_lazy_and_preserves_batch_boundaries(self):
        items = [
            {"job_id": str(index), "prompt": prompt}
            for index, prompt in enumerate(("aa", "bb", "cccc", "xxxxxx", "z"))
        ]
        rendered = []

        def render(_tokenizer, prompt):
            rendered.append(prompt)
            return prompt

        with mock.patch(
            "run_llm_extracted_benchmark_score_queue._render_api_prompt",
            side_effect=render,
        ):
            batches = _iter_api_batches(
                items,
                object(),
                batch_size=2,
                max_batch_chars=5,
            )
            self.assertEqual(rendered, [])
            first = next(iter(batches))
            self.assertEqual(rendered, ["aa", "bb"])
            remaining = list(batches)

        self.assertEqual(
            [[item["job_id"] for item, _ in batch] for batch in [first, *remaining]],
            [["0", "1"], ["2"], ["3"], ["4"]],
        )
        self.assertEqual(rendered, ["aa", "bb", "cccc", "xxxxxx", "z"])

    def test_api_pool_requests_first_batch_before_rendering_remaining_rows(self):
        items = []
        for index in range(6):
            item = _judge_extraction_item("option")
            item.update(
                {
                    "job_id": f"synthetic__option__{index}",
                    "index": str(index),
                    "ordinal": index,
                    "prompt": f"prompt {index}",
                    "request_hash": f"{index + 1:064x}",
                }
            )
            items.append(item)

        render_count = 0

        def render(_tokenizer, prompt):
            nonlocal render_count
            render_count += 1
            return f"rendered:{prompt}"

        class FakeJudge:
            calls = []
            instance = None

            def __init__(self, _args):
                self.cleaned = False
                type(self).instance = self

            def _get_endpoint_health(self):
                return object()

            def _call_api_completion_batch(self, _health, _start, prompts, **_kwargs):
                if not type(self).calls:
                    self.assert_first_request_is_streamed()
                type(self).calls.append(list(prompts))
                return [
                    {
                        "judge_output": '{"answer":"B"}',
                        "judge_finish_reason": "stop",
                        "judge_output_token_count": 4,
                        "judge_api_endpoint": "http://judge",
                    }
                    for _ in prompts
                ]

            def assert_first_request_is_streamed(self):
                if render_count != 2:
                    raise AssertionError(
                        f"first request started after rendering {render_count} rows instead of one batch"
                    )

            def cleanup(self):
                self.cleaned = True

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "out",
                queue_name="streaming-api",
                queue_root=root / "queue",
                worker_id="test-worker",
                api_bases=["http://judge"],
                api_parallelism=1,
                api_batches_per_endpoint=1,
                api_batch_size=2,
                api_max_batch_chars=10_000,
                api_queue_capacity=1,
                api_model="judge",
                api_tokenizer_model="judge",
                api_timeout=1.0,
                api_max_retries=1,
                api_endpoint_failure_threshold=1,
                api_endpoint_cooldown_seconds=0.0,
                api_retry_base_delay=0.0,
                judge_model="judge",
                judge_max_tokens=64,
            )
            FakeJudge.calls = []
            with (
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.load_manifest",
                    return_value=items,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._request_hash_for_item",
                    side_effect=lambda _args, item: item["request_hash"],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._load_api_tokenizer",
                    return_value=object(),
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._render_api_prompt",
                    side_effect=render,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._judge_retry_token_limits",
                    return_value=[64],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.PersistentJudge",
                    FakeJudge,
                ),
            ):
                run_api_pool(args)

            self.assertEqual(render_count, len(items))
            self.assertEqual([len(batch) for batch in FakeJudge.calls], [2, 2, 2])
            self.assertTrue(FakeJudge.instance.cleaned)
            self.assertTrue(all(_done_path(args, item["job_id"]).exists() for item in items))

    def test_api_pool_bounds_render_ahead_by_queue_capacity(self):
        items = []
        for index in range(8):
            item = _judge_extraction_item("option")
            item.update(
                {
                    "job_id": f"synthetic__bounded__{index}",
                    "index": str(index),
                    "ordinal": index,
                    "prompt": f"prompt {index}",
                    "request_hash": f"{index + 1:064x}",
                }
            )
            items.append(item)

        render_count = 0
        wait_observations = []

        def render(_tokenizer, prompt):
            nonlocal render_count
            render_count += 1
            return f"rendered:{prompt}"

        original_wait = concurrent.futures.wait

        def observe_wait(futures, **kwargs):
            wait_observations.append((len(futures), render_count))
            return original_wait(futures, **kwargs)

        class FakeJudge:
            calls = 0

            def __init__(self, _args):
                pass

            def _get_endpoint_health(self):
                return object()

            def _call_api_completion_batch(self, _health, _start, prompts, **_kwargs):
                type(self).calls += 1
                return [
                    {
                        "judge_output": '{"answer":"B"}',
                        "judge_finish_reason": "stop",
                        "judge_output_token_count": 4,
                        "judge_api_endpoint": "http://judge",
                    }
                    for _ in prompts
                ]

            def cleanup(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "out",
                queue_name="bounded-api",
                queue_root=root / "queue",
                worker_id="test-worker",
                api_bases=["http://judge"],
                api_parallelism=1,
                api_batches_per_endpoint=1,
                api_batch_size=2,
                api_max_batch_chars=10_000,
                api_queue_capacity=2,
                api_model="judge",
                api_tokenizer_model="judge",
                api_timeout=1.0,
                api_max_retries=1,
                api_endpoint_failure_threshold=1,
                api_endpoint_cooldown_seconds=0.0,
                api_retry_base_delay=0.0,
                judge_model="judge",
                judge_max_tokens=64,
            )
            FakeJudge.calls = 0
            with (
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.load_manifest",
                    return_value=items,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._request_hash_for_item",
                    side_effect=lambda _args, item: item["request_hash"],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._load_api_tokenizer",
                    return_value=object(),
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._render_api_prompt",
                    side_effect=render,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._judge_retry_token_limits",
                    return_value=[64],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.PersistentJudge",
                    FakeJudge,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.concurrent.futures.wait",
                    side_effect=observe_wait,
                ),
            ):
                run_api_pool(args)

        self.assertEqual(render_count, len(items))
        self.assertEqual(FakeJudge.calls, 4)
        self.assertTrue(wait_observations)
        self.assertEqual(wait_observations[0], (2, 4))
        self.assertTrue(all(in_flight <= 2 for in_flight, _ in wait_observations))

    def test_api_pool_cleans_up_and_propagates_lazy_render_failure(self):
        items = []
        for index in range(3):
            item = _judge_extraction_item("option")
            item.update(
                {
                    "job_id": f"synthetic__render_failure__{index}",
                    "index": str(index),
                    "ordinal": index,
                    "prompt": f"prompt {index}",
                    "request_hash": f"{index + 1:064x}",
                }
            )
            items.append(item)

        def render(_tokenizer, prompt):
            if prompt == "prompt 1":
                raise RuntimeError("synthetic render failure")
            return f"rendered:{prompt}"

        class FakeJudge:
            calls = 0
            instance = None

            def __init__(self, _args):
                self.cleanup_calls = 0
                type(self).instance = self

            def _get_endpoint_health(self):
                return object()

            def _call_api_completion_batch(self, _health, _start, prompts, **_kwargs):
                type(self).calls += 1
                return [
                    {
                        "judge_output": '{"answer":"B"}',
                        "judge_finish_reason": "stop",
                        "judge_output_token_count": 4,
                        "judge_api_endpoint": "http://judge",
                    }
                    for _ in prompts
                ]

            def cleanup(self):
                self.cleanup_calls += 1

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                output_root=root / "out",
                queue_name="render-failure-api",
                queue_root=root / "queue",
                worker_id="test-worker",
                api_bases=["http://judge"],
                api_parallelism=1,
                api_batches_per_endpoint=1,
                api_batch_size=1,
                api_max_batch_chars=10_000,
                api_queue_capacity=2,
                api_model="judge",
                api_tokenizer_model="judge",
                api_timeout=1.0,
                api_max_retries=1,
                api_endpoint_failure_threshold=1,
                api_endpoint_cooldown_seconds=0.0,
                api_retry_base_delay=0.0,
                judge_model="judge",
                judge_max_tokens=64,
            )
            FakeJudge.calls = 0
            with (
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.load_manifest",
                    return_value=items,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._request_hash_for_item",
                    side_effect=lambda _args, item: item["request_hash"],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._load_api_tokenizer",
                    return_value=object(),
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._render_api_prompt",
                    side_effect=render,
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue._judge_retry_token_limits",
                    return_value=[64],
                ),
                mock.patch(
                    "run_llm_extracted_benchmark_score_queue.PersistentJudge",
                    FakeJudge,
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "synthetic render failure"):
                    run_api_pool(args)

            self.assertEqual(FakeJudge.calls, 1)
            self.assertEqual(FakeJudge.instance.cleanup_calls, 1)
            self.assertTrue(_done_path(args, items[0]["job_id"]).exists())
            self.assertFalse(_done_path(args, items[1]["job_id"]).exists())
            self.assertFalse(_done_path(args, items[2]["job_id"]).exists())

    def test_invalid_single_choice_extractions_become_abstentions(self):
        self.assertEqual(_normalize_option("E", "ABCD"), "Z")
        self.assertEqual(_normalize_option("HD", "ABCDEFGHIJ"), "Z")
        self.assertEqual(_normalize_option("B", "ABCD"), "B")
        self.assertEqual(_normalize_option("yellow", "ABCD"), "")

    def test_legacy_failed_output_is_recoverable(self):
        job_id = "physics__model__row"
        raw = '```json\n{"score": 0, "answer": "E = \\\\frac{a}{b}"}\n```'
        error = repr(ValueError(f"Malformed binary judge output for {job_id}: {raw!r}"))
        self.assertEqual(_legacy_raw_output_from_error(job_id, error), raw)

    def test_incomplete_judge_cache_entries_are_retried(self):
        self.assertTrue(
            _judge_cache_entry_needs_retry(
                {"judge_output": "partial reasoning", "judge_finish_reason": "length"}
            )
        )
        self.assertTrue(_judge_cache_entry_needs_retry({"judge_output": "", "judge_finish_reason": "stop"}))
        self.assertFalse(_judge_cache_entry_needs_retry({"judge_output": "0", "judge_finish_reason": "stop"}))
        self.assertEqual(_judge_retry_token_limits(16), [128, 256, 512, 1024])
        self.assertEqual(_judge_retry_token_limits(256), [256, 512, 1024])
        self.assertEqual(_judge_retry_token_limits(2048), [2048])

    def test_logicvista_normalizes_numeric_and_letter_option_schemes(self):
        self.assertEqual(_normalize_logicvista_judgement("3", "3"), ("3", True, False))
        self.assertEqual(_normalize_logicvista_judgement("3", "B"), ("C", False, True))
        self.assertEqual(_normalize_logicvista_judgement("2", "B"), ("B", True, True))
        self.assertEqual(_normalize_logicvista_judgement("B", "2"), ("2", True, True))
        self.assertEqual(_normalize_logicvista_judgement("BD", "B, D"), ("BD", True, False))
        self.assertIsNone(_normalize_logicvista_judgement("The answer is B", "B"))

    def test_chartmuseum_parser_matches_pinned_yes_substring_rule(self):
        self.assertEqual(_parse_chartmuseum_judgement_output("**Yes**"), 1)
        self.assertEqual(_parse_chartmuseum_judgement_output("**No**\n\nThe answers differ."), 0)
        self.assertEqual(_parse_chartmuseum_judgement_output("Reasoning\nFinal Answer: Yes"), 1)
        self.assertEqual(_parse_chartmuseum_judgement_output("The answers are not equivalent"), 0)
        self.assertIsNone(_parse_chartmuseum_judgement_output(""))

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

    def test_screenspot_patch_keeps_pinned_named_coordinate_parser(self):
        from vlmeval.dataset.GUI import screenspot

        pinned_parser = screenspot.parse_bbox_aguvis
        _patch_screenspot_point_parser(spec_by_key("screenspot"))

        self.assertIs(screenspot.parse_bbox_aguvis, pinned_parser)
        self.assertEqual(screenspot.parse_bbox_aguvis("pyautogui.click(x=12, y=34)"), [12.0, 34.0])
        self.assertEqual(screenspot.parse_bbox_aguvis("pyautogui.click(12, 34)"), [0.0, 0.0])
        self.assertEqual(screenspot.parse_bbox_aguvis("I cannot find the target"), [0.0, 0.0])

    def test_screenspot_compact_table_restores_image_path_from_source(self):
        spec = spec_by_key("screenspot")
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
            pd.DataFrame(
                {
                    "index": [0, 1],
                    "bbox": ["[0, 0, 10, 10]", "[1, 1, 10, 10]"],
                    "prediction": ["[5, 5]", "[6, 6]"],
                }
            ).to_excel(pred_table, index=False)
            source = SimpleNamespace(
                data=pd.DataFrame(
                    {
                        "index": [0, 1],
                        "image_path": ["first.png", "second.png"],
                    }
                )
            )
            with mock.patch("run_external_benchmark_score_queue.build_vlmeval_dataset", return_value=source):
                _restore_screenspot_prediction_metadata(spec, output_dir)
            restored = pd.read_excel(pred_table)
            self.assertEqual(restored["image_path"].tolist(), ["first.png", "second.png"])

    def test_tablevqabench_route_uses_only_pinned_answer_prefix_cleanup(self):
        rows = [
            {"index": 0, "split": "fintabnetqa", "prediction": "Answer: 100", "answer": "100"},
            {"index": 1, "split": "vtabfact", "prediction": "Answer: True", "answer": "1"},
            {"index": 2, "split": "vwtq", "prediction": "Answer: Apple", "answer": "Apple"},
            {"index": 3, "split": "vwtq_syn", "prediction": "Answer: Banana", "answer": "Banana"},
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
        self.assertEqual(summary["extraction"]["changed_predictions"], 4)

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
