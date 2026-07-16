from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_FINAL24_BENCHMARK_CATEGORIES,
    TRACE_FINAL24_BENCHMARKS,
    TRACE_FINAL31_BENCHMARKS,
    spec_by_key,
)
from prepare_trace_final25_datasets import EXPECTED_ROWS  # noqa: E402
from summarize_trace_final25_multiseed import (  # noqa: E402
    _benchmark_rows_for_suite,
    _categories_for_suite,
    _default_title,
)
from trace_final25_contract import (  # noqa: E402
    FINAL24_CONTRACT_BY_KEY,
    FINAL24_DEDICATED_SCORE_KEYS,
    FINAL24_DIRECT_SCORE_KEYS,
    FINAL24_OFFICIAL_VLMEVAL_SCORE_KEYS,
)


SELECTION_PATH = REPO_ROOT / "evaluation" / "final24" / "suite.v1.json"
SOURCE_PATH = REPO_ROOT / "evaluation" / "final25" / "suite.v1.json"


def test_final24_selection_is_exact_balanced_and_pinned() -> None:
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    source_sha256 = hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
    flattened = tuple(key for keys in selection["categories"].values() for key in keys)

    assert selection["schema_version"] == "trace-final24-suite-v1"
    assert selection["status"] == "canonical"
    assert selection["source_contract"]["sha256"] == source_sha256
    assert tuple(selection["benchmarks"]) == flattened == TRACE_FINAL24_BENCHMARKS
    assert selection["categories"] == {
        category: list(keys) for category, keys in TRACE_FINAL24_BENCHMARK_CATEGORIES.items()
    }
    assert len(selection["categories"]) == 6
    assert {len(keys) for keys in selection["categories"].values()} == {4}
    assert len(flattened) == len(set(flattened)) == 24
    assert set(flattened).issubset(TRACE_FINAL31_BENCHMARKS)


def test_final24_inherits_complete_all31_routes_and_expected_rows() -> None:
    routed = (
        *FINAL24_DIRECT_SCORE_KEYS,
        *FINAL24_OFFICIAL_VLMEVAL_SCORE_KEYS,
        *FINAL24_DEDICATED_SCORE_KEYS,
    )

    assert (len(FINAL24_DIRECT_SCORE_KEYS), len(FINAL24_OFFICIAL_VLMEVAL_SCORE_KEYS)) == (7, 16)
    assert FINAL24_DEDICATED_SCORE_KEYS == ("mme_reasoning",)
    assert len(routed) == len(set(routed)) == 24
    assert set(routed) == set(TRACE_FINAL24_BENCHMARKS) == set(FINAL24_CONTRACT_BY_KEY)
    assert sum(EXPECTED_ROWS[key] for key in TRACE_FINAL24_BENCHMARKS) == 32805
    for key in TRACE_FINAL24_BENCHMARKS:
        assert spec_by_key(key).key == key


def test_final24_summary_uses_the_canonical_categories_and_title() -> None:
    assert _categories_for_suite("final24") == TRACE_FINAL24_BENCHMARK_CATEGORIES
    assert [key for _, key in _benchmark_rows_for_suite("final24")] == list(
        TRACE_FINAL24_BENCHMARKS
    )
    assert _default_title("final24", [42, 43, 44]) == (
        "TRACE Final24 Temp0.6 Three-Seed Results"
    )
