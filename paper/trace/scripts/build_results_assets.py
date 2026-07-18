#!/usr/bin/env python3
"""Build validated Trace paper result assets from canonical score records."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


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
    "pcgrpo-qwen2.5-vl-7b": "PCGRPO-7B",
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
            "\\raisebox{-0.35ex}{"
            f"\\fontsize{{5}}{{5}}\\selectfont\\color{{{color}}}{{{delta:+.1f}}}"
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
            "7B": max(float(summaries[mid]["mean"]) for mid in RESULT_TABLE_7B_ORDER),
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
        "\\begin{table*}[t]",
        "  \\centering",
        "  \\fontsize{6}{7}\\selectfont",
        "  \\setlength{\\tabcolsep}{2.5pt}",
        "  \\renewcommand{\\arraystretch}{1.04}",
        "  \\caption{Per-benchmark transfer on the 24-benchmark \\texttt{trace\\_eval\\_v1} suite. Each score reports the mean and sample standard deviation over decoding seeds 42--44, in percent. Smaller green/red subscripts in the Trace columns give the change from the corresponding base model. Bold marks the best result within each model scale. Category and overall averages are unweighted across benchmarks. External 7B checkpoints use the same evaluation protocol but are not training-compute matched.}",
        "  \\label{tab:main-results}",
        "  \\begin{tabular}{@{}l *{6}{c} !{\\hspace{2pt}\\vrule width 0.45pt\\hspace{2pt}} *{2}{c}@{}}",
        "    \\toprule",
        "     & \\multicolumn{6}{c}{7B checkpoints} & \\multicolumn{2}{c}{3B checkpoints} \\\\",
        "    \\cmidrule(lr){2-7}\\cmidrule(l){8-9}",
        "    Benchmark & Base & Trace & Game-RL & Sphinx & PCGRPO & Vero & Base & Trace \\\\",
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
            cells = [_latex(str(item["display"]))] + score_cells("benchmark", str(item["key"]))
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
            "  \\end{tabular}",
            "\\end{table*}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_training_table(path: Path, training: Mapping[str, Any]) -> None:
    config = training["shared_configuration"]
    data = training["data"]
    runtimes = {row["model_size"]: row["runtime_seconds"] / 3600 for row in training["runs"]}
    lines = [
        "% Generated by paper/trace/scripts/build_results_assets.py. Do not edit.",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\small",
        "  \\setlength{\\tabcolsep}{5pt}",
        "  \\caption{Shared answer-only RLVR configuration for Trace-3B and Trace-7B.}",
        "  \\label{tab:training-configuration}",
        "  \\begin{tabular}{@{}l l@{}}",
        "    \\toprule",
        "    Setting & Value \\\\",
        "    \\midrule",
        f"    Training data & {data['train_rows']:,} prompts; {data['active_tasks']:,} tasks \\\\",
        f"    Updates & {config['max_steps']}; one shuffled data pass \\\\",
        f"    Prompt batch / rollouts & {config['prompt_batch_size']} / {config['rollouts_per_prompt']} \\\\",
        f"    Sampled responses & {config['sampled_training_responses']:,} \\\\",
        f"    Actor optimizer & AdamW, LR $10^{{-6}}$, no warmup \\\\",
        f"    Reward & {1.0 - config['format_reward_weight']:.2f} exact answer $+$ {config['format_reward_weight']:.2f} JSON format \\\\",
        "    KL penalty & disabled \\\\",
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
        "\\begin{table*}[t]",
        "  \\centering",
        "  \\scriptsize",
        "  \\setlength{\\tabcolsep}{4pt}",
        "  \\caption{External evaluation suite. Each model and decoding seed is scored on 32,805 examples.}",
        "  \\label{tab:evaluation-suite}",
        "  \\begin{tabular}{@{}p{0.17\\textwidth} p{0.16\\textwidth} r p{0.50\\textwidth}@{}}",
        "    \\toprule",
        "    Category & Benchmark & Rows & Scoring contract \\\\",
        "    \\midrule",
    ]
    previous = None
    for item in benchmarks:
        category = str(item["category"])
        if previous is not None and category != previous:
            lines.append("    \\addlinespace[2pt]")
        category_cell = _latex(category) if category != previous else ""
        score_contract = _latex(str(item["score_contract"]))
        lines.append(
            f"    {category_cell} & {_latex(str(item['display']))} & {int(item['rows']):,} & {score_contract} \\\\"
        )
        previous = category
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table*}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    loaded, source_provenance = _load_sources()
    benchmarks, categories = _validate_suite(loaded["suite"])
    benchmark_keys = {str(item["key"]) for item in benchmarks}
    category_names = set(categories)
    result_payloads = [loaded["scores_3b"], loaded["scores_7b"], loaded["scores_rl_baselines"]]
    for payload in result_payloads:
        _validate_result(payload, benchmark_keys, category_names)
    _validate_training(loaded["training_runs"])
    models = _index_summaries(result_payloads)
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
            "training": loaded["training_runs"],
            "sources": source_provenance,
        },
    )

    outputs = [combined_path]
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
