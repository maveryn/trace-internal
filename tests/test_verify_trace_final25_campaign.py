from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.final25_media_contract import (
    GENERATION_CONTRACT_VERSION,
    MEDIA_CONTRACT_VERSION,
    MEDIA_TRANSPORT,
    QWEN_MAX_IMAGE_PIXELS,
    QWEN_MIN_IMAGE_PIXELS,
)
from scripts.verify_trace_final25_campaign import (
    FINAL31_SUBDATASET_ROWS,
    _benchmarks_for_suite,
    _expected_generation_contract_hash,
    _generation_complete,
    _validate_all31_subdatasets,
)
from scripts.benchmark_queue_lib import (
    TRACE_FINAL25_BENCHMARKS,
    TRACE_FINAL26_BENCHMARKS,
    TRACE_FINAL31_BENCHMARKS,
)


MODEL = "/models/qwen"
MODEL_SLUG = "qwen"
MODEL_REVISION = "revision-a"
DATASET_SNAPSHOT = "a" * 64
DATASET_REVISION = f"trace-final25-datasets-v2:{DATASET_SNAPSHOT}"
CODE_HASH = "b" * 64
SEED = 42


def _expected_hash() -> str:
    return _expected_generation_contract_hash(
        model=MODEL,
        model_slug=MODEL_SLUG,
        model_revision=MODEL_REVISION,
        seed=SEED,
        dataset_snapshot_sha256=DATASET_SNAPSHOT,
        dataset_revision=DATASET_REVISION,
        final25_code_hash=CODE_HASH,
    )


def _summary() -> dict:
    return {
        "model": MODEL,
        "model_slug": MODEL_SLUG,
        "rows": 100,
        "expected_rows": 100,
        "subset_manifest": None,
        "generation": {
            "contract_version": GENERATION_CONTRACT_VERSION,
            "contract_hash": _expected_hash(),
            "media_contract_version": MEDIA_CONTRACT_VERSION,
            "media_transport": MEDIA_TRANSPORT,
            "dataset_snapshot_sha256": DATASET_SNAPSHOT,
            "dataset_revision": DATASET_REVISION,
            "model_revision": MODEL_REVISION,
            "selection": {
                "mode": "full",
                "limit": None,
                "sample_seed": None,
                "subset_manifest_sha256": None,
            },
            "temperature": 0.6,
            "top_p": 1.0,
            "top_k": -1,
            "presence_penalty": 0.0,
            "repetition_penalty": 1.0,
            "max_tokens": 4096,
            "seed": SEED,
            "min_image_pixels": QWEN_MIN_IMAGE_PIXELS,
            "max_image_pixels": QWEN_MAX_IMAGE_PIXELS,
            "compact_prediction_tables": True,
        },
    }


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _verify(path: Path) -> tuple[bool, str]:
    return _generation_complete(
        path,
        SEED,
        DATASET_REVISION,
        expected_model_revision=MODEL_REVISION,
        expected_contract_hash=_expected_hash(),
    )


def test_suite_selection_preserves_frozen_default_and_adds_mmvp_to_all26() -> None:
    assert _benchmarks_for_suite("frozen") == TRACE_FINAL25_BENCHMARKS
    assert _benchmarks_for_suite("all26") == TRACE_FINAL26_BENCHMARKS
    assert len(_benchmarks_for_suite("frozen")) == 25
    assert len(_benchmarks_for_suite("all26")) == 26
    assert _benchmarks_for_suite("all26")[-1] == "mmvp"
    assert _benchmarks_for_suite("all31") == TRACE_FINAL31_BENCHMARKS
    assert len(_benchmarks_for_suite("all31")) == 31


def test_generation_completion_accepts_final31_gui_token_contract(tmp_path: Path) -> None:
    path = tmp_path / "generation_summary.json"
    summary = _summary()
    summary["generation"]["max_tokens"] = 16384
    expected_hash = _expected_generation_contract_hash(
        model=MODEL,
        model_slug=MODEL_SLUG,
        model_revision=MODEL_REVISION,
        seed=SEED,
        dataset_snapshot_sha256=DATASET_SNAPSHOT,
        dataset_revision=DATASET_REVISION,
        final25_code_hash=CODE_HASH,
        max_tokens=16384,
    )
    summary["generation"]["contract_hash"] = expected_hash
    _write(path, summary)

    assert _generation_complete(
        path,
        SEED,
        DATASET_REVISION,
        expected_model_revision=MODEL_REVISION,
        expected_contract_hash=expected_hash,
        expected_max_tokens=16384,
    ) == (True, "100/100")


def test_final31_concat_receipts_require_exact_subdataset_counts(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    payload = {
        "datasets": {
            key: {
                "rows": sum(entries.values()),
                "subdatasets": [
                    {"alias": alias, "rows": rows}
                    for alias, rows in entries.items()
                ],
            }
            for key, entries in FINAL31_SUBDATASET_ROWS.items()
        }
    }
    _write(path, payload)
    _validate_all31_subdatasets(path)

    payload["datasets"]["screenspot_v2"]["subdatasets"][0]["rows"] = 502
    _write(path, payload)
    try:
        _validate_all31_subdatasets(path)
    except ValueError as exc:
        assert "screenspot_v2" in str(exc)
    else:
        raise AssertionError("stale ScreenSpot v2 split counts must fail verification")


def test_generation_completion_accepts_only_exact_full_contract(tmp_path: Path) -> None:
    path = tmp_path / "generation_summary.json"
    _write(path, _summary())

    assert _verify(path) == (True, "100/100")


def test_generation_completion_rejects_limit_or_subset_identity(tmp_path: Path) -> None:
    path = tmp_path / "generation_summary.json"
    limited = copy.deepcopy(_summary())
    limited["rows"] = limited["expected_rows"] = 2
    limited["generation"]["selection"] = {
        "mode": "limit",
        "limit": 2,
        "sample_seed": 7,
        "subset_manifest_sha256": None,
    }
    _write(path, limited)

    complete, detail = _verify(path)
    assert not complete
    assert "full_selection" in detail

    subset = copy.deepcopy(_summary())
    subset["subset_manifest"] = "/tmp/subset/demo.jsonl"
    subset["generation"]["selection"] = {
        "mode": "subset",
        "limit": None,
        "sample_seed": 0,
        "subset_manifest_sha256": "c" * 64,
    }
    _write(path, subset)

    complete, detail = _verify(path)
    assert not complete
    assert "full_selection" in detail


def test_generation_completion_rejects_model_revision_and_contract_hash(tmp_path: Path) -> None:
    path = tmp_path / "generation_summary.json"
    stale = copy.deepcopy(_summary())
    stale["generation"]["model_revision"] = "revision-old"
    stale["generation"]["contract_hash"] = "d" * 64
    _write(path, stale)

    complete, detail = _verify(path)
    assert not complete
    assert "model_revision" in detail
    assert "contract_hash" in detail
