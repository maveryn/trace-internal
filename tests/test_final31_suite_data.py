from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    BENCHMARK_RUN_SETS,
    REMOTE_TSV_DATASET_FILES,
    REMOTE_TSV_DATASET_MD5,
    REMOTE_TSV_DATASET_MIRRORS,
    TRACE_FINAL26_BENCHMARKS,
    TRACE_FINAL31_ADDITIONS,
    TRACE_FINAL31_BENCHMARK_CATEGORIES,
    TRACE_FINAL31_BENCHMARKS,
    benchmark_specs_for_run_set,
    _ensure_dataset_mirror,
    spec_by_key,
)
from prepare_trace_final25_datasets import (  # noqa: E402
    EXPECTED_ROWS,
    EXPECTED_SUBDATASET_ROWS,
    _selected_keys,
    _subdataset_rows,
)
from trace_final25_contract import (  # noqa: E402
    FINAL31_DEDICATED_SCORE_KEYS,
    FINAL31_DIRECT_SCORE_KEYS,
    FINAL31_OFFICIAL_VLMEVAL_SCORE_KEYS,
)


SUITE_PATH = REPO_ROOT / "evaluation" / "final25" / "suite.v1.json"


def _suite() -> dict:
    return json.loads(SUITE_PATH.read_text(encoding="utf-8"))


def test_all31_is_all26_plus_five_explicit_additions() -> None:
    suite = _suite()
    expected = (*TRACE_FINAL26_BENCHMARKS, *TRACE_FINAL31_ADDITIONS)

    assert "trace_final31" in BENCHMARK_RUN_SETS
    assert tuple(suite["suites"]["all31"]) == expected == TRACE_FINAL31_BENCHMARKS
    assert len(expected) == len(set(expected)) == 31
    assert [spec.key for spec in benchmark_specs_for_run_set("trace_final31")] == list(expected)
    assert sum(EXPECTED_ROWS[key] for key in expected) == 40527


def test_all31_categories_cover_every_logical_benchmark_once() -> None:
    suite = _suite()
    entries = {entry["key"]: entry for entry in suite["benchmarks"]}
    categorized = [
        key
        for keys in TRACE_FINAL31_BENCHMARK_CATEGORIES.values()
        for key in keys
    ]

    assert len(categorized) == len(set(categorized)) == 31
    assert set(categorized) == set(TRACE_FINAL31_BENCHMARKS) == set(entries)
    for category, keys in TRACE_FINAL31_BENCHMARK_CATEGORIES.items():
        assert {key for key, entry in entries.items() if entry["category"] == category} == set(keys)


def test_all31_suite_routes_are_exhaustive_and_match_executable_contract() -> None:
    entries = {entry["key"]: entry for entry in _suite()["benchmarks"]}
    expected = {
        "direct_score": set(FINAL31_DIRECT_SCORE_KEYS),
        "official_vlmevalkit": set(FINAL31_OFFICIAL_VLMEVAL_SCORE_KEYS),
        "dedicated_score": set(FINAL31_DEDICATED_SCORE_KEYS),
    }

    assert set().union(*expected.values()) == set(TRACE_FINAL31_BENCHMARKS)
    assert sum(len(keys) for keys in expected.values()) == 31
    for route, keys in expected.items():
        assert {key for key, entry in entries.items() if entry["route"] == route} == keys


def test_final31_generation_specs_use_campaign_decoding_contract() -> None:
    for key in ("embspatial", "realworldqa", "visulogic"):
        spec = spec_by_key(key)
        assert (spec.max_tokens, spec.temperature, spec.top_p, spec.top_k) == (
            4096,
            0.6,
            1.0,
            -1,
        )
        assert spec.presence_penalty == 0.0

    gui_keys = (
        "screenspot",
        "screenspotpro",
        "screenspot_v2",
        "screenspotpro_development",
        "screenspotpro_creative",
        "screenspotpro_cad",
        "screenspotpro_scientific",
        "screenspotpro_office",
        "screenspotpro_os",
    )
    for key in gui_keys:
        spec = spec_by_key(key)
        assert (spec.max_tokens, spec.temperature, spec.top_p, spec.top_k) == (
            16384,
            0.6,
            1.0,
            -1,
        )
        assert spec.presence_penalty == 0.0


def test_all31_dataset_selection_is_explicit_and_rejects_unknown_views() -> None:
    suite = _suite()
    assert _selected_keys(suite, "all31", []) == list(TRACE_FINAL31_BENCHMARKS)
    assert _selected_keys(suite, "all31", ["visulogic", "screenspotpro"]) == [
        "screenspotpro",
        "visulogic",
    ]
    with pytest.raises(RuntimeError, match="unknown dataset view"):
        _selected_keys(suite, "typo", [])


def test_concat_receipts_preserve_official_child_order_and_counts() -> None:
    children = {
        alias: SimpleNamespace(data=range(rows))
        for alias, rows in EXPECTED_SUBDATASET_ROWS["ScreenSpot_v2"].items()
    }
    dataset = SimpleNamespace(
        datasets=list(children),
        dataset_map=children,
    )

    assert _subdataset_rows(dataset) == [
        {"alias": alias, "rows": rows}
        for alias, rows in EXPECTED_SUBDATASET_ROWS["ScreenSpot_v2"].items()
    ]
    assert sum(item["rows"] for item in _subdataset_rows(dataset)) == 1272
    assert sum(EXPECTED_SUBDATASET_ROWS["ScreenSpot_Pro"].values()) == 1581


def test_screenspot_v2_downloads_are_pinned_to_official_md5s() -> None:
    assert REMOTE_TSV_DATASET_FILES["screenspot_v2"][1] == "ScreenSpot_v2_Mobile.tsv"
    assert REMOTE_TSV_DATASET_FILES["screenspot_v2_desktop"][1] == "ScreenSpot_v2_Desktop.tsv"
    assert REMOTE_TSV_DATASET_FILES["screenspot_v2_web"][1] == "ScreenSpot_v2_Web.tsv"
    assert REMOTE_TSV_DATASET_MD5 == {
        "screenspot_v2": "234c858ab4f0e787e8388a73df65a4b7",
        "screenspot_v2_desktop": "5f2aa2a497327bd33b2512a0c75cf994",
        "screenspot_v2_web": "01cd0877ee1b735a6d5190b053ba9482",
    }
    assert REMOTE_TSV_DATASET_MIRRORS == {
        "screenspot_v2": "ScreenSpot_v2/ScreenSpot_v2_Mobile.tsv",
        "screenspot_v2_desktop": "ScreenSpot_v2/ScreenSpot_v2_Desktop.tsv",
        "screenspot_v2_web": "ScreenSpot_v2/ScreenSpot_v2_Web.tsv",
    }


def test_dataset_mirror_uses_a_hardlink_when_supported(tmp_path: Path) -> None:
    source = tmp_path / "ScreenSpot_v2_Mobile.tsv"
    mirror = tmp_path / "ScreenSpot_v2" / source.name
    source.write_bytes(b"pinned fixture")

    _ensure_dataset_mirror(source, mirror)

    assert mirror.read_bytes() == source.read_bytes()
    assert source.samefile(mirror)
