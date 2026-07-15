#!/usr/bin/env python3
"""Canonical extraction and scoring contracts for TRACE Final25 evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from benchmark_queue_lib import TRACE_FINAL25_BENCHMARK_CATEGORIES


@dataclass(frozen=True)
class Final25Contract:
    key: str
    output_type: str
    extraction: str
    scoring: str
    judge_role: str
    runner: str


CONTRACTS: tuple[Final25Contract, ...] = (
    Final25Contract(
        "chartmuseum",
        "short/free-form answer",
        "preserve response; unwrap <answer> when present",
        "Qwen3-32B semantic correctness against reference",
        "scoring",
        "run_external_benchmark_score_queue.py:chartmuseum_local_judge",
    ),
    Final25Contract(
        "chartqapro",
        "short answer after reasoning",
        "Qwen3-32B final-answer extraction",
        "ChartQAPro official/local normalized scorer",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
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
        "deterministic <answer>/boxed/JSON/final-answer wrapper parser",
        "official FinTabNetQA, VTabFact, VWTQ, and VWTQ-Syn scorers",
        "none",
        "run_external_benchmark_score_queue.py:tablevqabench_local_score",
    ),
    Final25Contract(
        "evochart",
        "short/free-form chart answer",
        "Qwen3-32B extracts final answer while judging",
        "Qwen3-32B semantic correctness with numeric-format tolerance",
        "both",
        "run_external_benchmark_score_queue.py:evochart_local_judge",
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
        "Qwen3-32B selected-option extraction",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "phyx_mini_mc",
        "MCQ option",
        "Qwen3-32B selected-option extraction with fixed A-D contract",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "physics",
        "free-form physics answer",
        "Qwen3-32B extracts answer while judging",
        "strict Qwen3-32B semantic correctness decision",
        "both",
        "run_llm_extracted_benchmark_score_queue.py:judge_binary",
    ),
    Final25Contract(
        "mmmu_pro_vision",
        "MCQ option",
        "Qwen3-32B selected-option extraction",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "mmstar",
        "MCQ option",
        "Qwen3-32B selected-option extraction with fixed A-D contract",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "screenspot",
        "GUI click point",
        "deterministic named/positional pyautogui or coordinate-pair parser",
        "official point-inside-target-box accuracy",
        "none",
        "run_external_benchmark_score_queue.py:screenspot",
    ),
    Final25Contract(
        "spatialvizbench_cot",
        "MCQ option",
        "Qwen3-32B selected-option extraction",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "cvbench_3d",
        "MCQ option",
        "Qwen3-32B selected-option extraction",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "erqa",
        "MCQ option",
        "Qwen3-32B selected-option extraction with fixed A-D contract",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "blink",
        "MCQ option",
        "Qwen3-32B selected-option extraction",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "countbenchqa",
        "integer count",
        "Qwen3-32B final integer extraction",
        "normalized exact integer match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "countqa",
        "integer count",
        "Qwen3-32B final integer extraction",
        "normalized exact integer match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "treebench",
        "MCQ option",
        "Qwen3-32B selected-option extraction using source option labels",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "puzzlevqa",
        "MCQ option or option value",
        "Qwen3-32B extraction and option-value-to-letter mapping",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "visualpuzzles",
        "MCQ option",
        "Qwen3-32B selected-option extraction with fixed A-D contract",
        "exact option-letter match",
        "extraction",
        "run_llm_extracted_benchmark_score_queue.py",
    ),
    Final25Contract(
        "logicvista",
        "one or more MCQ letters",
        "Qwen3-32B option-set extraction",
        "official exact normalized option-set comparison",
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


CONTRACT_BY_KEY = {contract.key: contract for contract in CONTRACTS}
CATEGORY_BY_KEY = {
    key: category
    for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items()
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
    "screenspot",
    "logicvista",
)
LLM_EXTRACT_SCORE_KEYS = (
    "chartqapro",
    "wemath",
    "phyx_mini_mc",
    "physics",
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
DEDICATED_SCORE_KEYS = ("mme_reasoning",)

# These routes require the actual choice text, not merely a guessed range of
# option letters. A row is invalid when its parsed choices omit the ground
# truth or, for fixed contracts, any expected option. TreeBench labels are
# source-derived because its image-embedded OCR questions include both A-C and
# A-D rows.
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
    "visualpuzzles",
)
