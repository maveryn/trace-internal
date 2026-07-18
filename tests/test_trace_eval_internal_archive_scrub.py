from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.final25_hf_archive_lib import (
    ArchiveDaemon,
    ArchiveValidationError,
    emit_slice_ready,
)
from scripts.reemit_trace_eval_internal_archive import (
    RootMapping,
    reemit_spool,
    verify_safe_value,
    verify_spool,
)


def _record(*, artifact: str) -> dict:
    return {
        "finish_reason": "stop",
        "ground_truth": "1",
        "metadata": {"official_score_artifact": artifact},
        "model_response": "1",
        "prompt": "answer",
        "question": "what?",
        "request_hash": "request-sha",
        "sampling": {"temperature": 0.6},
        "source_index": "0",
        "source_ordinal": 0,
        "source_row": {"index": 0},
        "source_row_hash": "row-sha",
        "usage": {"completion_tokens": 1},
    }


def _emit(root: Path, *, artifact: str) -> Path:
    return emit_slice_ready(
        root,
        stage="generation",
        run_id="trace-eval-scrub-test",
        model="owner/model@0123456789012345678901234567890123456789",
        model_revision="sha256set:" + "a" * 64,
        model_slug="model",
        seed=42,
        benchmark="chartqapro",
        dataset_alias="ChartQAPro_CoT",
        dataset_split="default",
        dataset_revision="dataset-sha",
        records=[_record(artifact=artifact)],
        provenance={
            "campaign_config_hash": "config-sha",
            "contract_version": "contract-v1",
            "trace_git_commit": "trace-sha",
            "vlmevalkit_git_commit": "vlm-sha",
        },
    )


class TraceEvalInternalArchiveScrubTests(unittest.TestCase):
    def test_reemit_preserves_identity_and_rewrites_only_mapped_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            output = base / "output"
            original = _emit(
                source,
                artifact="/dev/shm/trace-runtime/campaign/scoring/results.xlsx",
            )
            original_descriptor = json.loads(original.read_text(encoding="utf-8"))
            original_record = json.loads(
                (source / original_descriptor["payload_path"]).read_text(encoding="utf-8")
            )

            report = reemit_spool(
                source_root=source,
                output_root=output,
                mappings=[RootMapping("/dev/shm/trace-runtime", "runtime")],
            )

            self.assertEqual(report["descriptor_count"], 1)
            self.assertEqual(report["changed_descriptors"], 1)
            self.assertEqual(report["root_replacements"], 1)
            scrubbed_path = next((output / "ready").glob("*.ready.json"))
            scrubbed_descriptor = json.loads(scrubbed_path.read_text(encoding="utf-8"))
            scrubbed_record = json.loads(
                (output / scrubbed_descriptor["payload_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(scrubbed_descriptor["identity"], original_descriptor["identity"])
            self.assertEqual(scrubbed_record["record_id"], original_record["record_id"])
            self.assertEqual(
                scrubbed_record["metadata"]["official_score_artifact"],
                "trace-local-ref://runtime/campaign/scoring/results.xlsx",
            )
            self.assertNotIn("/dev/shm", json.dumps(scrubbed_descriptor))
            self.assertTrue((output / "control" / "scrub-receipt.json").is_file())

            ArchiveDaemon(spool_root=output, api=object()).build_ready()
            verified = verify_spool(root=output, include_staged=True, require_staged=True)
            self.assertEqual(verified["staged_parquet_count"], 1)
            self.assertEqual(verified["staged_manifest_count"], 1)
            self.assertEqual(verified["staged_row_count"], 1)

    def test_reemit_rejects_unmapped_machine_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            _emit(source, artifact="/home/runner/private/results.xlsx")
            with self.assertRaisesRegex(ArchiveValidationError, "unmapped machine-root"):
                reemit_spool(
                    source_root=source,
                    output_root=base / "output",
                    mappings=[RootMapping("/dev/shm/trace-runtime", "runtime")],
                )

    def test_reemit_rejects_credential_without_echoing_it(self):
        secret = "hf_" + "abcdefghijklmnopqrstuvwxyz123456"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            _emit(source, artifact=f"https://example.test/result?token={secret}")
            with self.assertRaises(ArchiveValidationError) as caught:
                reemit_spool(
                    source_root=source,
                    output_root=base / "output",
                    mappings=[RootMapping("/dev/shm/trace-runtime", "runtime")],
                )
            self.assertNotIn(secret, str(caught.exception))

    def test_textual_basic_and_tex_backslashes_are_not_machine_secrets(self):
        value = r"Basic Proportionality is shown by \\frac{a}{b}."
        self.assertGreater(verify_safe_value(value, location="model_response"), 0)


if __name__ == "__main__":
    unittest.main()
