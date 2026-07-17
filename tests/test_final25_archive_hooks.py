from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.final25_archive_hooks import (
    ArchiveValidationError,
    emit_extraction_slice,
    emit_generation_slice,
    emit_records,
    emit_score_slice,
    resolve_model_revision,
    resolve_model_source,
    sanitize_benchmark_source_row,
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _env(root: Path) -> dict[str, str]:
    return {
        "TRACE_FINAL25_HF_SPOOL_ROOT": str(root),
        "TRACE_FINAL25_RUN_ID": "trace-final25-synthetic",
        "TRACE_FINAL25_TRACE_GIT_COMMIT": "trace-commit",
        "TRACE_FINAL25_VLMEVALKIT_GIT_COMMIT": "vlmeval-commit",
        "TRACE_FINAL25_CAMPAIGN_CONFIG_HASH": "campaign-hash",
        "TRACE_FINAL25_WANDB_RUN_ID": "wandb-run",
    }


def _common() -> dict:
    return {
        "source_index": "item-7",
        "source_ordinal": 2,
        "source_row_hash": _hash("source-row"),
        "request_hash": _hash("request"),
        "question": "Which choice is supported?",
        "ground_truth": "B",
        "options": {"A": "first", "B": "second"},
        "metadata": {"image_hash": "pixels-sha", "image_count": 1},
    }


def _identity() -> dict:
    return {
        "model": "Qwen/Test-7B",
        "model_revision": "checkpoint-500",
        "seed": 42,
        "benchmark": "chartqapro",
        "dataset_alias": "ChartQAPro_CoT",
        "dataset_split": "test",
        "dataset_revision": "dataset-commit",
        "contract_version": "final25-contract-v1",
    }


class Final25ArchiveHookTests(unittest.TestCase):
    def test_model_source_and_revision_resolve_per_slug(self):
        env = {
            "TRACE_FINAL25_MODEL_SOURCES_JSON": '{"model-a":"org/model-a"}',
            "TRACE_FINAL25_MODEL_REVISIONS_JSON": '{"model-a":"commit-a"}',
        }
        self.assertEqual(resolve_model_source("model-a", "/tmp/model", env), "org/model-a")
        self.assertEqual(resolve_model_revision("model-a", "/tmp/model", env), "commit-a")
        self.assertEqual(resolve_model_source("model-b", "fallback", env), "fallback")

    def test_disabled_hook_is_noop_and_does_not_consume_records(self):
        def records():
            raise AssertionError("disabled archive hook consumed records")
            yield {}

        with patch("scripts.final25_archive_hooks._emit_slice_ready") as emit:
            result = emit_generation_slice(records=records(), env={}, **_identity())

        self.assertIsNone(result)
        emit.assert_not_called()

    def test_enabled_hook_requires_complete_run_provenance(self):
        with self.assertRaisesRegex(ArchiveValidationError, "TRACE_FINAL25_RUN_ID"):
            emit_score_slice(
                records=[],
                env={"TRACE_FINAL25_HF_SPOOL_ROOT": "/tmp/archive"},
                **_identity(),
            )

    def test_source_row_scrubber_drops_media_and_credentials(self):
        safe = sanitize_benchmark_source_row(
            {
                "index": 7,
                "image": "/datasets/chart/7.png",
                "attachment": "data:image/png;base64,AAAA",
                "image_hash": "pixels-sha",
                "image_width": 640,
                "nested": {
                    "hf_token": "must-not-survive",
                    "label": "bar",
                    "frames": ["/datasets/video/frame.png", "caption"],
                },
                "blob": b"raw pixels",
            }
        )

        self.assertEqual(safe["index"], 7)
        self.assertEqual(safe["image_hash"], "pixels-sha")
        self.assertEqual(safe["image_width"], 640)
        self.assertNotIn("image", safe)
        self.assertNotIn("attachment", safe)
        self.assertNotIn("blob", safe)
        self.assertEqual(safe["nested"], {"label": "bar", "frames": ["caption"]})
        self.assertNotIn("must-not-survive", json.dumps(safe))

    def test_generation_emits_sanitized_fixed_schema_to_local_spool(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = _common() | {
                "source_row": {
                    "index": "item-7",
                    "question": "Which choice is supported?",
                    "image": "/datasets/chart/7.png",
                    "image_hash": "pixels-sha",
                    "api_key": "must-not-survive",
                },
                "prompt": "<image> Which choice is supported?",
                "model_response": "<answer>B</answer>",
                "sampling": {"temperature": 0.6, "seed": 42},
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            }
            descriptor_path = emit_generation_slice(
                records=[record], env=_env(root), aggregate={"rows": 1}, **_identity()
            )

            self.assertIsNotNone(descriptor_path)
            descriptor = json.loads(descriptor_path.read_text())
            payload_path = root / descriptor["payload_path"]
            archived = json.loads(payload_path.read_text())
            self.assertEqual(archived["source_index"], record["source_index"])
            self.assertEqual(archived["source_ordinal"], record["source_ordinal"])
            self.assertEqual(archived["source_row_hash"], record["source_row_hash"])
            self.assertEqual(archived["request_hash"], record["request_hash"])
            self.assertEqual(archived["model_response"], "<answer>B</answer>")
            self.assertEqual(archived["source_row"]["image_hash"], "pixels-sha")
            self.assertNotIn("image", archived["source_row"])
            self.assertNotIn("must-not-survive", payload_path.read_text())
            self.assertEqual(
                descriptor["provenance"],
                {
                    "archive_hook_version": "trace-final25-archive-hooks-v1",
                    "campaign_config_hash": "campaign-hash",
                    "contract_version": "final25-contract-v1",
                    "trace_git_commit": "trace-commit",
                    "vlmevalkit_git_commit": "vlmeval-commit",
                    "wandb_run_id": "wandb-run",
                },
            )

    def test_generation_preserves_media_like_model_response_as_opaque_text(self):
        response = (
            "The screenshot path is /tmp/benchmark/example.png and the literal "
            "answer is data:image/png;base64,not-an-archive-payload."
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = _common() | {
                "source_row": {"index": "item-7"},
                "prompt": "Describe /datasets/chart/example.png.",
                "model_response": response,
                "sampling": {"temperature": 0.6, "seed": 42},
                "finish_reason": "stop",
                "usage": {},
            }

            descriptor_path = emit_generation_slice(
                records=[record], env=_env(root), **_identity()
            )
            descriptor = json.loads(descriptor_path.read_text())
            archived = json.loads((root / descriptor["payload_path"]).read_text())

            self.assertEqual(archived["model_response"], response)
            self.assertEqual(archived["prompt"], record["prompt"])

    def test_extraction_and_score_keep_reanalysis_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            common = _common()
            extraction = common | {
                "request_hash": _hash("extract-request"),
                "model_response": "The answer is B.",
                "judge_prompt": "Extract one option.",
                "judge_response": '{"answer":"B"}',
                "normalized_extraction": {"answer": "B", "method": "judge"},
                "retries": [{"attempt": 1, "reason": "length"}],
            }
            score = common | {
                "request_hash": _hash("score-request"),
                "prediction": "B",
                "score": 1.0,
                "scorer": "official_exact_match",
                "excluded": False,
            }

            extraction_path = emit_extraction_slice(
                records=[extraction], env=_env(root), **_identity()
            )
            score_path = emit_score_slice(
                records=[score],
                env=_env(root),
                aggregate={"accuracy": 1.0},
                **_identity(),
            )

            extraction_descriptor = json.loads(extraction_path.read_text())
            score_descriptor = json.loads(score_path.read_text())
            extraction_row = json.loads(
                (root / extraction_descriptor["payload_path"]).read_text()
            )
            score_row = json.loads((root / score_descriptor["payload_path"]).read_text())
            self.assertEqual(extraction_row["judge_response"], '{"answer":"B"}')
            self.assertEqual(extraction_row["normalized_extraction"]["answer"], "B")
            self.assertEqual(score_row["prediction"], "B")
            self.assertEqual(score_row["score"], 1.0)
            self.assertEqual(score_descriptor["aggregate"], {"accuracy": 1.0})

    def test_extraction_preserves_media_like_text_in_retry_judge_exchange(self):
        media_like_text = "data:image/png;base64,{shaded face}"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extraction = _common() | {
                "request_hash": _hash("extract-retry-request"),
                "model_response": "The answer is C.",
                "judge_prompt": "Extract one option.",
                "judge_response": "C",
                "normalized_extraction": {"answer": "C", "method": "judge"},
                "retries": {
                    "events": [
                        {
                            "prompt": f"Answer: {media_like_text}",
                            "response": f"Literal response: {media_like_text}",
                            "request_hash": _hash("judge-retry"),
                        }
                    ],
                    "total_retries": 0,
                },
            }

            descriptor_path = emit_extraction_slice(
                records=[extraction], env=_env(root), **_identity()
            )
            descriptor = json.loads(descriptor_path.read_text())
            archived = json.loads((root / descriptor["payload_path"]).read_text())

            event = archived["retries"]["events"][0]
            self.assertEqual(event["prompt"], f"Answer: {media_like_text}")
            self.assertEqual(event["response"], f"Literal response: {media_like_text}")

    def test_generic_emitter_accepts_dataframe_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = pd.DataFrame(
                [
                    _common()
                    | {
                        "prediction": "B",
                        "score": 1.0,
                        "scorer": "official_exact_match",
                        "excluded": False,
                    }
                ]
            )
            descriptor_path = emit_records(
                stage="score", records=frame, env=_env(root), **_identity()
            )

            descriptor = json.loads(descriptor_path.read_text())
            archived = json.loads((root / descriptor["payload_path"]).read_text())
            self.assertEqual(archived["source_index"], "item-7")
            self.assertEqual(archived["score"], 1.0)

    def test_provenance_extra_cannot_override_or_include_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            score = _common() | {
                "prediction": "B",
                "score": 1.0,
                "scorer": "exact",
            }
            with self.assertRaisesRegex(ArchiveValidationError, "cannot override"):
                emit_score_slice(
                    records=[score],
                    env=_env(root),
                    provenance_extra={"contract_version": "wrong"},
                    **_identity(),
                )
            with self.assertRaisesRegex(ArchiveValidationError, "credential"):
                emit_score_slice(
                    records=[score],
                    env=_env(root),
                    provenance_extra={"hf_token": "must-not-survive"},
                    **_identity(),
                )


if __name__ == "__main__":
    unittest.main()
