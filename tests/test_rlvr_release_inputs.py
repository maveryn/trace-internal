from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from build_rlvr_public_file_manifest import build_manifest  # noqa: E402
from validate_rlvr_release_inputs import (  # noqa: E402
    validate_file_manifest,
    validate_release_inputs,
)


class RLVRReleaseInputsTest(unittest.TestCase):
    def test_release_inputs_validate(self) -> None:
        report = validate_release_inputs()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["provenance"]["benchmarks"], 24)
        self.assertEqual(report["provenance"]["rows_per_model_seed"], 32_805)
        self.assertEqual(report["results"]["models"], 8)
        self.assertEqual(report["results"]["benchmark_scores"], 576)
        self.assertEqual(
            report["public_file_manifest"]["training_receipts"],
            {"configs": 2, "train_shards": 16, "environment_runs": 2},
        )

    def test_reviewed_file_manifest_is_generated_and_default_deny(self) -> None:
        path = (
            REPO_ROOT
            / "docs"
            / "workflows"
            / "PUBLIC_RELEASE"
            / "rlvr_public_file_manifest.v1.json"
        )
        checked_in = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(checked_in, build_manifest())
        self.assertEqual(checked_in["review_policy"]["default"], "deny")
        serialized = json.dumps(checked_in, sort_keys=True)
        self.assertNotIn("content_sha256_frozen_pending_internal_commit", serialized)
        for row in checked_in["files"]:
            self.assertRegex(row["source_revision"], r"^[0-9a-f]{40}$")
        historical = "rlvr/experiments/final_answer_only_manifest.json"
        self.assertNotIn(historical, {row["source_path"] for row in checked_in["files"]})
        self.assertIn(
            historical,
            {row["path_or_pattern"] for row in checked_in["denylist"]},
        )

    def test_training_map_is_curated_to_two_configs_and_one_cli(self) -> None:
        manifest = build_manifest()
        rows = [
            row
            for row in manifest["files"]
            if row["component"]
            in {"answer_only_training", "answer_only_training_entrypoint"}
        ]
        entrypoints = {
            row["destination_path"]
            for row in rows
            if row["component"] == "answer_only_training_entrypoint"
        }
        self.assertEqual(
            entrypoints,
            {
                "rlvr/configs/trace-qwen2.5-vl-3b.yaml",
                "rlvr/configs/trace-qwen2.5-vl-7b.yaml",
                "rlvr/train.py",
            },
        )
        self.assertEqual(
            sum(
                row["source_path"].startswith("rlvr/easyr1_backend/verl/")
                for row in rows
            ),
            64,
        )
        sources = {row["source_path"] for row in rows}
        for excluded in (
            "rlvr/easyr1_backend/examples/config.yaml",
            "rlvr/easyr1_backend/pyproject.toml",
            "rlvr/easyr1_backend/requirements.txt",
            "rlvr/easyr1_backend/setup.py",
            "rlvr/easyr1_backend/tests/test_trace_rlvr_reward.py",
            "scripts/run_trace_qwen25vl3b_easyr1_all1000_answer_nokl_step500_job.sh",
            "scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh",
            "scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh",
            "scripts/run_trace_qwen25vl7b_easyr1_answer_nokl_tmpfs.sh",
        ):
            self.assertNotIn(excluded, sources)

        adapted = {
            row["source_path"]
            for row in rows
            if row["component"] == "answer_only_training"
            and row["review_status"] == "approved_for_public_adaptation"
        }
        self.assertEqual(
            adapted,
            {
                "rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py",
                "rlvr/easyr1_backend/scripts/model_merger.py",
                "rlvr/easyr1_backend/verl/trainer/config.py",
                "rlvr/easyr1_backend/verl/trainer/data_loader.py",
                "rlvr/easyr1_backend/verl/trainer/metrics.py",
                "rlvr/easyr1_backend/verl/utils/dataset.py",
            },
        )

    def test_canonical_training_receipts_are_sanitized_and_non_resuming(self) -> None:
        configs_path = (
            REPO_ROOT
            / "docs/workflows/PUBLIC_RELEASE/rlvr_training_configs.v1.json"
        )
        environments_path = (
            REPO_ROOT
            / "docs/workflows/PUBLIC_RELEASE/rlvr_training_environments.v1.json"
        )
        configs = json.loads(configs_path.read_text(encoding="utf-8"))
        environments = json.loads(environments_path.read_text(encoding="utf-8"))
        trainer = configs["common_resolved_config"]["trainer"]
        self.assertEqual(trainer["save_limit"], 1)
        self.assertIs(trainer["find_last_checkpoint"], False)
        self.assertIsNone(trainer["load_checkpoint_path"])
        self.assertEqual(
            [row["config_id"] for row in configs["runs"]],
            ["trace-qwen2.5-vl-3b", "trace-qwen2.5-vl-7b"],
        )
        self.assertEqual(
            environments["common_reproduction_pins"]["torch"],
            "2.8.0+cu128",
        )
        serialized = json.dumps([configs, environments], sort_keys=True).lower()
        for marker in ("/home/", "/dev/shm", "shadeform", "10.0.", "gpu-"):
            self.assertNotIn(marker, serialized)

    def test_manifest_rejects_resume_and_unreviewed_training_sources(self) -> None:
        manifest = build_manifest()
        manifest["release_inputs"]["training_contract"]["scale_specific"]["7B"][
            "find_last_checkpoint"
        ] = True
        with self.assertRaisesRegex(ValueError, "7B canonical run must not discover"):
            validate_file_manifest(manifest)

        manifest = build_manifest()
        training_row = next(
            row
            for row in manifest["files"]
            if row["source_path"]
            == "rlvr/easyr1_backend/verl/trainer/data_loader.py"
        )
        training_row["review_status"] = "approved_exact_copy"
        training_row["adaptations"] = []
        with self.assertRaisesRegex(ValueError, "unexpected exact/adapted training boundary"):
            validate_file_manifest(manifest)

    def test_source_and_evaluator_row_counts_are_not_conflated(self) -> None:
        path = REPO_ROOT / "evaluation" / "trace_eval" / "benchmark_provenance.v1.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))
        rows = {row["benchmark_id"]: row for row in provenance["benchmarks"]}
        self.assertEqual(rows["countbenchqa"]["source"]["source_row_count"], 491)
        self.assertEqual(rows["countbenchqa"]["row_count"], 487)
        self.assertEqual(rows["logicvista"]["source"]["source_row_count"], 448)
        self.assertEqual(rows["logicvista"]["row_count"], 447)

    def test_release_facing_sources_have_no_machine_paths(self) -> None:
        paths = (
            "docs/workflows/PUBLIC_RELEASE/README.md",
            "docs/workflows/PUBLIC_RELEASE/RELEASE_COMPLETION_CHECKLIST.md",
            "docs/workflows/PUBLIC_RELEASE/RLVR_RELEASE_INPUT_FREEZE.md",
            "docs/workflows/PUBLIC_RELEASE/rlvr_public_file_manifest.v1.json",
            "docs/workflows/PUBLIC_RELEASE/rlvr_training_configs.v1.json",
            "docs/workflows/PUBLIC_RELEASE/rlvr_training_environments.v1.json",
            "evaluation/trace_eval/README.md",
            "evaluation/trace_eval/benchmark_provenance.v1.json",
            "results/canonical/trace_eval_v1/release/README.md",
            "results/canonical/trace_eval_v1/release/results.json",
            "scripts/build_rlvr_public_file_manifest.py",
            "scripts/build_trace_eval_release_results.py",
        )
        markers = ("/home/", "/Users/", "/dev/shm", "/workspace/", "C:\\Users\\")
        for relative_path in paths:
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for marker in markers:
                self.assertNotIn(marker, text, f"{relative_path} contains {marker!r}")


if __name__ == "__main__":
    unittest.main()
