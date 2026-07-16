from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
TEST_LMU_ROOT = Path("/tmp/trace-mme-failure-guard-tests-lmudata")
TEST_LMU_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["LMUData"] = str(TEST_LMU_ROOT)
for path in (SCRIPTS_ROOT, VLMEVAL_ROOT, VLMEVAL_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_mme_reasoning_eval as mme  # noqa: E402


class _FakeJudge:
    def __init__(self, responder, events: list[str], cleanup_error: Exception | None = None):
        self.responder = responder
        self.events = events
        self.cleanup_error = cleanup_error
        self.calls: list[dict] = []

    def run_cached(self, **kwargs):
        self.calls.append(kwargs)
        rows = {}
        for index, _prompt in kwargs["prompts"]:
            output = self.responder(kwargs["cache_name"], str(index))
            rows[str(index)] = {
                "judge_output": output,
                "request_hash": "a" * 64,
                "judge_retry_count": 0,
            }
        return rows

    def cleanup(self):
        self.events.append("cleanup")
        if self.cleanup_error is not None:
            raise self.cleanup_error


class MMEReasoningFailureGuardTests(unittest.TestCase):
    @staticmethod
    def _args(root: Path) -> SimpleNamespace:
        return SimpleNamespace(
            model="Qwen/Test",
            model_slug="test-model",
            seed=42,
            run_root=root / "runs",
            benchmark_root=root / "benchmark",
            extract_max_tokens=128,
            score_max_tokens=16,
            no_resume=False,
            judge_model="Qwen/Judge",
            judge_api_model="judge",
            judge_api_bases=[],
            judge_cache_contract_version="test-persistent-judge-v1",
        )

    @staticmethod
    def _row(**overrides) -> dict:
        row = {
            "index": "0",
            "question": "Choose the answer.",
            "answer": "B",
            "prediction": "The answer is A.",
            "finish_reason": "stop",
            "question_type": "choice",
            "function_id": "test_function",
            "prompt_id": "choice_prompt",
            "capability": "calculation",
            "reasoning_type": "deductive",
        }
        row.update(overrides)
        return row

    def _execute(
        self,
        root: Path,
        data: pd.DataFrame,
        responder,
        eval_functions: dict,
        *,
        cleanup_error: Exception | None = None,
        score_manifest_error: Exception | None = None,
    ) -> tuple[dict | None, Exception | None, list[str], _FakeJudge, list[dict]]:
        args = self._args(root)
        events: list[str] = []
        archived_scores: list[dict] = []
        judge = _FakeJudge(responder, events, cleanup_error)
        real_write_json = mme.write_json

        def tracked_write(path, payload):
            events.append(f"write:{Path(path).name}")
            if Path(path).name == "scores.json" and score_manifest_error is not None:
                raise score_manifest_error
            real_write_json(Path(path), payload)

        def archive_extractions(*_args, **_kwargs):
            events.append("archive:extraction")
            return root / "extract.ready.json"

        def archive_scores(_args, _data, _extraction_rows, score_rows, _summary):
            events.append("archive:score")
            archived_scores.append({key: dict(value) for key, value in score_rows.items()})
            descriptor = root / "score.ready.json"
            descriptor.write_text("{}", encoding="utf-8")
            return descriptor

        patches = (
            mock.patch.object(mme, "_patch_mme_reasoning_dataset"),
            mock.patch.object(mme, "_load_eval_table", return_value=data.copy()),
            mock.patch.object(
                mme,
                "_extract_prompt",
                side_effect=lambda line: (f"extract:{line['index']}", str(line["prompt_id"])),
            ),
            mock.patch.object(mme, "_openeval_prompt", side_effect=lambda line: f"score:{line['index']}"),
            mock.patch.object(mme, "PersistentJudge", return_value=judge),
            mock.patch.object(mme, "_archive_mme_extractions", side_effect=archive_extractions),
            mock.patch.object(mme, "_archive_mme_scores", side_effect=archive_scores),
            mock.patch.object(mme, "write_json", side_effect=tracked_write),
            mock.patch.object(mme, "_extract_json_from_response", return_value=None),
            mock.patch.object(
                mme,
                "_load_mme_scoring_runtime",
                return_value=(mme.MME_API_FAILURE_MESSAGE, eval_functions, mock.Mock()),
            ),
            mock.patch.object(pd.DataFrame, "to_excel"),
            mock.patch.object(pd.DataFrame, "to_csv"),
        )
        result = None
        error = None
        with ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            try:
                result = mme.run_score(args)
            except Exception as exc:  # Returned for assertions below.
                error = exc
        return result, error, events, judge, archived_scores

    @staticmethod
    def _score_dir(root: Path) -> Path:
        return mme.run_dir(mme.MME_REASONING_SPEC, "test-model", root / "benchmark")

    def test_choice_extraction_accepts_official_atomic_identifier_variants(self):
        cases = {
            "A": "A",
            "[A, C]": "A,C",
            "['b', 'd']": "B,D",
            "[CD]": "C,D",
            "BDE": "B,D,E",
            "B.": "B",
            r"C. $30^\circ$": "C",
            r"D. $\frac{3+\sqrt{2}}{2}$": "D",
            "3": "3",
            "44": "44",
        }
        for output, expected in cases.items():
            with self.subTest(output=output):
                self.assertEqual(mme._validate_extraction("choice_prompt", output), (True, expected))

    def test_choice_extraction_types_explicit_model_abstentions(self):
        for output in (
            "None",
            "None of the above",
            "None of the given options can be used to compare the metals.",
        ):
            with self.subTest(output=output):
                self.assertEqual(
                    mme._validate_extraction("choice_prompt", output),
                    (True, mme.MME_NO_CHOICE_SENTINEL),
                )

    def test_choice_extraction_rejects_empty_verbose_or_conflicting_outputs(self):
        for output in (
            "",
            "the answer is A",
            "A or B",
            "A. first, B. second",
            "AA",
            "AH",
            "None whatsoever",
        ):
            with self.subTest(output=output):
                valid, _normalized = mme._validate_extraction("choice_prompt", output)
                self.assertFalse(valid)

    def test_choice_normalization_still_delegates_correctness_to_official_scorer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, _events, _judge, archived = self._execute(
                root,
                pd.DataFrame(
                    [
                        self._row(index="0", answer="B", function_id="choice_function"),
                        self._row(index="1", answer="4", function_id="choice_function"),
                    ]
                ),
                responder=lambda _cache, index: "B. echoed option" if index == "0" else "3",
                eval_functions={
                    "choice_function": lambda response, answer: response == str(answer)
                },
            )

            self.assertIsNone(error)
            self.assertEqual(result["evaluation"]["correct"], 1)
            self.assertEqual(result["evaluation"]["incorrect"], 1)
            self.assertEqual(archived[0]["0"]["evaluation_status"], "correct")
            self.assertEqual(archived[0]["1"]["evaluation_status"], "incorrect")

    def test_generation_wrapper_propagates_final25_media_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = mme.build_parser().parse_args(
                [
                    "generate",
                    "--model",
                    "model",
                    "--model-slug",
                    "slug",
                    "--api-model",
                    "slug",
                    "--api-base",
                    "http://endpoint/v1",
                    "--run-root",
                    str(root),
                    "--media-transport",
                    "file-url",
                    "--allowed-local-media-path",
                    str(root),
                    "--dataset-manifest",
                    str(root / "datasets.json"),
                ]
            )
            with (
                mock.patch.object(mme, "_patch_mme_reasoning_dataset"),
                mock.patch.object(mme, "_install_runtime_spec"),
                mock.patch("run_external_benchmark_generation_api_queue.run") as run,
            ):
                mme.run_generation(args)

            generated = run.call_args.args[0]
            self.assertEqual(generated.media_transport, "file-url")
            self.assertEqual(generated.allowed_local_media_path, root)
            self.assertEqual(generated.dataset_manifest, root / "datasets.json")
            self.assertEqual(generated.dataset_manifest_view, "frozen")
            self.assertEqual(generated.min_image_pixels, 1_003_520)
            self.assertEqual(generated.max_image_pixels, 12_845_056)

    def test_explicit_false_is_incorrect_and_scores_manifest_is_written_last(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, events, judge, archived = self._execute(
                root,
                pd.DataFrame([self._row(function_id="choice_function")]),
                responder=lambda _cache, _index: "A",
                eval_functions={"choice_function": lambda _response, _answer: False},
            )

            self.assertIsNone(error)
            self.assertEqual(result["accuracy"], 0.0)
            self.assertEqual(result["evaluation"]["incorrect"], 1)
            self.assertEqual(result["evaluation"]["evaluator_invalid"], 0)
            self.assertEqual(archived[0]["0"]["evaluation_status"], "incorrect")
            self.assertEqual(
                events,
                ["cleanup", "archive:extraction", "archive:score", "write:scores.json"],
            )
            self.assertEqual(judge.calls[0]["contract_version"], (
                "test-persistent-judge-v1+" + mme.MME_EXTRACTION_JUDGE_CONTRACT_VERSION
            ))
            persisted = json.loads((self._score_dir(root) / "scores.json").read_text())
            self.assertEqual(persisted["evaluation"]["contract_version"], mme.MME_EVALUATION_CONTRACT_VERSION)

    def test_open_judge_zero_is_incorrect_not_evaluator_failure(self):
        def responder(cache_name, _index):
            return "short answer" if "extract" in cache_name else "0"

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, _events, _judge, archived = self._execute(
                root,
                pd.DataFrame(
                    [
                        self._row(
                            answer="standard answer",
                            question_type="open",
                            function_id=None,
                            prompt_id="open_question_prompt",
                        )
                    ]
                ),
                responder=responder,
                eval_functions={},
            )

            self.assertIsNone(error)
            self.assertEqual(result["evaluation"]["incorrect"], 1)
            self.assertEqual(archived[0]["0"]["score"], False)
            self.assertEqual(archived[0]["0"]["evaluation_status"], "incorrect")

    def test_api_failure_sentinel_fails_preflight_without_judge_or_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            score_dir = self._score_dir(root)
            score_dir.mkdir(parents=True)
            (score_dir / "scores.json").write_text('{"stale":true}', encoding="utf-8")
            (score_dir / "scores_raw.json").write_text('{"stale":true}', encoding="utf-8")
            result, error, events, judge, archived = self._execute(
                root,
                pd.DataFrame(
                    [
                        self._row(
                            prediction=mme.MME_API_FAILURE_MESSAGE + " timeout",
                            finish_reason="error",
                        )
                    ]
                ),
                responder=lambda _cache, _index: "A",
                eval_functions={"test_function": lambda _response, _answer: False},
            )

            self.assertIsNone(result)
            self.assertIsInstance(error, mme.MMEEvaluationFailure)
            self.assertEqual(judge.calls, [])
            self.assertEqual(archived, [])
            self.assertNotIn("cleanup", events)
            self.assertFalse((score_dir / "scores.json").exists())
            self.assertFalse((score_dir / "scores_raw.json").exists())
            failure = json.loads((score_dir / mme.MME_FAILURE_FILENAME).read_text())
            self.assertEqual(failure["stage"], "prediction_preflight")
            self.assertEqual(failure["failures"][0]["kind"], "generation_failure")

    def test_malformed_extraction_retries_then_fails_without_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, events, judge, archived = self._execute(
                root,
                pd.DataFrame(
                    [
                        self._row(
                            question_type="structured",
                            prompt_id="id_answer_pair_prompt",
                        )
                    ]
                ),
                responder=lambda _cache, _index: "not valid json",
                eval_functions={"test_function": lambda _response, _answer: False},
            )

            self.assertIsNone(result)
            self.assertIsInstance(error, mme.MMEEvaluationFailure)
            self.assertEqual(len(judge.calls), 5)
            self.assertEqual(
                [call["temperature"] for call in judge.calls],
                list(mme.MME_RETRY_TEMPERATURES),
            )
            self.assertEqual(archived, [])
            self.assertIn("cleanup", events)
            score_dir = self._score_dir(root)
            self.assertFalse((score_dir / "scores.json").exists())
            failure = json.loads((score_dir / mme.MME_FAILURE_FILENAME).read_text())
            self.assertEqual(failure["stage"], "answer_extraction")
            self.assertEqual(failure["failures"][0]["kind"], "malformed_extraction")

    def test_judge_infrastructure_exception_is_recorded_and_cleanup_runs(self):
        def responder(_cache, _index):
            raise RuntimeError("endpoint unavailable")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, events, _judge, archived = self._execute(
                root,
                pd.DataFrame([self._row()]),
                responder=responder,
                eval_functions={"test_function": lambda _response, _answer: False},
            )

            self.assertIsNone(result)
            self.assertIsInstance(error, mme.MMEEvaluationFailure)
            self.assertEqual(archived, [])
            self.assertIn("cleanup", events)
            failure = json.loads(
                (self._score_dir(root) / mme.MME_FAILURE_FILENAME).read_text()
            )
            self.assertEqual(failure["stage"], "answer_extraction")
            self.assertEqual(failure["failures"][0]["kind"], "evaluator_exception")
            self.assertEqual(failure["failures"][0]["exception_type"], "RuntimeError")

    def test_official_exception_and_nonboolean_result_are_evaluator_failures(self):
        def raises(_response, _answer):
            raise ValueError("official parser failed")

        cases = (
            (raises, "official_evaluator_exception"),
            (lambda _response, _answer: 0, "non_boolean_evaluator_result"),
        )
        for evaluator, expected_kind in cases:
            with self.subTest(expected_kind=expected_kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                result, error, events, _judge, archived = self._execute(
                    root,
                    pd.DataFrame(
                        [
                            self._row(
                                answer="{}",
                                question_type="structured",
                                prompt_id="id_answer_pair_prompt",
                            )
                        ]
                    ),
                    responder=lambda _cache, _index: '{"answer": "x"}',
                    eval_functions={"test_function": evaluator},
                )

                self.assertIsNone(result)
                self.assertIsInstance(error, mme.MMEEvaluationFailure)
                self.assertEqual(archived, [])
                self.assertIn("cleanup", events)
                score_dir = self._score_dir(root)
                self.assertFalse((score_dir / "scores.json").exists())
                failure = json.loads((score_dir / mme.MME_FAILURE_FILENAME).read_text())
                self.assertEqual(failure["stage"], "deterministic_scoring")
                self.assertEqual(failure["failures"][0]["kind"], expected_kind)

    def test_cleanup_failure_happens_before_score_artifacts_or_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, events, _judge, archived = self._execute(
                root,
                pd.DataFrame([self._row(function_id="choice_function")]),
                responder=lambda _cache, _index: "A",
                eval_functions={"choice_function": lambda _response, _answer: False},
                cleanup_error=RuntimeError("cleanup failed"),
            )

            self.assertIsNone(result)
            self.assertIsInstance(error, mme.MMEEvaluationFailure)
            self.assertEqual(events, ["cleanup", "write:mme_reasoning_failures.json"])
            self.assertEqual(archived, [])
            score_dir = self._score_dir(root)
            self.assertFalse((score_dir / "scores.json").exists())
            failure = json.loads((score_dir / mme.MME_FAILURE_FILENAME).read_text())
            self.assertEqual(failure["stage"], "judge_cleanup")

    def test_score_manifest_failure_withdraws_score_archive_and_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, events, _judge, _archived = self._execute(
                root,
                pd.DataFrame([self._row(function_id="choice_function")]),
                responder=lambda _cache, _index: "A",
                eval_functions={"choice_function": lambda _response, _answer: False},
                score_manifest_error=OSError("manifest write failed"),
            )

            self.assertIsNone(result)
            self.assertIsInstance(error, mme.MMEEvaluationFailure)
            self.assertEqual(
                events,
                [
                    "cleanup",
                    "archive:extraction",
                    "archive:score",
                    "write:scores.json",
                    "write:mme_reasoning_failures.json",
                ],
            )
            self.assertFalse((root / "score.ready.json").exists())
            score_dir = self._score_dir(root)
            self.assertFalse((score_dir / "scores.json").exists())
            failure = json.loads((score_dir / mme.MME_FAILURE_FILENAME).read_text())
            self.assertEqual(failure["stage"], "score_manifest")

    def test_missing_required_special_info_is_evaluator_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, error, _events, _judge, archived = self._execute(
                root,
                pd.DataFrame(
                    [
                        self._row(
                            answer="{}",
                            question_type="structured",
                            prompt_id="id_answer_pair_prompt",
                            function_id="calculate_answer_function_hashi",
                            special_info=None,
                        )
                    ]
                ),
                responder=lambda _cache, _index: '{}',
                eval_functions={
                    "calculate_answer_function_hashi": lambda _response, _answer, _special=None: False
                },
            )

            self.assertIsNone(result)
            self.assertIsInstance(error, mme.MMEEvaluationFailure)
            self.assertEqual(archived, [])
            score_dir = self._score_dir(root)
            failure = json.loads((score_dir / mme.MME_FAILURE_FILENAME).read_text())
            self.assertEqual(failure["stage"], "deterministic_scoring")
            self.assertEqual(failure["failures"][0]["kind"], "official_evaluator_exception")
            self.assertIn("requires special_info", failure["failures"][0]["message"])


if __name__ == "__main__":
    unittest.main()
