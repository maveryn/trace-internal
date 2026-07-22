#!/usr/bin/env python3
"""Build validated Trace paper result assets from canonical score records."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import seaborn as sns  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
PAPER_ROOT = REPO_ROOT / "paper" / "trace"

SOURCE_SPECS = {
    "suite": (
        REPO_ROOT / "evaluation" / "trace_eval" / "suite.v1.json",
        "b84262bcd2243d1d2879b2e02d9b49b17052659ea767df3d7303758f4d63de71",
    ),
    "scores_3b": (
        REPO_ROOT
        / "results"
        / "trace_eval_v1_temp06_seed42_43_44_qwen25vl3b_base_trace_step500_20260716_scores.json",
        "3a7acbf1d9baf3f32fe7ba7b4e522cc713a648fecf438eeae0319b013d8efda7",
    ),
    "scores_7b": (
        REPO_ROOT
        / "results"
        / "canonical"
        / "trace_eval_v1"
        / "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1"
        / "metadata"
        / "results"
        / "benchmark_scores.json",
        "578e574d68702af0b83a9c1962bd73c36f8887787cc9ac10a8f7da3d207c10ac",
    ),
    "scores_rl_baselines": (
        REPO_ROOT
        / "results"
        / "trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717_scores.json",
        "7af92decffc261ad70bd2925632a4aeb3aa61a14cbc5974d285a264a32082c85",
    ),
    "training_runs": (
        PAPER_ROOT / "data" / "training_runs.json",
        None,
    ),
}

TEXT_SOURCE_SPECS = {
    "iid_validation_report": (
        REPO_ROOT / "results" / "trace_validation_iid2000_seed42_8models_20260718_results.md",
        "2ecfdd69b26f81fde09a234ea2f7e2424046984808c9a284f770a7494823747f",
    ),
}

EXPECTED_RUN_MODELS = {
    "qwen2.5-vl-3b-comparison-temp06-seeds42-44-v1": {
        "qwen2.5-vl-3b-base",
        "trace-qwen2.5-vl-3b",
    },
    "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1": {
        "qwen2.5-vl-7b-base",
        "trace-qwen2.5-vl-7b",
        "vero-qwen2.5-vl-7b",
    },
    "qwen2.5-vl-7b-rl-baselines-temp06-seeds42-44-v1": {
        "game-rl-qwen2.5-vl-7b",
        "sphinx-qwen2.5-vl-7b",
        "pcgrpo-qwen2.5-vl-7b",
    },
}

MODEL_LABELS = {
    "qwen2.5-vl-3b-base": "Qwen2.5-VL-3B (base)",
    "trace-qwen2.5-vl-3b": "Trace-3B",
    "qwen2.5-vl-7b-base": "Qwen2.5-VL-7B (base)",
    "game-rl-qwen2.5-vl-7b": "Game-RL-7B",
    "sphinx-qwen2.5-vl-7b": "Sphinx-7B",
    "pcgrpo-qwen2.5-vl-7b": "PC-GRPO-7B",
    "vero-qwen2.5-vl-7b": "Vero-7B",
    "trace-qwen2.5-vl-7b": "Trace-7B",
}

MODEL_ORDER = (
    "qwen2.5-vl-3b-base",
    "trace-qwen2.5-vl-3b",
    "qwen2.5-vl-7b-base",
    "game-rl-qwen2.5-vl-7b",
    "sphinx-qwen2.5-vl-7b",
    "pcgrpo-qwen2.5-vl-7b",
    "vero-qwen2.5-vl-7b",
    "trace-qwen2.5-vl-7b",
)

RESULT_TABLE_7B_ORDER = (
    "qwen2.5-vl-7b-base",
    "trace-qwen2.5-vl-7b",
    "game-rl-qwen2.5-vl-7b",
    "sphinx-qwen2.5-vl-7b",
    "pcgrpo-qwen2.5-vl-7b",
    "vero-qwen2.5-vl-7b",
)

RESULT_TABLE_7B_PRIMARY_ORDER = (
    "qwen2.5-vl-7b-base",
    "trace-qwen2.5-vl-7b",
    "game-rl-qwen2.5-vl-7b",
    "sphinx-qwen2.5-vl-7b",
    "pcgrpo-qwen2.5-vl-7b",
)

RESULT_TABLE_3B_ORDER = (
    "qwen2.5-vl-3b-base",
    "trace-qwen2.5-vl-3b",
)

CATEGORY_TABLE_STYLES = {
    "Charts & Tables": "TraceChartsBand",
    "Visual Math": "TraceMathBand",
    "Science & General": "TraceScienceBand",
    "Spatial Reasoning": "TraceSpatialBand",
    "Perception & Counting": "TracePerceptionBand",
    "Puzzles & Logic": "TracePuzzlesBand",
}

CATEGORY_PLOT_COLORS = {
    "Charts & Tables": "#3C7892",
    "Visual Math": "#6F68A8",
    "Science & General": "#2F8F78",
    "Spatial Reasoning": "#6F9848",
    "Perception & Counting": "#976EA6",
    "Puzzles & Logic": "#66788A",
}

PLOT_INK = "#1F2937"
PLOT_MUTED = "#667085"
PLOT_GRID = "#E4E7EC"
PLOT_REFERENCE = "#98A2B3"

PAPER_SCORE_LABELS = {
    "chartqapro": "benchmark-defined answer accuracy",
    "charxivreason": "Qwen3-32B rubric score",
    "tablevqabench": "aggregate score over four table-reasoning subsets",
    "evochart": "deterministic normalized-answer accuracy",
    "mathvision": "normalized-answer accuracy",
    "mathvista": "normalized-answer accuracy",
    "mathverse": "official answer score with strict judging for unresolved responses",
    "wemath": "strict answer accuracy",
    "phyx_mini_mc": "normalized multiple-choice accuracy",
    "mmmu_pro_vision": "benchmark-defined score",
    "realworldqa": "benchmark-defined score",
    "mmstar": "benchmark-defined score",
    "embspatial": "benchmark-defined score",
    "spatialvizbench_cot": "benchmark-defined score",
    "cvbench_3d": "benchmark-defined score",
    "erqa": "EASI ERQABench score",
    "blink": "benchmark-defined score",
    "countbenchqa": "benchmark-defined score",
    "countqa": "benchmark-defined score",
    "treebench": "dimension accuracy",
    "puzzlevqa": "benchmark-defined score",
    "visualpuzzles": "benchmark-defined score",
    "logicvista": "normalized option-set accuracy",
    "mme_reasoning": "official score with model judging for open-answer items",
}

PAPER_BENCHMARK_DISPLAY_NAMES = {
    "spatialvizbench_cot": "SpatialVizBench",
}

PAPER_BENCHMARK_CITATIONS = {
    "chartqapro": "masry2025chartqapro",
    "charxivreason": "wang2024charxiv",
    "tablevqabench": "kim2024tablevqabench",
    "evochart": "huang2025evochart",
    "mathvision": "wang2024mathvision",
    "mathvista": "lu2024mathvista",
    "mathverse": "zhang2024mathverse",
    "wemath": "qiao2025wemath",
    "phyx_mini_mc": "shen2025phyx",
    "mmmu_pro_vision": "yue2025mmmupro",
    "realworldqa": "xai2024realworldqa",
    "mmstar": "chen2024mmstar",
    "embspatial": "du2024embspatial",
    "spatialvizbench_cot": "wang2026spatialviz",
    "cvbench_3d": "tong2024cambrian",
    "erqa": "deepmind2025erqa",
    "blink": "fu2024blink",
    "countbenchqa": "paiss2023countbench",
    "countqa": "tamarapalli2025countqa",
    "treebench": "wang2026treebench",
    "puzzlevqa": "chia2024puzzlevqa",
    "visualpuzzles": "song2025visualpuzzles",
    "logicvista": "xiao2024logicvista",
    "mme_reasoning": "yuan2025mmereasoning",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    loaded: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    for name, (path, expected_sha) in SOURCE_SPECS.items():
        if not path.exists():
            raise FileNotFoundError(f"missing result source: {path}")
        actual_sha = _sha256(path)
        if expected_sha is not None and actual_sha != expected_sha:
            raise RuntimeError(
                f"canonical source changed for {path}: expected {expected_sha}, got {actual_sha}"
            )
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
        provenance[name] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": actual_sha,
        }
    return loaded, provenance


def _load_text_sources() -> tuple[dict[str, str], dict[str, Any]]:
    loaded: dict[str, str] = {}
    provenance: dict[str, Any] = {}
    for name, (path, expected_sha) in TEXT_SOURCE_SPECS.items():
        if not path.exists():
            raise FileNotFoundError(f"missing result source: {path}")
        actual_sha = _sha256(path)
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"canonical source changed for {path}: expected {expected_sha}, got {actual_sha}"
            )
        loaded[name] = path.read_text(encoding="utf-8")
        provenance[name] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": actual_sha,
        }
    return loaded, provenance


def _markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _percent_value(cell: str) -> float:
    normalized = cell.replace("**", "").replace("%", "").strip()
    return float(normalized.split("+/-", maxsplit=1)[0].strip())


def _parse_iid_validation_report(text: str) -> dict[str, Any]:
    labels = {
        "Qwen2.5-VL-3B Base": "qwen2.5-vl-3b-base",
        "TRACE Qwen2.5-VL-3B": "trace-qwen2.5-vl-3b",
        "Qwen2.5-VL-7B Base": "qwen2.5-vl-7b-base",
        "TRACE Qwen2.5-VL-7B": "trace-qwen2.5-vl-7b",
    }
    scores: dict[str, float] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = _markdown_cells(line)
        if len(cells) >= 2 and cells[0] in labels and "%" in cells[1]:
            scores[labels[cells[0]]] = _percent_value(cells[1])
    if set(scores) != set(labels.values()):
        raise RuntimeError("IID validation report is missing a matched Base/Trace score")
    return {
        "rows": 2000,
        "samples_per_task": 2,
        "task_count": 1000,
        "seed": 42,
        "metric": "combined_semantic_accuracy",
        "scores": scores,
    }


def _validate_suite(suite: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    if suite.get("schema_version") != "trace-eval-suite-v1":
        raise RuntimeError("unexpected evaluation-suite schema")
    if suite.get("suite_id") != "trace_eval_v1":
        raise RuntimeError("paper results require trace_eval_v1")
    benchmarks = list(suite.get("benchmarks", []))
    categories = dict(suite.get("categories", {}))
    if len(benchmarks) != 24 or len(categories) != 6:
        raise RuntimeError("trace_eval_v1 must contain 24 benchmarks in six categories")
    keys = [str(item["key"]) for item in benchmarks]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate benchmark key in suite")
    categorized = [key for values in categories.values() for key in values]
    if len(categorized) != 24 or set(categorized) != set(keys):
        raise RuntimeError("suite categories do not partition the benchmark list")
    if sum(int(item["rows"]) for item in benchmarks) != 32805:
        raise RuntimeError("unexpected total evaluated rows in trace_eval_v1")
    return benchmarks, list(categories)


def _validate_result(
    payload: Mapping[str, Any],
    benchmark_keys: set[str],
    category_names: set[str],
) -> None:
    run_id = str(payload.get("run_id"))
    if payload.get("schema_version") != "trace_eval_results_v1":
        raise RuntimeError(f"unexpected result schema for {run_id}")
    if payload.get("suite_id") != "trace_eval_v1":
        raise RuntimeError(f"unexpected suite for {run_id}")
    if payload.get("score_unit") != "percent":
        raise RuntimeError(f"unexpected score unit for {run_id}")
    if payload.get("aggregation") != "unweighted_macro_mean":
        raise RuntimeError(f"unexpected aggregation for {run_id}")
    expected_models = EXPECTED_RUN_MODELS.get(run_id)
    if expected_models is None:
        raise RuntimeError(f"unrecognized canonical run: {run_id}")
    summary_models = {str(row["model_id"]) for row in payload["overall_summaries"]}
    if summary_models != expected_models:
        raise RuntimeError(f"model-set drift for {run_id}: {sorted(summary_models)}")
    expected_seed_rows = len(expected_models) * 3
    if len(payload["overall_scores"]) != expected_seed_rows:
        raise RuntimeError(f"unexpected overall seed rows for {run_id}")
    for model_id in expected_models:
        seeds = {
            int(row["seed"])
            for row in payload["overall_scores"]
            if row["model_id"] == model_id
        }
        if seeds != {42, 43, 44}:
            raise RuntimeError(f"seed drift for {model_id}: {sorted(seeds)}")
        model_benchmarks = {
            str(row["benchmark_id"])
            for row in payload["benchmark_summaries"]
            if row["model_id"] == model_id
        }
        if model_benchmarks != benchmark_keys:
            raise RuntimeError(f"benchmark drift for {model_id}")
        model_categories = {
            str(row["category_name"])
            for row in payload["category_summaries"]
            if row["model_id"] == model_id
        }
        if model_categories != category_names:
            raise RuntimeError(f"category drift for {model_id}")
    for row in payload["benchmark_summaries"]:
        if int(row["seed_count"]) != 3:
            raise RuntimeError(f"non-three-seed benchmark summary in {run_id}")
    for row in payload["category_summaries"] + payload["overall_summaries"]:
        if int(row["seed_count"]) != 3:
            raise RuntimeError(f"non-three-seed aggregate in {run_id}")


def _validate_training(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != "trace_paper_training_runs_v1":
        raise RuntimeError("unexpected paper training-run schema")
    data = payload["data"]
    config = payload["shared_configuration"]
    if (data["active_tasks"], data["train_rows"], data["validation_rows"]) != (
        1000,
        64000,
        2000,
    ):
        raise RuntimeError("paper training-data identity drift")
    required = {
        "algorithm": "grpo",
        "max_steps": 500,
        "prompt_batch_size": 128,
        "rollouts_per_prompt": 8,
        "kl_enabled": False,
        "answer_scoring": "exact_json",
        "answer_reward_weight": 1.0,
        "format_reward_weight": 0.05,
        "effective_answer_coefficient": 0.95,
        "annotation_reward_weight": 0.0,
    }
    for key, value in required.items():
        if config.get(key) != value:
            raise RuntimeError(f"paper training configuration drift: {key}")
    if {row["model_size"] for row in payload["runs"]} != {"3B", "7B"}:
        raise RuntimeError("paper training snapshot must contain 3B and 7B runs")


def _index_summaries(payloads: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        for row in payload["overall_summaries"]:
            model_id = str(row["model_id"])
            if model_id in models:
                raise RuntimeError(f"duplicate model summary: {model_id}")
            models[model_id] = {
                "display_name": MODEL_LABELS[model_id],
                "overall": {
                    "mean": float(row["mean"]),
                    "stddev": float(row["stddev"]),
                    "seed_count": int(row["seed_count"]),
                },
                "categories": {},
                "benchmarks": {},
            }
        for row in payload["category_summaries"]:
            models[str(row["model_id"])]["categories"][str(row["category_name"])] = {
                "mean": float(row["mean"]),
                "stddev": float(row["stddev"]),
            }
        for row in payload["benchmark_summaries"]:
            models[str(row["model_id"])]["benchmarks"][str(row["benchmark_id"])] = {
                "mean": float(row["mean"]),
                "stddev": float(row["stddev"]),
            }
    if set(models) != set(MODEL_ORDER):
        raise RuntimeError(f"combined model-set drift: {sorted(models)}")
    return models


def _comparison(
    models: Mapping[str, Mapping[str, Any]],
    trace_id: str,
    base_id: str,
    categories: Iterable[str],
    benchmarks: Iterable[str],
) -> dict[str, Any]:
    trace = models[trace_id]
    base = models[base_id]
    category_deltas = {
        category: trace["categories"][category]["mean"]
        - base["categories"][category]["mean"]
        for category in categories
    }
    benchmark_deltas = {
        benchmark: trace["benchmarks"][benchmark]["mean"]
        - base["benchmarks"][benchmark]["mean"]
        for benchmark in benchmarks
    }
    return {
        "trace_model_id": trace_id,
        "base_model_id": base_id,
        "overall_delta": trace["overall"]["mean"] - base["overall"]["mean"],
        "category_deltas": category_deltas,
        "benchmark_deltas": benchmark_deltas,
        "positive_benchmark_count": sum(value > 0 for value in benchmark_deltas.values()),
        "negative_benchmark_count": sum(value < 0 for value in benchmark_deltas.values()),
        "zero_benchmark_count": sum(value == 0 for value in benchmark_deltas.values()),
    }


def _fmt_result(
    mean: float,
    stddev: float,
    *,
    bold: bool = False,
    delta: float | None = None,
) -> str:
    if bold:
        score = (
            f"\\textbf{{{mean:.1f}}}"
            f"\\ensuremath{{\\mathord{{\\boldsymbol{{\\pm}}}}}}"
            f"\\textbf{{{stddev:.1f}}}"
        )
    else:
        score = f"{mean:.1f}\\ensuremath{{\\mathord{{\\pm}}}}{stddev:.1f}"
    if delta is not None:
        color = "TraceGain" if delta >= 0 else "TraceLoss"
        score += (
            "\\raisebox{-0.45ex}{"
            f"\\fontsize{{4}}{{4}}\\selectfont\\color{{{color}}}{{{delta:+.1f}}}"
            "}"
        )
    return score


def _latex(text: str) -> str:
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _write_main_table(
    path: Path,
    models: Mapping[str, Mapping[str, Any]],
    benchmarks: list[dict[str, Any]],
    categories: list[str],
) -> None:
    table_models = RESULT_TABLE_7B_ORDER + RESULT_TABLE_3B_ORDER
    trace_bases = {
        "trace-qwen2.5-vl-7b": "qwen2.5-vl-7b-base",
        "trace-qwen2.5-vl-3b": "qwen2.5-vl-3b-base",
    }

    def score_cells(scope: str, key: str | None = None) -> list[str]:
        summaries: dict[str, Mapping[str, Any]] = {}
        for model_id in table_models:
            if scope == "benchmark":
                assert key is not None
                summaries[model_id] = models[model_id]["benchmarks"][key]
            elif scope == "category":
                assert key is not None
                summaries[model_id] = models[model_id]["categories"][key]
            elif scope == "overall":
                summaries[model_id] = models[model_id]["overall"]
            else:
                raise ValueError(f"unsupported result-table scope: {scope}")

        maxima = {
            "7B": max(float(summaries[mid]["mean"]) for mid in RESULT_TABLE_7B_PRIMARY_ORDER),
            "3B": max(float(summaries[mid]["mean"]) for mid in RESULT_TABLE_3B_ORDER),
        }
        cells: list[str] = []
        for model_id in table_models:
            summary = summaries[model_id]
            mean = float(summary["mean"])
            scale = "3B" if model_id in RESULT_TABLE_3B_ORDER else "7B"
            base_id = trace_bases.get(model_id)
            delta = None if base_id is None else mean - float(summaries[base_id]["mean"])
            cells.append(
                _fmt_result(
                    mean,
                    float(summary["stddev"]),
                    bold=math.isclose(mean, maxima[scale]),
                    delta=delta,
                )
            )
        return cells

    lines = [
        "% Generated by paper/trace/scripts/build_results_assets.py. Do not edit.",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\fontsize{7.5}{8.5}\\selectfont",
        "  \\setlength{\\tabcolsep}{0.5pt}",
        "  \\renewcommand{\\arraystretch}{1.04}",
        "  \\caption{Per-benchmark transfer on the 24-benchmark external evaluation suite. Each score reports the mean and sample standard deviation over three decoding seeds, in percent. Smaller green/red subscripts in the \\trace columns give the change from the corresponding base model. Bold marks the best score among the base model and synthetic-data RLVR checkpoints at each model scale. Category and overall averages are unweighted across benchmarks.}",
        "  \\label{tab:main-results}",
        "  \\begin{tabularx}{\\textwidth}{@{}>{\\raggedright\\arraybackslash}p{0.16\\textwidth} *{5}{>{\\centering\\arraybackslash}X}|>{\\centering\\arraybackslash}X|*{2}{>{\\centering\\arraybackslash}X}@{}}",
        "    \\toprule",
        "     & \\multicolumn{5}{c|}{7B base + synthetic RLVR} & \\multicolumn{1}{c|}{Real-image} & \\multicolumn{2}{c}{3B base + synthetic RLVR} \\\\",
        "    \\cmidrule(lr){2-6}\\cmidrule(lr){7-7}\\cmidrule(l){8-9}",
        "    Benchmark & Base & \\trace & Game-RL & Sphinx & PC-GRPO & Vero & Base & \\trace \\\\",
        "    \\midrule",
    ]

    for category_index, category in enumerate(categories):
        if category_index:
            lines.append("    \\specialrule{0.35pt}{0pt}{0pt}")
        band = CATEGORY_TABLE_STYLES[category]
        lines.append(
            f"    \\rowcolor{{{band}}} \\multicolumn{{9}}{{@{{}}l@{{}}}}{{\\textbf{{{_latex(category)}}}}} \\\\"
        )
        for item in benchmarks:
            if str(item["category"]) != category:
                continue
            benchmark_key = str(item["key"])
            display_name = PAPER_BENCHMARK_DISPLAY_NAMES.get(
                benchmark_key,
                str(item["display"]),
            )
            cells = [_latex(display_name)] + score_cells("benchmark", benchmark_key)
            lines.append(f"    \\rowcolor{{{band}}} " + " & ".join(cells) + " \\\\")
        average_cells = ["\\textit{Category average}"] + score_cells("category", category)
        lines.append(f"    \\rowcolor{{{band}}} " + " & ".join(average_cells) + " \\\\")

    lines.extend(
        [
            "    \\specialrule{0.7pt}{1pt}{0pt}",
            "    \\rowcolor{TraceOverallBand} "
            + " & ".join(["\\textbf{Overall average}"] + score_cells("overall"))
            + " \\\\",
        ]
    )
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabularx}",
            "\\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_training_table(path: Path, training: Mapping[str, Any]) -> None:
    config = training["shared_configuration"]
    data = training["data"]
    runtimes = {row["model_size"]: row["runtime_seconds"] / 3600 for row in training["runs"]}
    if not config["full_parameter_training"] or config["vision_tower_frozen"]:
        raise RuntimeError("paper training table assumes full-model training with a trainable vision encoder")
    lines = [
        "% Generated by paper/trace/scripts/build_results_assets.py. Do not edit.",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\small",
        "  \\setlength{\\tabcolsep}{5pt}",
        "  \\caption{RLVR configuration shared across the 3B and 7B runs.}",
        "  \\label{tab:training-configuration}",
        "  \\begin{tabular}{@{}l l@{}}",
        "    \\toprule",
        "    Setting & Value \\\\",
        "    \\midrule",
        f"    Training data & {data['train_rows']:,} prompts; {data['active_tasks']:,} tasks \\\\",
        f"    Image pixel cap & {data['embedded_image_pixel_cap']:,} per image \\\\",
        f"    Updates & {config['max_steps']}; one shuffled data pass \\\\",
        f"    Validation & {data['validation_rows']:,} instances every {config['validation_interval_steps']} updates \\\\",
        f"    Prompt batch / rollouts & {config['prompt_batch_size']} / {config['rollouts_per_prompt']} \\\\",
        f"    Sampled responses & {config['sampled_training_responses']:,} \\\\",
        f"    Prompt / response caps & {config['prompt_token_cap']:,} / {config['response_token_cap']:,} tokens \\\\",
        f"    Optimization scope & Full model; vision encoder trainable; {str(config['precision']).upper()} \\\\",
        f"    Actor optimizer & AdamW; LR $10^{{-6}}$; weight decay {config['actor_weight_decay']:.2f} \\\\",
        f"    Policy epochs & {config['policy_epochs']} \\\\",
        f"    Policy clipping & {config['clip_ratio_low']:.1f} lower; {config['clip_ratio_high']:.1f} upper; dual {config['dual_clip_bound']:.1f} \\\\",
        f"    Rollout sampling & temperature {config['training_temperature']:.1f}; top-$p$ {config['training_top_p']:.1f} \\\\",
        f"    Reward & {1.0 - config['format_reward_weight']:.2f} exact answer $+$ {config['format_reward_weight']:.2f} JSON format \\\\",
        f"    Hardware & {config['hardware']['gpu_count']} $\\times$ H100 80GB \\\\",
        f"    Runtime & {runtimes['3B']:.1f} h (3B); {runtimes['7B']:.1f} h (7B) \\\\",
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_suite_table(path: Path, benchmarks: list[dict[str, Any]]) -> None:
    lines = [
        "% Generated by paper/trace/scripts/build_results_assets.py. Do not edit.",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\scriptsize",
        "  \\setlength{\\tabcolsep}{4pt}",
        "  \\caption{External evaluation suite. Each model and decoding seed is scored on 32,805 examples.}",
        "  \\label{tab:evaluation-suite}",
        "  \\begin{tabular}{@{}p{0.30\\textwidth} p{0.38\\textwidth} c@{}}",
        "    \\toprule",
        "    Category & Benchmark & Rows \\\\",
        "    \\midrule",
    ]
    previous = None
    for item in benchmarks:
        category = str(item["category"])
        if previous is not None and category != previous:
            lines.append("    \\midrule")
        category_cell = _latex(category) if category != previous else ""
        benchmark_key = str(item["key"])
        display_name = PAPER_BENCHMARK_DISPLAY_NAMES.get(
            benchmark_key,
            str(item["display"]),
        )
        citation_key = PAPER_BENCHMARK_CITATIONS.get(benchmark_key)
        if citation_key is None:
            raise RuntimeError(f"missing paper citation for benchmark {benchmark_key}")
        benchmark_cell = f"{_latex(display_name)}~\\citep{{{citation_key}}}"
        lines.append(
            f"    {category_cell} & {benchmark_cell} & {int(item['rows']):,} \\\\"
        )
        previous = category
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_scale_gain_figure(
    path: Path,
    comparisons: Mapping[str, Mapping[str, Any]],
    benchmarks: list[dict[str, Any]],
    categories: list[str],
) -> dict[str, Any]:
    """Plot benchmark-level gains at 3B against gains at 7B."""

    gains_3b = comparisons["3B"]["benchmark_deltas"]
    gains_7b = comparisons["7B"]["benchmark_deltas"]
    keys = [str(item["key"]) for item in benchmarks]
    x = np.asarray([float(gains_3b[key]) for key in keys], dtype=float)
    y = np.asarray([float(gains_7b[key]) for key in keys], dtype=float)
    correlation = spearmanr(x, y)
    rho = float(correlation.statistic)
    pvalue = float(correlation.pvalue)
    if not math.isfinite(rho) or not math.isfinite(pvalue):
        raise RuntimeError("non-finite cross-scale gain correlation")

    benchmark_categories = [str(item["category"]) for item in benchmarks]
    display_names = {
        str(item["key"]): PAPER_BENCHMARK_DISPLAY_NAMES.get(
            str(item["key"]), str(item["display"])
        )
        for item in benchmarks
    }

    rc = {
        "font.family": "DejaVu Sans",
        "font.size": 8.0,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.0,
        "axes.edgecolor": PLOT_REFERENCE,
        "axes.labelcolor": PLOT_INK,
        "xtick.color": PLOT_MUTED,
        "ytick.color": PLOT_MUTED,
        "text.color": PLOT_INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
    with plt.rc_context(rc), sns.axes_style(
        "whitegrid", rc={"grid.color": PLOT_GRID}
    ), sns.plotting_context("paper", rc=rc):
        fig, ax = plt.subplots(figsize=(6.5, 3.55))
        for category in categories:
            indices = [
                index
                for index, value in enumerate(benchmark_categories)
                if value == category
            ]
            sns.scatterplot(
                x=x[indices],
                y=y[indices],
                s=50,
                color=CATEGORY_PLOT_COLORS[category],
                edgecolor="white",
                linewidth=0.65,
                label=category,
                ax=ax,
                zorder=3,
            )

        lower = -2.5
        upper = 12.0
        ax.axhline(0, color=PLOT_REFERENCE, linewidth=0.8, linestyle="--", zorder=1)
        ax.axvline(0, color=PLOT_REFERENCE, linewidth=0.8, linestyle="--", zorder=1)
        ax.plot(
            [lower, upper],
            [lower, upper],
            color=PLOT_REFERENCE,
            linewidth=0.9,
            linestyle=":",
            zorder=1,
        )
        ax.set_xlim(lower, upper)
        ax.set_ylim(lower, upper)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("3B improvement over base (points)")
        ax.set_ylabel("7B improvement over base (points)")
        ax.text(
            0.04,
            0.95,
            rf"Spearman $\rho_s={rho:.2f}$",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color=PLOT_INK,
        )

        annotation_positions = {
            "evochart": ((6, 0), "left"),
            "chartqapro": ((-6, 30), "right"),
            "treebench": ((-6, -16), "right"),
        }
        for key, (offset, horizontal_alignment) in annotation_positions.items():
            index = keys.index(key)
            ax.annotate(
                display_names[key],
                (x[index], y[index]),
                xytext=offset,
                textcoords="offset points",
                fontsize=7,
                color=PLOT_INK,
                ha=horizontal_alignment,
                va="center",
                arrowprops=(
                    None
                    if key == "evochart"
                    else {
                        "arrowstyle": "-",
                        "color": PLOT_MUTED,
                        "linewidth": 0.55,
                        "shrinkA": 2,
                        "shrinkB": 2,
                    }
                ),
            )

        ax.legend(
            title="Benchmark group",
            frameon=False,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0,
            handletextpad=0.4,
        )
        sns.despine(ax=ax)
        fig.tight_layout()
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            path,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0.02,
            metadata={"CreationDate": None, "ModDate": None, "Creator": "Trace"},
        )
        plt.close(fig)

    return {
        "benchmark_count": len(keys),
        "spearman_rho": rho,
        "spearman_pvalue": pvalue,
        "source_values": "benchmark mean improvement over the corresponding base model",
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    loaded, source_provenance = _load_sources()
    text_sources, text_provenance = _load_text_sources()
    loaded.update(text_sources)
    source_provenance.update(text_provenance)
    benchmarks, categories = _validate_suite(loaded["suite"])
    benchmark_keys = {str(item["key"]) for item in benchmarks}
    category_names = set(categories)
    result_payloads = [loaded["scores_3b"], loaded["scores_7b"], loaded["scores_rl_baselines"]]
    for payload in result_payloads:
        _validate_result(payload, benchmark_keys, category_names)
    _validate_training(loaded["training_runs"])
    models = _index_summaries(result_payloads)
    iid_validation = _parse_iid_validation_report(loaded["iid_validation_report"])
    comparisons = {
        "3B": _comparison(
            models,
            "trace-qwen2.5-vl-3b",
            "qwen2.5-vl-3b-base",
            categories,
            [item["key"] for item in benchmarks],
        ),
        "7B": _comparison(
            models,
            "trace-qwen2.5-vl-7b",
            "qwen2.5-vl-7b-base",
            categories,
            [item["key"] for item in benchmarks],
        ),
    }
    comparisons["7B"]["contextual_overall_deltas"] = {
        model_id: models["trace-qwen2.5-vl-7b"]["overall"]["mean"]
        - models[model_id]["overall"]["mean"]
        for model_id in (
            "game-rl-qwen2.5-vl-7b",
            "sphinx-qwen2.5-vl-7b",
            "pcgrpo-qwen2.5-vl-7b",
            "vero-qwen2.5-vl-7b",
        )
    }

    data_dir = PAPER_ROOT / "data"
    table_dir = PAPER_ROOT / "tables"
    provenance_dir = PAPER_ROOT / "provenance"
    for directory in (data_dir, table_dir, provenance_dir):
        directory.mkdir(parents=True, exist_ok=True)

    scale_gain_figure = PAPER_ROOT / "figures" / "scale_gain_correlation.pdf"
    scale_gain_consistency = _write_scale_gain_figure(
        scale_gain_figure,
        comparisons,
        benchmarks,
        categories,
    )

    combined_path = data_dir / "trace_eval_v1_paper_results.json"
    _write_json(
        combined_path,
        {
            "schema_version": "trace_paper_results_v1",
            "suite": {
                "suite_id": loaded["suite"]["suite_id"],
                "benchmark_count": len(benchmarks),
                "category_count": len(categories),
                "rows_per_model_seed": sum(int(item["rows"]) for item in benchmarks),
                "categories": categories,
                "seeds": [42, 43, 44],
                "aggregation": loaded["suite"]["aggregation"],
                "generation": loaded["suite"]["generation"],
                "vlmevalkit": loaded["suite"]["vlmevalkit"],
            },
            "models": {model_id: models[model_id] for model_id in MODEL_ORDER},
            "comparisons": comparisons,
            "scale_gain_consistency": scale_gain_consistency,
            "iid_validation": iid_validation,
            "training": loaded["training_runs"],
            "sources": source_provenance,
        },
    )

    outputs = [combined_path, scale_gain_figure]
    main_table = table_dir / "main_results.tex"
    training_table = table_dir / "training_configuration.tex"
    suite_table = table_dir / "evaluation_suite.tex"
    _write_main_table(main_table, models, benchmarks, categories)
    _write_training_table(training_table, loaded["training_runs"])
    _write_suite_table(suite_table, benchmarks)
    outputs.extend([main_table, training_table, suite_table])

    generator_path = Path(__file__).resolve()
    provenance_path = provenance_dir / "results_assets.json"
    _write_json(
        provenance_path,
        {
            "schema_version": "trace_paper_result_assets_v1",
            "generator": {
                "path": str(generator_path.relative_to(REPO_ROOT)),
                "sha256": _sha256(generator_path),
            },
            "sources": source_provenance,
            "outputs": {
                str(path.relative_to(REPO_ROOT)): {
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
                for path in outputs
            },
        },
    )
    print(f"wrote {combined_path.relative_to(REPO_ROOT)}")
    for path in outputs[1:]:
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    print(f"wrote {provenance_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
