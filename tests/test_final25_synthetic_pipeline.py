from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
EXTRA_DEPS_ROOT = REPO_ROOT / ".tmp" / "eval_deps"
SUITE_PATH = REPO_ROOT / "evaluation" / "final25" / "suite.v1.json"
PINNED_VLMEVAL_COMMIT = "a8b12bf1c3737a33fc1de967c202f9c592b22e86"

os.environ.setdefault("LMUData", "/tmp/trace-final25-synthetic-lmudata")
Path(os.environ["LMUData"]).mkdir(parents=True, exist_ok=True)
for path in (EXTRA_DEPS_ROOT, SCRIPTS_ROOT, VLMEVAL_ROOT, VLMEVAL_ROOT / "scripts"):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_FINAL25_BENCHMARKS,
    TRACE_FINAL25_BENCHMARK_CATEGORIES,
    spec_by_key,
)
from run_external_benchmark_score_queue import (  # noqa: E402
    _parse_chartmuseum_judgement_output,
    _resolve_charxiv_extracted_answer,
    _resolve_evochart_judgement,
)
from run_llm_extracted_benchmark_score_queue import (  # noqa: E402
    SHADOW_CONTRACT_VERSION,
    _score_option_or_number,
    _shadow_extraction_record,
)
from run_mme_reasoning_eval import _validate_extraction  # noqa: E402
from trace_benchmark_answer_parsing import extract_click_point, parse_binary_score  # noqa: E402
from trace_final25_contract import (  # noqa: E402
    DEDICATED_SCORE_KEYS,
    DIRECT_SCORE_KEYS,
    FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS,
)


def _load_suite() -> dict[str, Any]:
    return json.loads(SUITE_PATH.read_text(encoding="utf-8"))


_OPTION_CASES = {
    "wemath",
    "phyx_mini_mc",
    "mmmu_pro_vision",
    "mmstar",
    "spatialvizbench_cot",
    "cvbench_3d",
    "erqa",
    "blink",
    "treebench",
    "visualpuzzles",
    "mme_reasoning",
    "mmvp",
}


SYNTHETIC_CASES: tuple[dict[str, Any], ...] = (
    {"key": "chartmuseum", "kind": "short", "response": "<answer>42</answer>", "gold": "42", "expected": "42", "probe": "chartmuseum_judge"},
    {"key": "chartqapro", "kind": "short", "response": "<answer>12.5</answer>", "gold": "12.5", "expected": "12.5", "probe": "exact"},
    {"key": "charxivreason", "kind": "short", "response": "<answer>increased</answer>", "gold": "increased", "expected": "increased", "probe": "charxiv_judge"},
    {"key": "tablevqabench", "kind": "short", "response": "<answer>Yes</answer>", "gold": "yes", "expected": "Yes", "probe": "exact"},
    {"key": "evochart", "kind": "short", "response": "<answer>2019</answer>", "gold": "2019", "expected": "2019", "probe": "evochart_judge"},
    {"key": "mathvision", "kind": "short", "response": "<answer>7/2</answer>", "gold": "7/2", "expected": "7/2", "probe": "exact"},
    {"key": "mathvista", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "mathverse", "kind": "short", "response": "<answer>sqrt(3)</answer>", "gold": "sqrt(3)", "expected": "sqrt(3)", "probe": "exact"},
    {"key": "wemath", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "phyx_mini_mc", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "physics", "kind": "judge_binary", "response": "<answer>9.8 m/s^2</answer>", "gold": "9.8 m/s^2", "expected": "9.8 m/s^2", "probe": "binary_judge"},
    {"key": "mmmu_pro_vision", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "mmstar", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "screenspot", "kind": "short", "response": "<answer>[50, 60]</answer>", "gold": "[50, 60]", "expected": "[50, 60]", "probe": "point"},
    {"key": "spatialvizbench_cot", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "cvbench_3d", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "erqa", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "blink", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "countbenchqa", "kind": "number", "response": "<answer>004</answer>", "gold": "4", "expected": "4", "probe": "exact"},
    {"key": "countqa", "kind": "number", "response": "<answer>11</answer>", "gold": "11", "expected": "11", "probe": "exact"},
    {"key": "treebench", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "puzzlevqa", "kind": "option_value", "response": "<answer>B</answer>", "gold": "triangle", "expected": "B", "probe": "exact"},
    {"key": "visualpuzzles", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "exact"},
    {"key": "logicvista", "kind": "short", "response": "<answer>A,C</answer>", "gold": "A,C", "expected": "A,C", "probe": "exact"},
    {"key": "mme_reasoning", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "mme_choice"},
    {"key": "mmvp", "kind": "option", "response": "<answer>B</answer>", "gold": "B", "expected": "B", "probe": "mmvp_paired"},
)


def _item(case: dict[str, Any], response: str | None = None) -> dict[str, Any]:
    key = str(case["key"])
    prediction = str(case["response"] if response is None else response)
    options = {"A": "circle", "B": "triangle", "C": "square", "D": "star"}
    return {
        "job_id": f"synthetic__{key}",
        "benchmark": key,
        "model_slug": "synthetic-model",
        "index": "0",
        "ordinal": 0,
        "prediction": prediction,
        "response_sha256": hashlib.sha256(prediction.encode("utf-8")).hexdigest(),
        "answer": case["gold"],
        "answer_kind": case["kind"],
        "valid_letters": list("ABCD"),
        "options": options,
        "extracted": case["expected"],
    }


def test_suite_manifest_has_frozen_and_provisional_25_views() -> None:
    suite = _load_suite()
    frozen = suite["suites"]["frozen"]
    provisional = suite["suites"]["provisional_mmvp"]

    assert suite["schema_version"] == "trace-final25-suite-v1"
    assert suite["vlmevalkit"]["commit"] == PINNED_VLMEVAL_COMMIT
    assert len(frozen) == len(set(frozen)) == 25
    assert len(provisional) == len(set(provisional)) == 25
    assert tuple(frozen) == TRACE_FINAL25_BENCHMARKS
    assert set(frozen) - set(provisional) == {"countqa"}
    assert set(provisional) - set(frozen) == {"mmvp"}
    assert suite["provisional_replacement"]["expected_rows"] == 300
    assert suite["provisional_replacement"]["primary_metric"] == "Overall"


def test_manifest_matches_registered_alias_categories_and_score_routes() -> None:
    suite = _load_suite()
    entries = {entry["key"]: entry for entry in suite["benchmarks"]}
    frozen = set(suite["suites"]["frozen"])

    assert set(entries) == frozen | {"mmvp"}
    assert {entry["key"] for entry in suite["benchmarks"] if entry["category"] == "Perception & Counting"} == {
        "blink",
        "countbenchqa",
        "countqa",
        "mmvp",
        "treebench",
    }
    for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items():
        assert {entry["key"] for entry in suite["benchmarks"] if entry["category"] == category} & frozen == set(keys)
    for key in frozen:
        assert entries[key]["vlmeval_alias"] == spec_by_key(key).alias

    assert {key for key in frozen if entries[key]["route"] == "direct_score"} == set(DIRECT_SCORE_KEYS)
    assert {key for key in frozen if entries[key]["route"] == "official_vlmevalkit"} == (
        set(FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS)
    )
    assert {key for key in frozen if entries[key]["route"] == "dedicated_score"} == set(DEDICATED_SCORE_KEYS)
    assert entries["chartqapro"]["answer_contract"] == "mandated_final_the_answer_is_sentence"
    assert entries["wemath"]["primary_metric"] == "Score (Strict)"
    assert entries["wemath"]["primary_metric_scale"] == "percent"
    assert entries["erqa"]["dataset_class"] == "vlmeval.dataset.erqabench.ERQABench"


def test_checked_out_vlmevalkit_matches_manifest_pin_when_present() -> None:
    if not (VLMEVAL_ROOT / ".git").exists():
        pytest.skip("external/VLMEvalKit is not checked out")
    actual = subprocess.check_output(
        ["git", "-C", str(VLMEVAL_ROOT), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    assert actual == PINNED_VLMEVAL_COMMIT


def test_final25_configuration_directory_contains_no_runtime_results() -> None:
    forbidden_suffixes = {".csv", ".jsonl", ".parquet", ".tsv", ".xls", ".xlsx"}
    files = [path for path in SUITE_PATH.parent.rglob("*") if path.is_file()]
    assert files
    assert not [path for path in files if path.suffix.lower() in forbidden_suffixes]


@pytest.mark.parametrize("case", SYNTHETIC_CASES, ids=lambda case: case["key"])
def test_each_benchmark_has_a_resolved_synthetic_handoff_and_score_probe(case: dict[str, Any]) -> None:
    record = _shadow_extraction_record(_item(case))

    assert record["status"] == "resolved_explicit"
    assert record["candidate"] == case["expected"]
    assert record["contract_version"] == SHADOW_CONTRACT_VERSION
    assert record["score_neutral"] is True

    probe = case["probe"]
    if probe == "exact":
        score, rows = _score_option_or_number([_item(case)])
        assert score == 100.0
        assert rows[0]["eval_score"] == 1
    elif probe == "chartmuseum_judge":
        assert _parse_chartmuseum_judgement_output("Yes. The answers agree.") == 1
        assert _parse_chartmuseum_judgement_output("maybe") == 0
    elif probe == "charxiv_judge":
        extracted, method = _resolve_charxiv_extracted_answer(
            {"extract_answer": case["expected"]},
            {},
            case["response"],
        )
        assert (extracted, method) == (case["expected"], "judge")
        score = float(json.loads('{"score": 1.0}')["score"])
        assert 0.0 <= score <= 1.0
    elif probe == "evochart_judge":
        score, extracted, method = _resolve_evochart_judgement(
            '{"score": 1, "extracted_answer": "2019"}',
            case["response"],
        )
        assert (score, extracted, method) == (1.0, "2019", "judge_json")
    elif probe == "binary_judge":
        assert parse_binary_score('{"score": 1}') == 1.0
        assert parse_binary_score("probably correct") is None
    elif probe == "point":
        point = extract_click_point(case["response"])
        assert point == (50.0, 60.0)
        target_box = (40.0, 50.0, 70.0, 80.0)
        assert target_box[0] <= point[0] <= target_box[2]
        assert target_box[1] <= point[1] <= target_box[3]
    elif probe == "mme_choice":
        valid, normalized = _validate_extraction("choice_prompt", case["expected"])
        assert valid is True
        assert normalized == case["expected"]
    elif probe == "mmvp_paired":
        from vlmeval.dataset.utils.multiple_choice import report_acc_MMVP

        metrics = report_acc_MMVP(
            pd.DataFrame(
                {
                    "question": ["pair one", "pair one", "pair two", "pair two"],
                    "hit": [1, 1, 1, 0],
                }
            )
        )
        assert float(metrics.loc[0, "Average"]) == pytest.approx(0.75)
        assert float(metrics.loc[0, "Overall"]) == pytest.approx(0.5)
    else:  # pragma: no cover - fixture completeness guard
        raise AssertionError(f"Unknown synthetic score probe: {probe}")


def test_synthetic_cases_cover_frozen_suite_plus_mmvp_once() -> None:
    expected = set(_load_suite()["suites"]["frozen"]) | {"mmvp"}
    observed = [str(case["key"]) for case in SYNTHETIC_CASES]
    assert len(observed) == len(set(observed)) == 26
    assert set(observed) == expected
    assert _OPTION_CASES <= set(observed)


def test_shadow_parser_keeps_raw_and_conflicting_candidates_unresolved() -> None:
    base_case = next(case for case in SYNTHETIC_CASES if case["key"] == "wemath")

    raw = _shadow_extraction_record(_item(base_case, response="B"))
    assert raw["status"] == "unresolved_raw"
    assert raw["candidate"] == ""
    assert raw["candidates"] == []
    assert raw["score_neutral"] is True

    conflict = _shadow_extraction_record(
        _item(base_case, response="<answer>A</answer>\nFinal answer: B")
    )
    assert conflict["status"] == "conflict"
    assert conflict["candidate"] == ""
    assert {candidate["normalized"] for candidate in conflict["candidates"]} == {"A", "B"}
    assert conflict["score_neutral"] is True

    scalar_conflict = _shadow_extraction_record(
        _item(base_case, response="<answer>A or B</answer>")
    )
    assert scalar_conflict["status"] == "conflict"
    assert scalar_conflict["candidate"] == ""
    assert {candidate["normalized"] for candidate in scalar_conflict["candidates"]} == {
        "A",
        "B",
    }

    count_case = next(case for case in SYNTHETIC_CASES if case["key"] == "countbenchqa")
    number_conflict = _shadow_extraction_record(
        _item(count_case, response="<answer>4 or 5</answer>")
    )
    assert number_conflict["status"] == "conflict"
    assert number_conflict["candidate"] == ""
    assert {candidate["normalized"] for candidate in number_conflict["candidates"]} == {
        "4",
        "5",
    }


def test_malformed_judge_output_is_not_interpreted_as_zero() -> None:
    assert parse_binary_score("") is None
    assert parse_binary_score("The response appears wrong, but no score was emitted.") is None
    assert _parse_chartmuseum_judgement_output("Unable to decide") == 0
