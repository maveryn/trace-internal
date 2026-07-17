from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from final25_media_contract import (  # noqa: E402
    GENERATION_CONTRACT_VERSION,
    MEDIA_CONTRACT_VERSION,
    MEDIA_TRANSPORT,
    QWEN_MAX_IMAGE_PIXELS,
    QWEN_MIN_IMAGE_PIXELS,
)
from run_trace_final26_official_score_campaign import (  # noqa: E402
    Campaign,
    Workbook,
    _activate_suite,
    _archive_normalized_extraction,
    _judge_kwargs,
    _official_archive_row_scores,
    _partition_mme_endpoints,
    _prepare_score_root,
    _run_mme_phase,
    _stage_workbooks,
    _validate_generation_inputs,
    _validate_media_generation_contract,
)
import run_trace_final26_official_score_campaign as score_campaign  # noqa: E402


class TraceFinal26ScoreCampaignTests(unittest.TestCase):
    def tearDown(self):
        _activate_suite("all26")

    def test_generation_contract_requires_native_processor_bounds(self):
        generation = {
            "contract_version": GENERATION_CONTRACT_VERSION,
            "media_contract_version": MEDIA_CONTRACT_VERSION,
            "media_transport": MEDIA_TRANSPORT,
            "min_image_pixels": QWEN_MIN_IMAGE_PIXELS,
            "max_image_pixels": QWEN_MAX_IMAGE_PIXELS,
        }

        _validate_media_generation_contract(generation)
        generation["min_image_pixels"] = 1_003_520
        with self.assertRaisesRegex(ValueError, "generation.min_image_pixels"):
            _validate_media_generation_contract(generation)

    def test_resume_restores_mutated_staged_workbook_from_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.xlsx"
            staged = root / "staged.xlsx"
            source.write_bytes(b"contract-verified source")
            staged.write_bytes(b"scorer-enriched staging copy")
            workbook = Workbook(
                benchmark_key="screenspot",
                alias="ScreenSpot",
                run_name="run",
                source=source,
                staged=staged,
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                primary=True,
            )

            _stage_workbooks({"model": [workbook]}, resume=True)

            self.assertEqual(staged.read_bytes(), source.read_bytes())

    def test_final31_route_contract_adds_only_five_official_jobs(self):
        _activate_suite("all31")
        self.assertEqual(len(score_campaign.ALL_SCORE_KEYS), 31)
        self.assertEqual(len(score_campaign.DIRECT_SCORE_KEYS), 10)
        self.assertEqual(
            score_campaign.OFFICIAL_SCORE_KEYS[-5:],
            ("screenspotpro", "screenspot_v2", "embspatial", "realworldqa", "visulogic"),
        )
        self.assertEqual(score_campaign.GENERATION_MAX_TOKENS_BY_KEY["screenspot"], 16384)

    def test_final31_additions_use_deterministic_official_scoring(self):
        args = SimpleNamespace(
            judge_api_model="qwen3-32b-judge",
            eval_nproc=16,
            judge_max_tokens=256,
        )
        for key in (
            "screenspotpro",
            "screenspot_v2",
            "embspatial",
            "realworldqa",
            "visulogic",
        ):
            self.assertEqual(
                _judge_kwargs(args, key),
                {"model": "exact_matching", "nproc": 16},
                key,
            )
        self.assertEqual(_judge_kwargs(args, "mmvp")["model"], "qwen3-32b-judge")

    def test_generation_input_snapshot_must_match_active_manifest_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "MMVP_predictions.xlsx"
            pd.DataFrame([{"index": 0, "prediction": "A"}]).to_excel(source, index=False)
            wrong_snapshot = "a" * 64
            expected_snapshot = "b" * 64
            summary = {
                "rows": 1,
                "expected_rows": 1,
                "model": "Qwen/Test",
                "model_slug": "test-model",
                "generation": {
                    "temperature": 0.6,
                    "top_p": 1.0,
                    "top_k": -1,
                    "presence_penalty": 0.0,
                    "repetition_penalty": 1.0,
                    "max_tokens": 4096,
                    "seed": 42,
                    "api_model": "test-model",
                    "contract_version": GENERATION_CONTRACT_VERSION,
                    "media_contract_version": MEDIA_CONTRACT_VERSION,
                    "media_transport": MEDIA_TRANSPORT,
                    "min_image_pixels": QWEN_MIN_IMAGE_PIXELS,
                    "max_image_pixels": QWEN_MAX_IMAGE_PIXELS,
                    "dataset_snapshot_sha256": wrong_snapshot,
                },
                "finish_reason": {"stop": 1},
                "artifacts": {"eval_file": str(source.resolve())},
            }
            (root / "generation_summary.json").write_text(json.dumps(summary))
            workbook = Workbook(
                benchmark_key="mmvp",
                alias="MMVP",
                run_name="run",
                source=source,
                staged=root / "staged.xlsx",
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                primary=True,
            )
            campaign = Campaign(model="Qwen/Test", slug="test-model", root=root)
            with patch.object(score_campaign, "ALL_SCORE_KEYS", ("mmvp",)):
                with self.assertRaisesRegex(RuntimeError, "active all26 manifest snapshot"):
                    _validate_generation_inputs(
                        [campaign],
                        {"test-model": [workbook]},
                        seed=42,
                        expected_dataset_snapshot=expected_snapshot,
                    )

    def test_shared_score_root_keeps_independent_seed_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = {"seed": 42, "value": "a"}
            second = {"seed": 43, "value": "b"}
            first_hash = _prepare_score_root(root, first, False, shared_seed_root=True)
            second_hash = _prepare_score_root(root, second, False, shared_seed_root=True)
            self.assertNotEqual(first_hash, second_hash)
            self.assertTrue((root / "score_campaign_manifest_seed_42.json").is_file())
            self.assertTrue((root / "score_campaign_manifest_seed_43.json").is_file())
            payload = json.loads((root / "score_campaign_manifest_seed_42.json").read_text())
            self.assertEqual(payload["contract"], first)

    def test_mme_endpoint_partition_uses_all_replicas(self):
        endpoints = [f"http://judge-{index}/v1" for index in range(8)]

        groups = _partition_mme_endpoints(endpoints, 3)

        self.assertEqual([len(group) for group in groups], [3, 3, 2])
        self.assertEqual({endpoint for group in groups for endpoint in group}, set(endpoints))
        self.assertEqual(sum(map(len, groups)), len(endpoints))

    def test_score_validation_uses_established_mme_accuracy_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaign = Campaign(model="Qwen/Test", slug="test-model", root=root)
            score_file = root / "benchmark" / "mme_reasoning" / "test-model" / "run" / "scores.json"
            score_file.parent.mkdir(parents=True)
            score_file.write_text(
                json.dumps(
                    {
                        "model": campaign.model,
                        "model_slug": campaign.slug,
                        "rows": 3,
                        "accuracy": 100.0 / 3.0,
                    }
                ),
                encoding="utf-8",
            )

            completed = score_campaign._validate_score_outputs(
                [campaign],
                ("mme_reasoning",),
                benchmark_root=root / "benchmark",
                specs={"mme_reasoning": SimpleNamespace(run_name="run")},
                generation_inputs={"test-model": {"mme_reasoning": {"rows": 3}}},
            )

            self.assertEqual(len(completed), 1)
            self.assertAlmostEqual(completed[0]["score"], 100.0 / 3.0)

    def test_non_mme_score_validation_still_requires_score_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaign = Campaign(model="Qwen/Test", slug="test-model", root=root)
            score_file = root / "benchmark" / "mmstar" / "test-model" / "run" / "scores.json"
            score_file.parent.mkdir(parents=True)
            score_file.write_text(
                json.dumps({"rows": 1, "accuracy": 100.0}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "'score'"):
                score_campaign._validate_score_outputs(
                    [campaign],
                    ("mmstar",),
                    benchmark_root=root / "benchmark",
                    specs={"mmstar": SimpleNamespace(run_name="run")},
                    generation_inputs={"test-model": {"mmstar": {"rows": 1}}},
                )

    def test_direct_resume_requires_two_existing_archive_descriptors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score_file = root / "scores.json"
            descriptors = [root / "extraction.ready.json", root / "score.ready.json"]
            score_file.write_text(
                json.dumps({"archive_descriptors": [str(path) for path in descriptors]})
            )
            args = SimpleNamespace(emit_archive=True)

            self.assertFalse(
                score_campaign._direct_archive_descriptors_current(args, score_file)
            )
            for path in descriptors:
                path.write_text("{}")
            self.assertTrue(
                score_campaign._direct_archive_descriptors_current(args, score_file)
            )
            descriptors[0].unlink()
            self.assertFalse(
                score_campaign._direct_archive_descriptors_current(args, score_file)
            )

    def test_mme_resume_assigns_all_endpoints_to_only_pending_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaigns = [
                Campaign(model=f"model-{index}", slug=f"slug-{index}", root=root)
                for index in range(3)
            ]
            specs = {"mme_reasoning": SimpleNamespace(run_name="run")}
            for campaign in campaigns[:2]:
                score_file = root / "benchmark" / "mme_reasoning" / campaign.slug / "run" / "scores.json"
                score_file.parent.mkdir(parents=True, exist_ok=True)
                score_file.write_text("{}")
            endpoints = [f"http://judge-{index}/v1" for index in range(8)]
            assigned: list[tuple[str, list[str]]] = []

            def command(_args, campaign, **kwargs):
                assigned.append((campaign.slug, list(kwargs["endpoints"])))
                return ["true"]

            args = SimpleNamespace(resume=True, mme_workers=3)
            with (
                patch.object(score_campaign, "_validate_score_outputs", return_value=[]),
                patch.object(score_campaign, "_mme_command", side_effect=command),
                patch.object(score_campaign, "_run_logged"),
            ):
                _run_mme_phase(
                    args,
                    campaigns,
                    staged_run_root=root / "runs",
                    benchmark_root=root / "benchmark",
                    endpoints=endpoints,
                    env={},
                    log_root=root / "logs",
                    specs=specs,
                    generation_inputs={},
                )

            self.assertEqual(assigned, [("slug-2", endpoints)])

    def test_archive_preserves_unresolved_screenspot_extraction(self):
        row = pd.Series(
            {
                "trace_extraction_status": "ambiguous",
                "trace_extraction_method": "conflicting_json_point_2d",
                "trace_extraction_candidates": "[[10,20],[30,40]]",
            }
        )

        extraction = _archive_normalized_extraction(
            row,
            "pyautogui.click(x=1000000000000, y=1000000000000)",
            "fallback",
        )

        self.assertEqual(extraction["status"], "ambiguous")
        self.assertIsNone(extraction["value"])
        self.assertEqual(extraction["method"], "conflicting_json_point_2d")
        self.assertEqual(extraction["candidates"], [[10, 20], [30, 40]])

    def test_archive_joins_official_row_scores_by_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = pd.DataFrame(
                [
                    {"index": 1, "source_row_hash": "hash-a"},
                    {"index": 2, "source_row_hash": "hash-b"},
                ]
            )
            scored = pd.DataFrame(
                [
                    {"index": 2, "source_row_hash": "hash-b", "hit": 0},
                    {"index": 1, "source_row_hash": "hash-a", "hit": 1},
                ]
            )
            artifact = root / "official_result.xlsx"
            scored.to_excel(artifact, index=False)

            scores = _official_archive_row_scores(
                {"artifacts": {"official_outputs": [str(artifact)]}},
                source,
            )

            self.assertEqual(scores[0]["score"], 1.0)
            self.assertEqual(scores[1]["score"], 0.0)
            self.assertEqual(scores[0]["identity_column"], "source_row_hash")

    def test_archive_reads_hash_columns_as_strings_and_emits_exact_identity(self):
        request_hash = "194e088947465066b916808afc8c3ad82814f55231c1dc210af8907dead6e2b1"
        source_row_hash = "f" * 64
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staged = root / "source.xlsx"
            pd.DataFrame(
                [
                    {
                        "index": 9,
                        "question": "Choose one.",
                        "answer": "A",
                        "prediction": "A",
                        "request_hash": request_hash,
                        "source_row_hash": source_row_hash,
                    }
                ]
            ).to_excel(staged, index=False)
            prediction = root / "official_predictions.xlsx"
            pd.DataFrame(
                [{"index": 9, "answer": "A", "prediction": "A"}]
            ).to_excel(prediction, index=False)
            output_dir = root / "score"
            output_dir.mkdir()
            (output_dir / "scores.json").write_text(
                json.dumps(
                    {
                        "rows": 1,
                        "score": 100.0,
                        "primary_metric": {"key": "accuracy"},
                        "artifacts": {
                            "prediction_table": str(prediction),
                            "official_outputs": [],
                        },
                        "provenance": {
                            "contract": "test-official",
                            "prediction_adapter": None,
                        },
                    }
                ),
                encoding="utf-8",
            )
            campaign = Campaign(model="Qwen/Test", slug="test-model", root=root)
            workbook = Workbook(
                benchmark_key="countbenchqa",
                alias="CountBench",
                run_name="run",
                source=staged,
                staged=staged,
                sha256=hashlib.sha256(staged.read_bytes()).hexdigest(),
                primary=True,
            )
            job = score_campaign.OfficialJob(
                campaign=campaign,
                workbook=workbook,
                output_dir=output_dir,
                judge_kwargs={"model": "exact_matching"},
                primary_metric=None,
                primary_value_scale="auto",
            )

            with (
                patch("final25_archive_hooks.emit_extraction_slice") as emit_extraction,
                patch("final25_archive_hooks.emit_score_slice") as emit_score,
                patch(
                    "final25_archive_hooks.resolve_model_source",
                    return_value="Qwen/Test",
                ),
                patch(
                    "final25_archive_hooks.resolve_model_revision",
                    return_value="test-revision",
                ),
            ):
                score_campaign._archive_official_job(
                    SimpleNamespace(emit_archive=True, seed=42),
                    job,
                )

            extraction = emit_extraction.call_args.kwargs["records"][0]
            self.assertEqual(extraction["request_hash"], request_hash)
            self.assertEqual(extraction["source_row_hash"], source_row_hash)
            emit_score.assert_called_once()


if __name__ == "__main__":
    unittest.main()
