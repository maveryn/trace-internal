from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from PIL import Image


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import spec_by_key  # noqa: E402
from run_external_benchmark_generation_api_queue import (  # noqa: E402
    DatasetHandle,
    _archive_generation_slice,
)
from run_external_benchmark_score_queue import _archive_direct_score_slices  # noqa: E402
from run_external_benchmark_score_multi_model_queue import (  # noqa: E402
    _archive_sentinel_current,
    _repair_stale_archive_sentinels,
)
from run_llm_extracted_benchmark_score_queue import (  # noqa: E402
    EXTRACTION_CONTRACT_VERSION,
    _archive_extracted_group,
)
from run_mme_reasoning_eval import _archive_mme_extractions, _archive_mme_scores  # noqa: E402


def _archive_env(root: Path) -> dict[str, str]:
    return {
        "TRACE_FINAL25_HF_SPOOL_ROOT": str(root),
        "TRACE_FINAL25_RUN_ID": "runner-integration",
        "TRACE_GIT_COMMIT": "trace-sha",
        "TRACE_VLMEVALKIT_GIT_COMMIT": "vlmeval-sha",
        "TRACE_FINAL25_CAMPAIGN_CONFIG_HASH": "campaign-sha",
        "TRACE_FINAL25_DATASET_REVISION": "vlmeval-sha",
    }


def _payloads(root: Path) -> list[dict]:
    return [
        json.loads(line)
        for path in sorted((root / "payloads").glob("*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class Final25RunnerArchiveIntegrationTests(unittest.TestCase):
    def test_direct_score_sentinel_requires_current_archive_descriptors(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            root = Path(temporary)
            ready = root / "spool" / "ready"
            ready.mkdir(parents=True)
            descriptor_paths = []
            for stage in ("extraction", "score"):
                descriptor = {
                    "identity": {
                        "run_id": "runner-integration",
                        "model_slug": "test-model",
                        "seed": 42,
                        "benchmark": "chartmuseum",
                        "stage": stage,
                        "dataset_revision": "vlmeval-sha",
                    },
                    "provenance": {"campaign_config_hash": "campaign-sha"},
                }
                path = ready / f"{stage}.ready.json"
                path.write_text(json.dumps(descriptor), encoding="utf-8")
                descriptor_paths.append(str(path))
            sentinel = root / "sentinel.json"
            sentinel.write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "model_slug": "test-model",
                                "archive_descriptors": descriptor_paths,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            args = SimpleNamespace(model_entries=[("test-model", "Qwen/Test")], seed=42)

            self.assertTrue(_archive_sentinel_current(args, sentinel, "chartmuseum"))
            Path(descriptor_paths[0]).unlink()
            self.assertFalse(_archive_sentinel_current(args, sentinel, "chartmuseum"))

    def test_stale_direct_score_sentinel_resets_done_queue_for_backfill(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            root = Path(temporary)
            sentinel = root / "stale.json"
            sentinel.write_text('{"models": []}\n', encoding="utf-8")
            queue_path = root / "queue.json"
            queue_path.write_text(
                json.dumps({"jobs": {"chartmuseum": {"status": "done", "attempts": 2}}}),
                encoding="utf-8",
            )
            args = SimpleNamespace(model_entries=[("test-model", "Qwen/Test")], seed=42)

            _repair_stale_archive_sentinels(
                args, queue_path, [("chartmuseum", sentinel)]
            )

            state = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertFalse(sentinel.exists())
            self.assertEqual(state["jobs"]["chartmuseum"]["status"], "pending")
            self.assertEqual(state["jobs"]["chartmuseum"]["attempts"], 0)

    def test_generation_and_direct_score_share_source_identity(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            root = Path(temporary)
            spool = root / "spool"
            output = root / "tablevqabench"
            output.mkdir()
            source_hash = "a" * 64
            generation_args = SimpleNamespace(
                model="Qwen/Test",
                model_slug="test-model",
                seed=42,
                temperature=0.6,
                top_p=1.0,
                top_k=-1,
                presence_penalty=0.0,
                repetition_penalty=1.0,
                max_tokens=4096,
            )
            source_row = {
                "index": "7",
                "question": "How many?",
                "answer": "2",
                "image": "/tmp/not-archived.png",
            }
            result = {
                "index": "7",
                "prediction": "<answer>2</answer>",
                "request_hash": "b" * 64,
                "source_row_hash": source_hash,
                "prompt": "How many?",
                "finish_reason": "stop",
                "usage": {"completion_tokens": 4},
            }
            generation_path = _archive_generation_slice(
                generation_args,
                DatasetHandle(spec_by_key("tablevqabench")),
                [source_row],
                {"7": result},
                {"rows": 1},
            )

            judged = output / "TableVQABench_trace_final_answer_scored.xlsx"
            pd.DataFrame(
                [
                    {
                        **source_row,
                        "source_ordinal": 0,
                        "source_row_hash": source_hash,
                        "raw_prediction": "<answer>2</answer>",
                        "prediction": "2",
                        "trace_extraction_method": "answer_tag",
                    }
                ]
            ).drop(columns=["image"]).to_excel(judged, index=False)
            extraction_path, score_path = _archive_direct_score_slices(
                SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                spec_by_key("tablevqabench"),
                "Qwen/Test",
                "test-model",
                output,
                {
                    "rows": 1,
                    "score": 100.0,
                    "harness": "official",
                    "artifacts": {"judged_table": str(judged)},
                },
            )

            self.assertTrue(generation_path and extraction_path and score_path)
            rows = _payloads(spool)
            self.assertEqual({row["record_id"] for row in rows}, {rows[0]["record_id"]})
            self.assertNotIn("not-archived.png", json.dumps(rows))
            score_record = next(row for row in rows if "scorer" in row)
            self.assertIsNone(score_record["score"])
            self.assertEqual(score_record["metadata"]["score_contract"], "aggregate_only")
            self.assertEqual(score_record["metadata"]["aggregate_score"], 100.0)

    def test_direct_archive_preserves_zero_ordinal_when_score_rows_are_reordered(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            root = Path(temporary)
            output = root / "chartmuseum"
            output.mkdir()
            spec = spec_by_key("chartmuseum")
            source_table = output / f"{spec.alias}_predictions.xlsx"
            pd.DataFrame(
                [
                    {
                        "index": "zero",
                        "source_ordinal": 0,
                        "source_row_hash": "a" * 64,
                        "question": "Q0",
                        "answer": "A0",
                        "prediction": "A0",
                    },
                    {
                        "index": "one",
                        "source_ordinal": 1,
                        "source_row_hash": "b" * 64,
                        "question": "Q1",
                        "answer": "A1",
                        "prediction": "A1",
                    },
                ]
            ).to_excel(source_table, index=False)
            judged = output / "judged_predictions.xlsx"
            pd.DataFrame(
                [
                    {
                        "index": "one",
                        "source_ordinal": 1,
                        "source_row_hash": "b" * 64,
                        "question": "Q1",
                        "answer": "A1",
                        "prediction": "A1",
                        "score": 1,
                    },
                    {
                        "index": "zero",
                        "source_ordinal": 0,
                        "source_row_hash": "a" * 64,
                        "question": "Q0",
                        "answer": "A0",
                        "prediction": "A0",
                        "score": 1,
                    },
                ]
            ).to_excel(judged, index=False)

            _archive_direct_score_slices(
                SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                spec,
                "Qwen/Test",
                "test-model",
                output,
                {
                    "rows": 2,
                    "score": 100.0,
                    "harness": "official",
                    "artifacts": {"judged_table": str(judged)},
                },
            )

            archived = _payloads(root / "spool")
            zero_rows = [row for row in archived if row["source_index"] == "zero"]
            self.assertEqual(len(zero_rows), 2)
            self.assertEqual({row["source_ordinal"] for row in zero_rows}, {0})
            self.assertEqual({row["record_id"] for row in zero_rows}, {zero_rows[0]["record_id"]})

    def test_direct_archive_rejects_score_table_row_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            output = Path(temporary) / "chartmuseum"
            output.mkdir()
            judged = output / "judged_predictions.xlsx"
            pd.DataFrame(
                [{"index": "0", "prediction": "A", "answer": "A", "score": 1}]
            ).to_excel(judged, index=False)

            with self.assertRaisesRegex(RuntimeError, "score table has 1 rows.*declares 2"):
                _archive_direct_score_slices(
                    SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                    spec_by_key("chartmuseum"),
                    "Qwen/Test",
                    "test-model",
                    output,
                    {
                        "rows": 2,
                        "score": 100.0,
                        "harness": "official",
                        "artifacts": {"judged_table": str(judged)},
                    },
                )

    def test_direct_archive_rejects_source_table_row_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            output = Path(temporary) / "chartmuseum"
            output.mkdir()
            spec = spec_by_key("chartmuseum")
            source_table = output / f"{spec.alias}_predictions.xlsx"
            pd.DataFrame(
                [
                    {"index": "0", "prediction": "A", "answer": "A"},
                    {"index": "1", "prediction": "B", "answer": "B"},
                ]
            ).to_excel(source_table, index=False)
            judged = output / "judged_predictions.xlsx"
            pd.DataFrame(
                [{"index": "0", "prediction": "A", "answer": "A", "score": 1}]
            ).to_excel(judged, index=False)

            with self.assertRaisesRegex(RuntimeError, "source prediction table.*has 2"):
                _archive_direct_score_slices(
                    SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                    spec,
                    "Qwen/Test",
                    "test-model",
                    output,
                    {
                        "rows": 1,
                        "score": 100.0,
                        "harness": "official",
                        "artifacts": {"judged_table": str(judged)},
                    },
                )

    def test_screenspot_direct_archive_derives_official_per_row_scores(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ,
            {
                **_archive_env(Path(temporary) / "spool"),
                "LMUData": str(Path(temporary) / "LMUData"),
            },
            clear=False,
        ):
            root = Path(temporary)
            output = root / "screenspot"
            output.mkdir()
            image_dir = root / "LMUData" / "images" / "ScreenSpot_Mobile"
            image_dir.mkdir(parents=True)
            Image.new("RGB", (100, 100)).save(image_dir / "screen.png")
            judged = output / "screenspot_judged.xlsx"
            pd.DataFrame(
                [
                    {
                        "index": "0",
                        "question": "Click the control",
                        "bbox": "[10, 20, 11, 11]",
                        "SUB_DATASET": "ScreenSpot_Mobile",
                        "image_path": "screen.png",
                        "prediction": "pyautogui.click(x=20, y=30)",
                    },
                    {
                        "index": "1",
                        "question": "Click the other control",
                        "bbox": "[10, 20, 11, 11]",
                        "SUB_DATASET": "ScreenSpot_Mobile",
                        "image_path": "screen.png",
                        "prediction": "pyautogui.click(x=21, y=30)",
                    },
                ]
            ).to_excel(judged, index=False)

            _archive_direct_score_slices(
                SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                spec_by_key("screenspot"),
                "Qwen/Test",
                "test-model",
                output,
                {
                    "rows": 2,
                    "score": 50.0,
                    "harness": "official",
                    "artifacts": {"judged_table": str(judged)},
                },
            )

            score_rows = [row for row in _payloads(root / "spool") if "scorer" in row]
            self.assertEqual(
                {row["source_index"]: row["score"] for row in score_rows},
                {"0": 1.0, "1": 0.0},
            )
            self.assertEqual({row["metadata"]["score_contract"] for row in score_rows}, {"per_row"})

    def test_screenspot_direct_archive_rejects_aggregate_disagreement(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ,
            {
                **_archive_env(Path(temporary) / "spool"),
                "LMUData": str(Path(temporary) / "LMUData"),
            },
            clear=False,
        ):
            root = Path(temporary)
            output = root / "screenspot"
            output.mkdir()
            image_dir = root / "LMUData" / "images" / "ScreenSpot_Mobile"
            image_dir.mkdir(parents=True)
            Image.new("RGB", (100, 100)).save(image_dir / "screen.png")
            judged = output / "screenspot_judged.xlsx"
            pd.DataFrame(
                [
                    {
                        "index": "0",
                        "bbox": "[10, 20, 11, 11]",
                        "SUB_DATASET": "ScreenSpot_Mobile",
                        "image_path": "screen.png",
                        "prediction": "pyautogui.click(x=20, y=30)",
                    }
                ]
            ).to_excel(judged, index=False)

            with self.assertRaisesRegex(RuntimeError, "do not match the official aggregate"):
                _archive_direct_score_slices(
                    SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                    spec_by_key("screenspot"),
                    "Qwen/Test",
                    "test-model",
                    output,
                    {
                        "rows": 1,
                        "score": 0.0,
                        "harness": "official",
                        "artifacts": {"judged_table": str(judged)},
                    },
                )

    def test_llm_extraction_emits_response_extraction_and_score(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            item = {
                "job_id": "blink__test-model__7",
                "index": "7",
                "ordinal": 0,
                "source_row_hash": "a" * 64,
                "question": "Select one.",
                "answer": "B",
                "options": {"A": "first", "B": "second"},
                "answer_kind": "option",
                "prediction": "The answer is B.",
                "prompt": "Return strict JSON.",
                "request_hash": "b" * 64,
                "response_sha256": hashlib.sha256(b"The answer is B.").hexdigest(),
            }
            scored = {
                "job_id": item["job_id"],
                "index": "7",
                "ordinal": 0,
                "extracted": "B",
                "extracted_raw": "B",
                "judge_output": '{"answer":"B"}',
                "extraction_status": "resolved",
                "extraction_method": "judge_json",
                "extraction_candidates": [
                    {"source": "json[0].answer", "raw": "B", "normalized": "B"}
                ],
                "explicit_abstention": False,
                "validation_contract_version": EXTRACTION_CONTRACT_VERSION,
                "eval_pred": "B",
                "eval_score": 1,
            }
            paths = _archive_extracted_group(
                SimpleNamespace(seed=42, judge_model="Qwen/Judge"),
                benchmark="blink",
                model_slug="test-model",
                model_path="Qwen/Test",
                manifest_items={item["job_id"]: item},
                exclusions=[],
                rows=[scored],
                summary={"run_name": "llm_extracted", "rows": 1, "score": 100.0},
            )
            self.assertTrue(all(path and path.exists() for path in paths))
            archived = _payloads(Path(temporary) / "spool")
            self.assertEqual({row["record_id"] for row in archived}, {archived[0]["record_id"]})
            extraction = next(row for row in archived if "judge_response" in row)
            self.assertEqual(extraction["judge_response"], '{"answer":"B"}')
            normalized = extraction["normalized_extraction"]
            self.assertEqual(normalized["status"], "resolved")
            self.assertEqual(normalized["method"], "judge_json")
            self.assertEqual(normalized["response_hash"], item["response_sha256"])
            self.assertEqual(normalized["contract_version"], EXTRACTION_CONTRACT_VERSION)

    def test_mme_archive_keeps_deterministic_scorer_provenance(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, _archive_env(Path(temporary) / "spool"), clear=False
        ):
            args = SimpleNamespace(model="Qwen/Test", model_slug="test-model", seed=42)
            data = pd.DataFrame(
                [
                    {
                        "index": "7",
                        "source_ordinal": 0,
                        "source_row_hash": "a" * 64,
                        "question": "Select one.",
                        "answer": "B",
                        "prediction": "Answer B",
                        "question_type": "choice",
                        "function_id": "choice_function",
                        "prompt_id": "choice_prompt",
                    }
                ]
            )
            extraction_rows = {
                "7": {
                    "res": "B",
                    "judge_prompt": "extract",
                    "judge_response": "B",
                    "request_hash": "b" * 64,
                    "retry_count": 0,
                }
            }
            score_rows = {"7": {"score": True, "log_score": "Succeed"}}
            paths = (
                _archive_mme_extractions(args, data, extraction_rows),
                _archive_mme_scores(
                    args,
                    data,
                    extraction_rows,
                    score_rows,
                    {"rows": 1, "accuracy": 100.0},
                ),
            )
            self.assertTrue(all(path and path.exists() for path in paths))
            archived = _payloads(Path(temporary) / "spool")
            self.assertIn("choice_function", json.dumps(archived))


if __name__ == "__main__":
    unittest.main()
