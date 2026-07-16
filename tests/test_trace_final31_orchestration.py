from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.benchmark_queue_lib import (
    TRACE_FINAL31_BENCHMARKS,
    run_dir,
    score_path,
    spec_by_key,
)
from scripts.run_external_benchmark_generation_api_queue import build_parser
from scripts.status_trace_final31_campaign import collect_status


def test_generation_parser_accepts_all31_manifest_view() -> None:
    args = build_parser().parse_args(
        [
            "--model", "model",
            "--model-slug", "model",
            "--api-model", "model",
            "--dataset-manifest-view", "all31",
            "--run-set", "trace_final31",
        ]
    )
    assert args.dataset_manifest_view == "all31"
    assert args.run_set == "trace_final31"


def test_status_requires_all_31_response_and_score_slices(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    score_root = campaign_root / "scoring"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "dataset_views": {"all31": list(TRACE_FINAL31_BENCHMARKS)},
                "datasets": {key: {"rows": 1} for key in TRACE_FINAL31_BENCHMARKS},
            }
        ),
        encoding="utf-8",
    )
    run_root = campaign_root / "seed_42" / "runs"
    benchmark_root = score_root / "seed_42" / "benchmark"
    for key in TRACE_FINAL31_BENCHMARKS:
        spec = spec_by_key(key)
        row_dir = run_dir(spec, "model", run_root) / "api_row_results"
        row_dir.mkdir(parents=True, exist_ok=True)
        (row_dir / "row.json").write_text("{}", encoding="utf-8")
        score = score_path(spec, "model", benchmark_root)
        score.parent.mkdir(parents=True, exist_ok=True)
        score.write_text(json.dumps({"score": 50.0, "rows": 1}), encoding="utf-8")

    args = argparse.Namespace(
        campaign_root=campaign_root,
        score_root=score_root,
        dataset_manifest=manifest,
        archive_spool_root=campaign_root / "hf_archive",
        model_slugs=("model",),
        seeds=[42],
        rate_window_seconds=300.0,
        low_gpu_threshold=10,
        gpu=False,
    )
    report = collect_status(args)
    assert report["durable_rows"] == 31
    assert report["expected_rows"] == 31
    assert report["score_slices"] == 31
    assert report["complete"] is True


def test_launcher_pins_schema_revision_and_qwen3_judge_contract() -> None:
    script = (Path(__file__).resolve().parents[1] / "scripts" / "run_trace_final31_temp06_3seed_3models.sh").read_text()
    assert 'TRACE_FINAL25_DATASET_REVISION="${dataset_schema}:${dataset_snapshot}"' in script
    assert '--dataset-manifest-view all31' in script
    assert 'qwen3 "${REPO_ROOT}/rlvr/examples/prompts/chat_template_no_think.jinja"' in script
    assert 'FINALIZER_JOBS="${FINALIZER_JOBS:-2}"' in script
    assert '--batch-size 48 --upload-threads 8 flush' in script
    assert 'stop_background_pid "${archive_pid}"' in script
    assert 'archive_pid=""\nflush_archive\n' in script
