from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    BENCHMARK_RUN_SETS,
    TRACE_FINAL25_BENCHMARKS,
    TRACE_FINAL26_BENCHMARKS,
    benchmark_specs_for_run_set,
    local_judge_eval_mode,
    spec_by_key,
)


def _suite() -> dict:
    return json.loads(
        (REPO_ROOT / "evaluation" / "final25" / "suite.v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_trace_final26_matches_manifest_all26_union_in_order() -> None:
    suite = _suite()
    expected = list(suite["suites"]["frozen"])
    expected.extend(
        key for key in suite["suites"]["provisional_mmvp"] if key not in expected
    )

    assert "trace_final26" in BENCHMARK_RUN_SETS
    assert tuple(suite["suites"]["frozen"]) == TRACE_FINAL25_BENCHMARKS
    assert tuple(expected) == TRACE_FINAL26_BENCHMARKS
    assert len(TRACE_FINAL26_BENCHMARKS) == len(set(TRACE_FINAL26_BENCHMARKS)) == 26
    assert [spec.key for spec in benchmark_specs_for_run_set("trace_final26")] == expected


def test_mmvp_spec_uses_official_paired_option_contract() -> None:
    entry = next(item for item in _suite()["benchmarks"] if item["key"] == "mmvp")
    spec = spec_by_key("mmvp")

    assert spec.display == entry["display_name"] == "MMVP"
    assert spec.alias == entry["vlmeval_alias"] == "MMVP"
    assert entry["route"] == "official_vlmevalkit"
    assert entry["answer_contract"] == "paired_option"
    assert entry["score_contract"] == "official_mmvp_paired"
    assert spec.kind == "vlmeval"
    assert spec.eval_mode == "auto"
    assert local_judge_eval_mode(spec) is None
    assert spec.run_name == "vlmevalkit_defaults"
    assert (spec.max_tokens, spec.temperature, spec.top_p, spec.top_k) == (
        4096,
        0.6,
        1.0,
        -1,
    )
    assert spec.presence_penalty == 0.0
    assert "both questions" in spec.note
