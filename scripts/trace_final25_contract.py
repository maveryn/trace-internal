#!/usr/bin/env python3
"""Canonical scoring contracts for TRACE Final25 and provisional MMVP."""

from __future__ import annotations

from dataclasses import dataclass

from benchmark_queue_lib import (
    TRACE_FINAL24_BENCHMARK_CATEGORIES,
    TRACE_FINAL24_BENCHMARKS,
    TRACE_FINAL25_BENCHMARK_CATEGORIES,
    TRACE_FINAL31_BENCHMARK_CATEGORIES,
)


@dataclass(frozen=True)
class Final25Contract:
    key: str
    output_type: str
    extraction: str
    scoring: str
    judge_role: str
    runner: str


def _pinned_vlmeval_contract(key: str, output_type: str) -> Final25Contract:
    return Final25Contract(
        key,
        output_type,
        "benchmark-defined handling inside pinned VLMEvalKit dataset.evaluate",
        "benchmark-defined metric from pinned VLMEvalKit dataset.evaluate",
        "benchmark-defined",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    )


CONTRACTS: tuple[Final25Contract, ...] = (
    Final25Contract(
        "chartmuseum",
        "short/free-form answer",
        "pinned ChartMuseum extract_answer",
        "pinned COMPARE_ANSWER_PROMPT and yes-substring decision",
        "scoring",
        "run_external_benchmark_score_queue.py:chartmuseum_local_judge",
    ),
    Final25Contract(
        "chartqapro",
        "short answer after reasoning",
        "mandated final 'The answer is X' sentence",
        "pinned ChartQAPro dataset.evaluate",
        "benchmark-defined",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    Final25Contract(
        "charxivreason",
        "free-form chart reasoning answer",
        "benchmark grading prompt extracts answer",
        "Qwen3-32B rubric score from benchmark grading prompt",
        "both",
        "run_external_benchmark_score_queue.py:charxiv_local_judge",
    ),
    Final25Contract(
        "tablevqabench",
        "short text/number/boolean",
        "pinned parser (only the official leading 'Answer: ' cleanup)",
        "pinned FinTabNetQA, VTabFact, VWTQ, and VWTQ-Syn scorers",
        "none",
        "run_external_benchmark_score_queue.py:tablevqabench_local_score",
    ),
    Final25Contract(
        "evochart",
        "short/free-form chart answer",
        "deterministic final-answer parsing in the TRACE dataset extension",
        "local deterministic EvoChart extension (pinned upstream has no evaluator)",
        "none",
        "run_external_benchmark_score_queue.py:evochart_local_score",
    ),
    Final25Contract(
        "mathvision",
        "math answer",
        "official prefetch, else Qwen3-32B answer extraction",
        "official MathVision normalized answer scorer",
        "extraction",
        "run_external_benchmark_score_queue.py:mathv_local_judge",
    ),
    Final25Contract(
        "mathvista",
        "math/MCQ answer",
        "official prefetch, else Qwen3-32B answer extraction",
        "official MathVista normalized answer scorer",
        "extraction",
        "run_external_benchmark_score_queue.py:mathvista_local_judge",
    ),
    Final25Contract(
        "mathverse",
        "math answer after reasoning",
        "Qwen3-32B answer extraction",
        "official prefetch, else strict Qwen3-32B binary correctness judge",
        "both",
        "run_external_benchmark_score_queue.py:mathverse_local_judge",
    ),
    Final25Contract(
        "wemath",
        "MCQ option",
        "benchmark-defined handling inside pinned VLMEvalKit dataset.evaluate",
        "pinned WeMath dataset.evaluate Score (Strict) percent metric",
        "benchmark-defined",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    Final25Contract(
        "phyx_mini_mc",
        "MCQ option",
        "deterministic final-option extraction before pinned VLMEvalKit evaluation",
        "pinned PhyX aggregation after deterministic option normalization",
        "none",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    Final25Contract(
        "physics",
        "free-form physics answer",
        "official VLMEvalKit boxed-answer extraction",
        "official VLMEvalKit is_equiv with Qwen3-32B fallback",
        "scoring",
        "run_external_benchmark_score_queue.py:physics_local_judge",
    ),
    _pinned_vlmeval_contract("mmmu_pro_vision", "MCQ option"),
    _pinned_vlmeval_contract("mmstar", "MCQ option"),
    Final25Contract(
        "screenspot",
        "GUI click point",
        "strict point_2d JSON adapter, then pinned named x/y parser",
        "pinned point-inside-target-box accuracy",
        "none",
        "run_external_benchmark_score_queue.py:screenspot",
    ),
    _pinned_vlmeval_contract("spatialvizbench_cot", "MCQ option"),
    _pinned_vlmeval_contract("cvbench_3d", "MCQ option"),
    Final25Contract(
        "erqa",
        "MCQ option",
        "benchmark-defined handling inside pinned ERQABench.evaluate",
        "pinned EASI ERQABench metric (duplicate ERQADataset registry entry bypassed)",
        "benchmark-defined",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    _pinned_vlmeval_contract("blink", "MCQ option"),
    _pinned_vlmeval_contract("countbenchqa", "integer count"),
    _pinned_vlmeval_contract("countqa", "integer count"),
    Final25Contract(
        "treebench",
        "MCQ option",
        "pinned parser after one explicit final boxed-option adapter",
        "pinned TreeBench dimension metric",
        "benchmark-defined",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    _pinned_vlmeval_contract("puzzlevqa", "MCQ option or option value"),
    _pinned_vlmeval_contract("visualpuzzles", "MCQ option"),
    Final25Contract(
        "logicvista",
        "one or more MCQ letters",
        "pinned option-set extraction with a numeric-label-only exception",
        "pinned exact normalized option-set comparison",
        "extraction",
        "run_external_benchmark_score_queue.py:logicvista_local_judge",
    ),
    Final25Contract(
        "mme_reasoning",
        "mixed MCQ, open, and structured puzzle answer",
        "official task-specific Qwen3-32B extraction prompts",
        "official deterministic functions; Qwen3-32B only for open-answer correctness",
        "both",
        "run_mme_reasoning_eval.py",
    ),
)

MMVP_CONTRACT = _pinned_vlmeval_contract("mmvp", "paired MCQ option")
ALL26_CONTRACTS = (*CONTRACTS, MMVP_CONTRACT)
FINAL31_ADDITION_CONTRACTS = (
    Final25Contract(
        "screenspotpro",
        "GUI click point",
        "strict final point_2d JSON adapter",
        "pinned ScreenSpotPro point-inside-target-box metric, pooled over six subsets",
        "none",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    Final25Contract(
        "screenspot_v2",
        "GUI click point",
        "strict final point_2d JSON adapter",
        "pinned ScreenSpot v2 point-inside-target-box metric, pooled over three subsets",
        "none",
        "run_official_vlmevalkit_saved_score.py:dataset.evaluate",
    ),
    _pinned_vlmeval_contract("embspatial", "MCQ option"),
    _pinned_vlmeval_contract("realworldqa", "MCQ option"),
    _pinned_vlmeval_contract("visulogic", "boxed MCQ option"),
)
ALL31_CONTRACTS = (*ALL26_CONTRACTS, *FINAL31_ADDITION_CONTRACTS)


CONTRACT_BY_KEY = {contract.key: contract for contract in CONTRACTS}
ALL26_CONTRACT_BY_KEY = {contract.key: contract for contract in ALL26_CONTRACTS}
ALL31_CONTRACT_BY_KEY = {contract.key: contract for contract in ALL31_CONTRACTS}
FINAL24_CONTRACTS = tuple(ALL31_CONTRACT_BY_KEY[key] for key in TRACE_FINAL24_BENCHMARKS)
FINAL24_CONTRACT_BY_KEY = {contract.key: contract for contract in FINAL24_CONTRACTS}
CATEGORY_BY_KEY = {
    key: category
    for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items()
    for key in keys
}
FINAL31_CATEGORY_BY_KEY = {
    key: category
    for category, keys in TRACE_FINAL31_BENCHMARK_CATEGORIES.items()
    for key in keys
}
FINAL24_CATEGORY_BY_KEY = {
    key: category
    for category, keys in TRACE_FINAL24_BENCHMARK_CATEGORIES.items()
    for key in keys
}

DIRECT_SCORE_KEYS = (
    "chartmuseum",
    "charxivreason",
    "tablevqabench",
    "evochart",
    "mathvision",
    "mathvista",
    "mathverse",
    "physics",
    "screenspot",
    "logicvista",
)
FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS = (
    "chartqapro",
    "wemath",
    "phyx_mini_mc",
    "mmmu_pro_vision",
    "mmstar",
    "spatialvizbench_cot",
    "cvbench_3d",
    "erqa",
    "blink",
    "countbenchqa",
    "countqa",
    "treebench",
    "puzzlevqa",
    "visualpuzzles",
)
OFFICIAL_VLMEVAL_SCORE_KEYS = (*FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS, "mmvp")
FINAL31_OFFICIAL_VLMEVAL_SCORE_KEYS = (
    *OFFICIAL_VLMEVAL_SCORE_KEYS,
    "screenspotpro",
    "screenspot_v2",
    "embspatial",
    "realworldqa",
    "visulogic",
)
FINAL31_DIRECT_SCORE_KEYS = DIRECT_SCORE_KEYS
FINAL31_DEDICATED_SCORE_KEYS = ("mme_reasoning",)
DEDICATED_SCORE_KEYS = ("mme_reasoning",)
FINAL24_DIRECT_SCORE_KEYS = tuple(
    key for key in TRACE_FINAL24_BENCHMARKS if key in FINAL31_DIRECT_SCORE_KEYS
)
FINAL24_OFFICIAL_VLMEVAL_SCORE_KEYS = tuple(
    key for key in TRACE_FINAL24_BENCHMARKS if key in FINAL31_OFFICIAL_VLMEVAL_SCORE_KEYS
)
FINAL24_DEDICATED_SCORE_KEYS = tuple(
    key for key in TRACE_FINAL24_BENCHMARKS if key in FINAL31_DEDICATED_SCORE_KEYS
)

# Compatibility alias for older queue code. These frozen-suite keys no longer
# use TRACE's generic Qwen extraction queue; the final route is pinned
# VLMEvalKit ``dataset.evaluate`` on the saved prediction workbook.
LLM_EXTRACT_SCORE_KEYS = FROZEN_OFFICIAL_VLMEVAL_SCORE_KEYS

# Compatibility metadata used only by the retired generic extraction queue
# and its historical artifact audit. Final scoring for these keys is pinned
# VLMEvalKit ``dataset.evaluate``.
OPTION_TEXT_REQUIRED_KEYS = (
    "wemath",
    "phyx_mini_mc",
    "mmmu_pro_vision",
    "mmstar",
    "spatialvizbench_cot",
    "cvbench_3d",
    "erqa",
    "blink",
    "treebench",
    "puzzlevqa",
)

# Compatibility metadata for the retired extraction queue's historical
# artifact audit. The final pinned evaluator receives the saved workbook.
SOURCE_ROW_EXCLUSIONS = {
    "mmstar": {
        "268": "official source omits the gold A option text",
        "273": "official source omits the gold A option text",
    },
}
