from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pandas as pd


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import BenchmarkSpec  # noqa: E402
from run_external_benchmark_score_queue import (  # noqa: E402
    _archive_existing_score_for_spec,
    _charxiv_primary_score,
    _math_like_judge_cache_policy,
    _load_logicvista_official_retry_outputs,
    _parse_chartmuseum_judgement_output,
    _parse_mathverse_score_output,
    _parse_physics_equivalence_output,
    _physics_ground_truths,
    _preferred_direct_score,
    _run_chartmuseum_local_judge,
    _run_evochart_local_score,
    _run_logicvista_judge_with_official_retries,
    _run_physics_subset_score,
    _run_tablevqabench_local_score,
    _screenspot_point_in_box_score,
    run_worker,
)
from screenspot_json_contract import (  # noqa: E402
    SCREENSPOT_JSON_UNRESOLVED,
    adapt_screenspot_prediction_frame,
    parse_screenspot_json_point,
)


class ExternalBenchmarkScoreQueueTests(unittest.TestCase):
    def test_logicvista_judge_uses_official_temperature_retries(self):
        invalid = {"index": "2", "judge_output": "D\u2297"}
        valid = {"index": "2", "judge_output": "AD"}
        judge = mock.Mock()
        judge.run_cached.side_effect = [
            {"2": invalid},
            {"2": invalid},
            {"2": invalid},
            {"2": invalid},
            {"2": valid},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_logicvista_judge_with_official_retries(
                judge=judge,
                call_args=SimpleNamespace(
                    output_dir=Path(tmp), no_resume=False, dataset="LogicVista"
                ),
                prompts=[("2", "prompt")],
                cache_name="logicvista_qwen3_32b_extract.jsonl",
                max_tokens=16,
                top_p=1.0,
                contract_version="logicvista-v1",
            )

        self.assertEqual(result["2"]["judge_output"], "AD")
        self.assertEqual(
            [call.kwargs["temperature"] for call in judge.run_cached.call_args_list],
            [0.0, 0.5, 1.0, 1.5, 2.0],
        )

    def test_logicvista_retry_selection_keeps_cache_identities_separate(self):
        primary = {
            "2": {"index": "2", "judge_output": "D\u2297", "request_hash": "primary"}
        }
        retry_one = {
            "2": {"index": "2", "judge_output": "", "request_hash": "retry-1"}
        }
        retry_two = {
            "2": {"index": "2", "judge_output": "AD", "request_hash": "retry-2"}
        }
        runner = mock.Mock()
        runner.load_jsonl_by_index.side_effect = [primary, retry_one, retry_two]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            for name in (
                "logicvista_qwen3_32b_extract.jsonl",
                "logicvista_qwen3_32b_extract_retry_1.jsonl",
                "logicvista_qwen3_32b_extract_retry_2.jsonl",
            ):
                (output_dir / name).touch()

            selected = _load_logicvista_official_retry_outputs(output_dir, runner)

        self.assertEqual(selected["2"]["judge_output"], "AD")
        self.assertEqual(selected["2"]["request_hash"], "retry-2")
        self.assertEqual(runner.load_jsonl_by_index.call_count, 3)

    def test_logicvista_judge_fails_after_official_retries(self):
        invalid = {"index": "2", "judge_output": "D\u2297"}
        judge = mock.Mock()
        judge.run_cached.return_value = {"2": invalid}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "five official temperature attempts"):
                _run_logicvista_judge_with_official_retries(
                    judge=judge,
                    call_args=SimpleNamespace(
                        output_dir=Path(tmp), no_resume=False, dataset="LogicVista"
                    ),
                    prompts=[("2", "prompt")],
                    cache_name="logicvista_qwen3_32b_extract.jsonl",
                    max_tokens=16,
                    top_p=1.0,
                    contract_version="logicvista-v1",
                )

        self.assertEqual(judge.run_cached.call_count, 5)

    def test_archive_only_finalizer_updates_run_and_benchmark_receipts(self):
        spec = BenchmarkSpec("logicvista", "LogicVista", "LogicVista", "run")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                run_root=root / "runs",
                benchmark_root=root / "benchmark",
            )
            output_dir = args.run_root / "logicvista" / "test-model" / "run"
            output_dir.mkdir(parents=True)
            stale = root / "missing.ready.json"
            (output_dir / "scores.json").write_text(
                json.dumps(
                    {
                        "score": 50.0,
                        "rows": 1,
                        "artifacts": {"prediction_table": "predictions.xlsx"},
                        "archive_descriptors": [str(stale), str(stale)],
                    }
                )
            )
            descriptors = [root / "extraction.ready.json", root / "score.ready.json"]
            for path in descriptors:
                path.write_text("{}")

            with mock.patch(
                "run_external_benchmark_score_queue._archive_direct_score_slices",
                return_value=tuple(descriptors),
            ) as archive:
                summary = _archive_existing_score_for_spec(
                    args, spec, "Qwen/Test", "test-model"
                )

            expected = [str(path) for path in descriptors]
            self.assertEqual(summary["archive_descriptors"], expected)
            archived_summary = archive.call_args.args[-1]
            self.assertNotIn("archive_descriptors", archived_summary)
            benchmark_path = args.benchmark_root / "logicvista" / "test-model" / "run" / "scores.json"
            self.assertEqual(
                json.loads(benchmark_path.read_text())["archive_descriptors"], expected
            )

    def test_archive_only_worker_bypasses_terminal_queue_and_judge(self):
        spec = BenchmarkSpec("logicvista", "LogicVista", "LogicVista", "run")
        args = SimpleNamespace(
            gpu="",
            attention_backend="FLASH_ATTN",
            run_set="trace_final25",
            model="Qwen/Test",
            model_slug="test-model",
            only=["logicvista"],
            exclude=[],
            archive_only=True,
        )
        with (
            mock.patch(
                "run_external_benchmark_score_queue.benchmark_specs_for_run_set",
                return_value=[spec],
            ),
            mock.patch(
                "run_external_benchmark_score_queue.filter_benchmark_specs",
                return_value=[spec],
            ),
            mock.patch(
                "run_external_benchmark_score_queue._archive_existing_score_for_spec"
            ) as finalize,
            mock.patch(
                "run_external_benchmark_score_queue.claim_next_job",
                side_effect=AssertionError("terminal queue must not be claimed"),
            ) as claim,
            mock.patch(
                "run_external_benchmark_score_queue.PersistentJudge",
                side_effect=AssertionError("archive-only must not construct a judge"),
            ) as judge,
        ):
            run_worker(args)

        finalize.assert_called_once_with(args, spec, "Qwen/Test", "test-model")
        claim.assert_not_called()
        judge.assert_not_called()

    def test_charxiv_summary_exposes_percent_scale_primary_score(self):
        self.assertAlmostEqual(_charxiv_primary_score({"Overall": 0.413}), 41.3)

    def test_physics_ground_truths_preserve_typed_answer_candidates(self):
        self.assertEqual(_physics_ground_truths("['(a)']"), ["(a)"])
        self.assertEqual(_physics_ground_truths('["x", "y"]'), ["x", "y"])
        self.assertEqual(_physics_ground_truths(["a;b;c"]), ["a;b;c"])
        for malformed in ("[]", "[not valid]", [], [""], [1]):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    _physics_ground_truths(malformed)

    def test_physics_equivalence_output_is_exact_true_or_false(self):
        self.assertIs(_parse_physics_equivalence_output("True"), True)
        self.assertIs(_parse_physics_equivalence_output("false"), False)
        self.assertIs(_parse_physics_equivalence_output("True.\n\nExplanation"), True)
        self.assertIs(_parse_physics_equivalence_output("**False**: explanation"), False)
        self.assertIs(_parse_physics_equivalence_output("maybe"), False)
        self.assertIs(_parse_physics_equivalence_output("True or False"), True)
        self.assertIsNone(_parse_physics_equivalence_output(""))

    def test_physics_scorer_uses_only_boxed_answers_and_typed_references(self):
        spec = BenchmarkSpec("physics", "Physics", "Physics", "vlmevalkit_reasoning")
        source = SimpleNamespace(
            data=pd.DataFrame(
                [
                    {"index": "r0", "answer": [r"\text{alpha}", r"\text{alternate}"]},
                    {"index": "r1", "answer": [r"\text{unused}"]},
                    {"index": "r2", "answer": [r"\text{beta}"]},
                ]
            )
        )

        class FakeJudge:
            def __init__(self):
                self.calls = []

            def run_cached(self, **kwargs):
                self.calls.append(kwargs)
                result = {}
                for prompt_id, prompt in kwargs["prompts"]:
                    alpha_match = (
                        "Expression 1:\n\\text{alpha}\n\nExpression 2:\n\\text{alpha}" in prompt
                    )
                    beta_match = (
                        "Expression 1:\n\\text{beta}\n\nExpression 2:\n\\text{beta}" in prompt
                    )
                    result[prompt_id] = {"judge_output": "True" if alpha_match or beta_match else "False"}
                return result

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame(
                [
                    {
                        "index": "r0",
                        "category": "synthetic",
                        "question": "full question must not reach the judge",
                        "answer": "serialized answer must not reach the judge",
                        "prediction": (
                            "flawed reasoning must not reach the judge "
                            r"\boxed{\text{alpha}} then \boxed{\text{wrong}}"
                        ),
                    },
                    {
                        "index": "r1",
                        "category": "synthetic",
                        "question": "no box",
                        "answer": "unused",
                        "prediction": "There is no boxed final answer.",
                    },
                    {
                        "index": "r2",
                        "category": "synthetic",
                        "question": "duplicate boxes",
                        "answer": "unused",
                        "prediction": r"\boxed{\text{beta}} and \boxed{\text{beta}}",
                    },
                ]
            ).to_excel(output_dir / "Physics_predictions.xlsx", index=False)
            fake_judge = FakeJudge()
            with mock.patch(
                "run_external_benchmark_score_queue.build_vlmeval_dataset",
                return_value=source,
            ):
                summary = _run_physics_subset_score(
                    SimpleNamespace(no_resume=False),
                    spec,
                    "model",
                    output_dir,
                    fake_judge,
                )

            self.assertAlmostEqual(summary["score"], 50.0)
            judged = pd.read_excel(output_dir / "Physics_official_judged_qwen3_32b.xlsx")
            self.assertEqual(judged["res"].tolist(), [0.5, 0.0, 1.0])
            prompts = fake_judge.calls[0]["prompts"]
            self.assertEqual(len(prompts), 5)
            self.assertEqual(fake_judge.calls[0]["max_tokens"], 4096)
            self.assertTrue(fake_judge.calls[0]["system_prompt"])
            rendered = "\n".join(prompt for _, prompt in prompts)
            self.assertNotIn("flawed reasoning", rendered)
            self.assertNotIn("full question", rendered)
            self.assertNotIn("serialized answer", rendered)
            self.assertNotIn("['", rendered)

    def test_physics_scorer_fails_on_empty_judge_decision(self):
        spec = BenchmarkSpec("physics", "Physics", "Physics", "vlmevalkit_reasoning")
        source = SimpleNamespace(data=pd.DataFrame([{"index": "r0", "answer": [r"\text{a}"]}]))

        class FakeJudge:
            def run_cached(self, **kwargs):
                return {prompt_id: {"judge_output": ""} for prompt_id, _ in kwargs["prompts"]}

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame(
                [{"index": "r0", "answer": "ignored", "prediction": r"\boxed{\text{a}}"}]
            ).to_excel(output_dir / "Physics_predictions.xlsx", index=False)
            with mock.patch(
                "run_external_benchmark_score_queue.build_vlmeval_dataset",
                return_value=source,
            ):
                with self.assertRaisesRegex(RuntimeError, "malformed decision"):
                    _run_physics_subset_score(
                        SimpleNamespace(no_resume=False),
                        spec,
                        "model",
                        output_dir,
                        FakeJudge(),
                    )
            self.assertFalse((output_dir / "scores.json").exists())

    def test_physics_extractor_timeout_uses_equivalence_judge_fallback(self):
        spec = BenchmarkSpec("physics", "Physics", "Physics", "vlmevalkit_reasoning")
        source = SimpleNamespace(data=pd.DataFrame([{"index": "r0", "answer": [r"\text{target}"]}]))
        raw_response = "pathological parser input <answer>target</answer>"

        class FakeJudge:
            def __init__(self):
                self.calls = []

            def run_cached(self, **kwargs):
                self.calls.append(kwargs)
                return {prompt_id: {"judge_output": "True"} for prompt_id, _ in kwargs["prompts"]}

        physics_eval_utils = __import__(
            "vlmeval.dataset.utils.physics_eval_utils",
            fromlist=["extract_final_answer_allform"],
        )
        __import__("vlmeval.dataset.utils.physic", fromlist=["PHYSIC_acc"])
        original_extract = physics_eval_utils.extract_final_answer_allform
        timeout_raised = False

        def timeout_once(response, *args, **kwargs):
            nonlocal timeout_raised
            if response == raw_response and not timeout_raised:
                timeout_raised = True
                raise physics_eval_utils.timeout_decorator.TimeoutError()
            return original_extract(response, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame(
                [{"index": "r0", "answer": "ignored", "prediction": raw_response}]
            ).to_excel(output_dir / "Physics_predictions.xlsx", index=False)
            fake_judge = FakeJudge()
            with mock.patch(
                "run_external_benchmark_score_queue.build_vlmeval_dataset",
                return_value=source,
            ), mock.patch(
                "vlmeval.dataset.utils.physics_eval_utils.extract_final_answer_allform",
                side_effect=timeout_once,
            ):
                summary = _run_physics_subset_score(
                    SimpleNamespace(no_resume=False),
                    spec,
                    "model",
                    output_dir,
                    fake_judge,
                )

            self.assertAlmostEqual(summary["score"], 100.0)
            self.assertEqual(len(fake_judge.calls), 1)
            prompts = fake_judge.calls[0]["prompts"]
            self.assertEqual(len(prompts), 1)
            self.assertIn(raw_response, prompts[0][1])
            judged = pd.read_excel(output_dir / "Physics_official_judged_qwen3_32b.xlsx")
            self.assertEqual(judged.loc[0, "physics_boxed_predictions"], "[]")
            self.assertEqual(judged.loc[0, "physics_extraction_status"], "parser_timeout_judge_fallback")
            self.assertEqual(
                judged.loc[0, "physics_prediction_sha256"],
                "2d6894f92d96526e08f07353c4180dcdaf3b51936e0ffc01c7d80f375b49ddad",
            )
            self.assertEqual(judged.loc[0, "res"], 1.0)

    def test_screenspot_row_score_matches_official_inclusive_pixel_box(self):
        self.assertEqual(
            _screenspot_point_in_box_score(
                bbox="[10, 20, 11, 11]",
                prediction="pyautogui.click(x=20, y=30)",
                image_size=(100, 100),
            ),
            1.0,
        )
        self.assertEqual(
            _screenspot_point_in_box_score(
                bbox="[10, 20, 11, 11]",
                prediction="pyautogui.click(x=21, y=30)",
                image_size=(100, 100),
            ),
            0.0,
        )

    def test_screenspot_parser_does_not_accept_nonofficial_coordinate_wrappers(self):
        self.assertEqual(
            _screenspot_point_in_box_score(
                bbox=[10, 20, 11, 11],
                prediction="<answer>(0.2, 0.3)</answer>",
                image_size=(100, 100),
            ),
            0.0,
        )

    def test_screenspot_unparsed_response_is_an_official_model_error(self):
        self.assertEqual(
            _screenspot_point_in_box_score(
                bbox=[10, 20, 11, 11],
                prediction="Click the button near the top left.",
                image_size=(100, 100),
            ),
            0.0,
        )

    def test_screenspot_json_adapter_accepts_one_point_and_identical_duplicates(self):
        responses = (
            '```json\n[{"point_2d": [12, 34]}]\n```',
            '<answer>[{"point_2d": [12, 34]}]</answer>',
            '[{"point_2d": [12, 34]}]\n[{"point_2d": [12, 34]}]',
            '{"analysis": "unrelated"}\n[{"point_2d": [12, 34]}]',
        )
        for response in responses:
            with self.subTest(response=response):
                parsed = parse_screenspot_json_point(response)
                self.assertEqual(parsed.status, "resolved")
                self.assertEqual(parsed.value, (12.0, 34.0))

    def test_screenspot_json_adapter_rejects_conflicts_and_non_schema_coordinates(self):
        raw = [
            '[{"point_2d": [12, 34]}]\n[{"point_2d": [56, 78]}]',
            'pyautogui.click(x=12, y=34)',
            "[12, 34]",
            '{"point_2d": [12, 34]}',
            '[{"point_2d": [12]}]',
            '[{"point_2d": [12, 34]}, {"metadata": "extra"}]',
        ]
        adapted, receipt = adapt_screenspot_prediction_frame(pd.DataFrame({"prediction": raw}))

        self.assertEqual(adapted["prediction"].tolist(), [SCREENSPOT_JSON_UNRESOLVED] * len(raw))
        self.assertEqual(receipt["resolved_rows"], 0)
        self.assertEqual(receipt["status_counts"], {"ambiguous": 1, "invalid": 5})

    def test_chartmuseum_parser_matches_official_yes_substring_rule(self):
        self.assertEqual(_parse_chartmuseum_judgement_output("Yes"), 1)
        self.assertEqual(_parse_chartmuseum_judgement_output("The answer is yes."), 1)
        self.assertEqual(_parse_chartmuseum_judgement_output("No"), 0)
        self.assertEqual(_parse_chartmuseum_judgement_output("equivalent"), 0)
        self.assertIsNone(_parse_chartmuseum_judgement_output(""))

    def test_chartmuseum_uses_pinned_prompt_and_answer_tag_extractor(self):
        spec = BenchmarkSpec("chartmuseum", "ChartMuseum", "ChartMuseum_test", "official")
        source = SimpleNamespace(
            data=pd.DataFrame(
                [{"index": 0, "question": "Official question?", "answer": "42", "category": "number"}]
            )
        )

        class FakeJudge:
            def __init__(self):
                self.call = None

            def run_cached(self, **kwargs):
                self.call = kwargs
                return {"0": {"judge_output": "Yes", "judge_finish_reason": "stop"}}

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame(
                [{"index": 0, "prediction": "reasoning <answer>42</answer>"}]
            ).to_excel(output_dir / "ChartMuseum_test_predictions.xlsx", index=False)
            judge = FakeJudge()
            with mock.patch(
                "run_external_benchmark_score_queue.build_vlmeval_dataset",
                return_value=source,
            ):
                summary = _run_chartmuseum_local_judge(
                    SimpleNamespace(no_resume=False, judge_model="judge"),
                    spec,
                    "model",
                    output_dir,
                    judge,
                )

            from vlmeval.dataset.chartmuseum import COMPARE_ANSWER_PROMPT

            expected = COMPARE_ANSWER_PROMPT.replace("[QUESTION]", "Official question?")
            expected = expected.replace("[ANSWER1]", "42").replace("[ANSWER2]", "42")
            self.assertEqual(judge.call["prompts"], [("0", expected)])
            self.assertEqual(summary["score"], 100.0)

    def test_mathverse_score_contract_accepts_only_atomic_supported_forms(self):
        validator, _ = _math_like_judge_cache_policy(
            "mathverse", "mathverse_qwen3_32b_score.jsonl"
        )
        accepted = {
            "0": 0,
            " 1 ": 1,
            "Judgement: 0": 0,
            "Judgement: 1": 1,
            "**Judgement: 0**": 0,
            " **Judgement: 1** ": 1,
            "Judgement: 1\n\n**Explanation**: the answers are equivalent": 1,
            "Judgement: **1**\nReasoning\n**Judgement: 1**": 1,
            "**Judgement: 0**\nReasoning\nJudgement: **0**": 0,
            "**Judgement**: **1**\nExplanation": 1,
            "The answers match.\nJudgement: 1": 1,
        }
        for output, expected in accepted.items():
            with self.subTest(output=output):
                self.assertEqual(_parse_mathverse_score_output(output), expected)
                self.assertTrue(validator(output))
        for malformed in (
            "1.",
            "Judgement: 1\nExplanation\n**Judgement: 0**",
            "**Judgement: 0**\nExplanation\nJudgement: **1**",
            "Final Judgement: 1",
            "Judgement: 1**",
            "True",
            "0 or 1",
            "",
        ):
            with self.subTest(malformed=malformed):
                self.assertIsNone(_parse_mathverse_score_output(malformed))
                self.assertFalse(validator(malformed))

    def test_tablevqabench_unwraps_one_answer_block_before_official_prefix(self):
        spec = BenchmarkSpec("tablevqabench", "TableVQABench", "TableVQABench", "official")
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pd.DataFrame(
                [
                    {"index": "f", "split": "fintabnetqa", "answer": "5", "prediction": "Answer: 5"},
                    {"index": "t", "split": "vtabfact", "answer": "1", "prediction": "Answer: True"},
                    {"index": "w", "split": "vwtq", "answer": "apple", "prediction": "Answer: apple"},
                    {"index": "s", "split": "vwtq_syn", "answer": "banana", "prediction": "<answer>banana</answer>"},
                ]
            ).to_excel(output_dir / "TableVQABench_predictions.xlsx", index=False)
            summary = _run_tablevqabench_local_score(spec, "model", output_dir)

            judged = pd.read_excel(summary["artifacts"]["judged_table"])
            predictions = dict(zip(judged["index"], judged["prediction"]))
            self.assertEqual(predictions["f"], "5")
            self.assertEqual(predictions["s"], "banana")
            self.assertEqual(
                [row["split"] for row in summary["scores"]["table"]],
                ["fintabnetqa", "vtabfact", "vwtq", "vwtq_syn"],
            )

    def test_evochart_calls_local_deterministic_dataset_evaluator(self):
        spec = BenchmarkSpec("evochart", "EvoChart", "EvoChart", "official")

        class FakeDataset:
            def __init__(self):
                self.calls = []

            def evaluate(self, path):
                self.calls.append(path)
                return pd.DataFrame([{"split": "Overall", "tot": 2, "hit": 1, "acc": 50.0}])

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            pred_table = output_dir / "EvoChart_predictions.xlsx"
            pd.DataFrame([{"index": 0, "prediction": "x"}]).to_excel(pred_table, index=False)
            fake = FakeDataset()
            with mock.patch(
                "run_external_benchmark_score_queue.build_vlmeval_dataset",
                return_value=fake,
            ):
                summary = _run_evochart_local_score(spec, "model", output_dir)

            self.assertEqual(fake.calls, [str(pred_table)])
            self.assertEqual(summary["score"], 50.0)
            self.assertNotIn("judge_model", summary)

    def test_videommmu_uses_accuracy_row_instead_of_averaging_counts(self):
        spec = BenchmarkSpec("videommmu", "VideoMMMU", "VideoMMMU_8frame", "video")
        summary = {
            "score": 453.7037037037037,
            "scores": {
                "table": [
                    {"Adaptation": 300.0, "Comprehension": 300.0, "Perception": 300.0, "Overall": 900.0},
                    {"Adaptation": 110.0, "Comprehension": 128.0, "Perception": 177.0, "Overall": 415.0},
                    {
                        "Adaptation": 36.6666666667,
                        "Comprehension": 42.6666666667,
                        "Perception": 59.0,
                        "Overall": 46.1111111111,
                    },
                ]
            },
        }

        self.assertAlmostEqual(_preferred_direct_score(spec, summary), 46.1111111111)

    def test_other_benchmarks_keep_generic_primary_score(self):
        spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
        self.assertIsNone(_preferred_direct_score(spec, {"score": 50.0}))

    def test_qbench_video_uses_row_weighted_accuracy_not_raw_counts(self):
        spec = BenchmarkSpec("qbench_video", "QBench-Video", "QBench_Video_8frame", "video")
        summary = {
            "scores": {
                "table": [
                    {"success": 134, "overall": 328, "acc": 40.9},
                    {"success": 161, "overall": 294, "acc": 54.8},
                    {"success": 153, "overall": 270, "acc": 28.35},
                ]
            }
        }
        expected = (40.9 * 328 + 54.8 * 294 + 28.35 * 270) / 892
        self.assertAlmostEqual(_preferred_direct_score(spec, summary), expected)

    def test_video_tt_uses_nested_overall_score(self):
        spec = BenchmarkSpec("video_tt", "Video-TT", "Video_TT_16frame", "video")
        summary = {"scores": {"overall": {"number": 1000, "correct": 384, "score": 38.4}}}
        self.assertEqual(_preferred_direct_score(spec, summary), 38.4)


if __name__ == "__main__":
    unittest.main()
