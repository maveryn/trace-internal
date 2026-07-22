#!/usr/bin/env python3
"""Build taxonomy-conditioned Trace IID validation analyses and figure."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from huggingface_hub import HfApi, hf_hub_download  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
PAPER_ROOT = REPO_ROOT / "paper" / "trace"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trace.core.reasoning_operations import (  # noqa: E402
    REASONING_OPERATION_KEYS,
    REASONING_OPERATION_LABELS,
    REASONING_OPERATION_SCHEMA_VERSION,
)
from trace.tasks.registry import create_task, task_reasoning_operations  # noqa: E402


EVAL_REPO_ID = "maveryn/trace-eval-runs"
EVAL_REVISION = "cf0d14aed86db2661d397ce8b68b36171873478d"
EVAL_RUN_ID = "trace-iid-validation-2000-answer-seed42-8models-v1"
EVAL_BENCHMARK_ID = "trace_validation_iid2000"
SOURCE_REPO_ID = "maveryn/trace"
SOURCE_REVISION = "e317b746b258630682367cc6a9d87dedd195113c"
SOURCE_PARQUET = "data/validation/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet"

MODELS = {
    "3B": {
        "base": "qwen2.5-vl-3b-base",
        "trace": "trace-qwen2.5-vl-3b",
    },
    "7B": {
        "base": "qwen2.5-vl-7b-base",
        "trace": "trace-qwen2.5-vl-7b",
    },
}
EXPECTED_ROWS = 2_000
EXPECTED_TASKS = 1_000

DOMAIN_LABELS = {
    "charts": "Charts",
    "games": "Games",
    "geometry": "Geometry",
    "graph": "Graph",
    "icons": "Icons",
    "illustrations": "Illustrations",
    "pages": "Pages",
    "physics": "Physics",
    "puzzles": "Puzzles",
    "symbolic": "Symbolic",
    "three_d": "3D",
}
ANSWER_LABELS = {
    "integer": "Integer",
    "number": "Numeric",
    "option_letter": "Option letter",
    "string": "String",
}

PLOT_INK = "#1F2937"
PLOT_MUTED = "#667085"
PLOT_GRID = "#E4E7EC"
PLOT_REFERENCE = "#98A2B3"
SCALE_STYLES = {
    "3B": {"color": "#2A6FB5", "marker": "o"},
    "7B": {"color": "#D9772F", "marker": "D"},
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    parser.add_argument("--bootstrap-chunk-size", type=int, default=512)
    parser.add_argument(
        "--token-file",
        type=Path,
        default=REPO_ROOT / "hf-token.txt",
        help="Optional Hugging Face token file; never recorded in provenance.",
    )
    parser.add_argument(
        "--output-data",
        type=Path,
        default=PAPER_ROOT / "data" / "iid_taxonomy_analysis.json",
    )
    parser.add_argument(
        "--output-figure",
        type=Path,
        default=PAPER_ROOT / "figures" / "iid_taxonomy_gains.pdf",
    )
    parser.add_argument(
        "--output-table",
        type=Path,
        default=PAPER_ROOT / "tables" / "iid_slice_results.tex",
    )
    parser.add_argument(
        "--output-provenance",
        type=Path,
        default=PAPER_ROOT / "provenance" / "iid_taxonomy_analysis.json",
    )
    args = parser.parse_args()
    if args.bootstrap_replicates < 1_000:
        parser.error("--bootstrap-replicates must be at least 1000")
    if args.bootstrap_chunk_size < 1:
        parser.error("--bootstrap-chunk-size must be positive")
    return args


def _token(token_file: Path) -> str | None:
    environment_token = os.environ.get("HF_TOKEN")
    if environment_token:
        return environment_token.strip()
    if token_file.is_file():
        return token_file.read_text(encoding="utf-8").strip()
    return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def _score_paths(token: str | None) -> dict[str, str]:
    files = HfApi(token=token).list_repo_files(
        repo_id=EVAL_REPO_ID,
        repo_type="dataset",
        revision=EVAL_REVISION,
    )
    expected_models = {
        str(model_id)
        for scale_models in MODELS.values()
        for model_id in scale_models.values()
    }
    prefix = f"runs/{EVAL_RUN_ID}/data/scores/"
    selected: dict[str, str] = {}
    for path in files:
        if not path.startswith(prefix) or not path.endswith(".parquet"):
            continue
        fields: dict[str, str] = {}
        for component in Path(path).parts:
            if "=" in component:
                key, value = component.split("=", maxsplit=1)
                fields[key] = value
        model_id = fields.get("model")
        if (
            model_id in expected_models
            and fields.get("seed") == "42"
            and fields.get("benchmark") == EVAL_BENCHMARK_ID
        ):
            if model_id in selected:
                raise RuntimeError(f"duplicate IID score part for {model_id}")
            selected[model_id] = path
    if set(selected) != expected_models:
        raise RuntimeError(
            f"IID score inventory drift: expected {sorted(expected_models)}, found {sorted(selected)}"
        )
    return selected


def _download_inputs(token: str | None) -> tuple[Path, dict[str, Path]]:
    source_path = Path(
        hf_hub_download(
            repo_id=SOURCE_REPO_ID,
            repo_type="dataset",
            revision=SOURCE_REVISION,
            filename=SOURCE_PARQUET,
            token=token,
        )
    )
    score_paths = {
        model_id: Path(
            hf_hub_download(
                repo_id=EVAL_REPO_ID,
                repo_type="dataset",
                revision=EVAL_REVISION,
                filename=remote_path,
                token=token,
            )
        )
        for model_id, remote_path in _score_paths(token).items()
    }
    return source_path, score_paths


def _load_source(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=["domain", "scene_id", "task", "query_id", "answer_gt"],
    )
    if len(frame) != EXPECTED_ROWS or frame["task"].nunique() != EXPECTED_TASKS:
        raise RuntimeError("IID source must contain two rows for each of 1,000 tasks")
    task_counts = frame.groupby("task", sort=False).size()
    if set(task_counts) != {2}:
        raise RuntimeError("IID source rows are not balanced at two instances per task")
    frame = frame.reset_index(drop=True)
    frame["source_ordinal"] = np.arange(len(frame), dtype=int)
    return frame


def _load_score_rows(path: Path, *, model_id: str) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=[
            "model_id",
            "seed",
            "benchmark_id",
            "score_scope",
            "source_ordinal",
            "source_row_sha256",
            "score_unit",
            "score_value",
            "excluded",
        ],
    )
    aggregate = frame.loc[frame["score_scope"] == "aggregate"]
    rows = frame.loc[(frame["score_scope"] == "row") & ~frame["excluded"]].copy()
    if len(aggregate) != 1 or len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"invalid IID score shape for {model_id}")
    if set(rows["model_id"]) != {model_id} or set(rows["seed"].astype(int)) != {42}:
        raise RuntimeError(f"IID model or seed drift for {model_id}")
    if set(rows["benchmark_id"]) != {EVAL_BENCHMARK_ID}:
        raise RuntimeError(f"IID benchmark drift for {model_id}")
    if set(rows["score_unit"]) != {"fraction"}:
        raise RuntimeError(f"IID row scores are not fractions for {model_id}")
    if rows["source_ordinal"].isna().any() or rows["source_row_sha256"].isna().any():
        raise RuntimeError(f"IID score rows have missing identity for {model_id}")
    rows["source_ordinal"] = rows["source_ordinal"].astype(int)
    rows = rows.sort_values("source_ordinal")
    if not np.array_equal(rows["source_ordinal"].to_numpy(), np.arange(EXPECTED_ROWS)):
        raise RuntimeError(f"IID source ordinal drift for {model_id}")
    point = float(100.0 * rows["score_value"].astype(float).mean())
    aggregate_point = float(aggregate.iloc[0]["score_value"])
    if not math.isclose(point, aggregate_point, abs_tol=1e-10):
        raise RuntimeError(f"IID aggregate mismatch for {model_id}: {point} != {aggregate_point}")
    return rows[["source_ordinal", "source_row_sha256", "score_value"]].reset_index(drop=True)


def _answer_type(value: Any) -> str:
    payload = json.loads(value) if isinstance(value, str) else value
    if not isinstance(payload, Mapping) or not isinstance(payload.get("type"), str):
        raise RuntimeError("IID answer_gt is missing its typed-answer contract")
    answer_type = str(payload["type"])
    if answer_type not in ANSWER_LABELS:
        raise RuntimeError(f"unexpected IID answer type: {answer_type}")
    return answer_type


def _task_metadata(task_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for task_id in sorted(task_ids):
        task = create_task(task_id)
        query_ids = tuple(str(value) for value in task.supported_query_ids)
        if not query_ids:
            raise RuntimeError(f"task has no supported query ids: {task_id}")
        metadata[task_id] = {
            "operations": list(task_reasoning_operations(task_id)),
            "query_count": len(query_ids),
            "query_structure": "single_query" if len(query_ids) == 1 else "multi_query",
        }
    return metadata


def _joined_rows(source_path: Path, score_paths: Mapping[str, Path]) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    source = _load_source(source_path)
    task_metadata = _task_metadata(source["task"].unique())
    source["answer_interface"] = source["answer_gt"].map(_answer_type)
    source["query_structure"] = source["task"].map(
        lambda task_id: task_metadata[str(task_id)]["query_structure"]
    )
    source["operations"] = source["task"].map(
        lambda task_id: tuple(task_metadata[str(task_id)]["operations"])
    )

    reference_hashes: pd.Series | None = None
    for model_id, path in score_paths.items():
        scores = _load_score_rows(path, model_id=model_id)
        hashes = scores["source_row_sha256"]
        if reference_hashes is None:
            reference_hashes = hashes
        elif not hashes.equals(reference_hashes):
            raise RuntimeError(f"IID source hash mismatch for {model_id}")
        source[model_id] = scores["score_value"].astype(float).to_numpy()
    return source, task_metadata


def _bootstrap_task_delta(
    task_values: np.ndarray,
    *,
    replicates: int,
    seed: int,
    chunk_size: int,
) -> tuple[float, float]:
    if task_values.ndim != 1 or len(task_values) < 2:
        raise ValueError("task-cluster bootstrap requires at least two tasks")
    rng = np.random.default_rng(seed)
    draws = np.empty(replicates, dtype=np.float64)
    for start in range(0, replicates, chunk_size):
        stop = min(start + chunk_size, replicates)
        indices = rng.integers(0, len(task_values), size=(stop - start, len(task_values)))
        draws[start:stop] = task_values[indices].mean(axis=1)
    lower, upper = np.percentile(draws, (2.5, 97.5))
    return float(lower), float(upper)


def _slice_result(
    rows: pd.DataFrame,
    *,
    scale: str,
    replicates: int,
    bootstrap_seed: int,
    chunk_size: int,
    slice_key: str,
) -> dict[str, Any]:
    model_ids = MODELS[scale]
    base_id = str(model_ids["base"])
    trace_id = str(model_ids["trace"])
    task_means = rows.groupby("task", sort=True)[[base_id, trace_id]].mean()
    task_deltas = 100.0 * (
        task_means[trace_id].to_numpy(float) - task_means[base_id].to_numpy(float)
    )
    seed = int.from_bytes(
        hashlib.sha256(f"{bootstrap_seed}:{scale}:{slice_key}".encode("utf-8")).digest()[:8],
        byteorder="big",
    )
    ci = _bootstrap_task_delta(
        task_deltas,
        replicates=replicates,
        seed=seed,
        chunk_size=chunk_size,
    )
    base_score = float(100.0 * rows[base_id].mean())
    trace_score = float(100.0 * rows[trace_id].mean())
    return {
        "rows": int(len(rows)),
        "tasks": int(rows["task"].nunique()),
        "base_score": base_score,
        "trace_score": trace_score,
        "paired_gain": trace_score - base_score,
        "paired_gain_ci95": [ci[0], ci[1]],
    }


def _analyze_slices(
    rows: pd.DataFrame,
    *,
    replicates: int,
    bootstrap_seed: int,
    chunk_size: int,
) -> dict[str, Any]:
    analyses: dict[str, Any] = {
        "overall": {},
        "domains": {},
        "operations": {},
        "answer_interfaces": {},
        "query_structures": {},
    }
    for scale in MODELS:
        analyses["overall"][scale] = _slice_result(
            rows,
            scale=scale,
            replicates=replicates,
            bootstrap_seed=bootstrap_seed,
            chunk_size=chunk_size,
            slice_key="overall",
        )

    for domain in DOMAIN_LABELS:
        subset = rows.loc[rows["domain"] == domain]
        if subset.empty:
            raise RuntimeError(f"IID validation has no rows for domain {domain}")
        analyses["domains"][domain] = {
            "label": DOMAIN_LABELS[domain],
            **{
                scale: _slice_result(
                    subset,
                    scale=scale,
                    replicates=replicates,
                    bootstrap_seed=bootstrap_seed,
                    chunk_size=chunk_size,
                    slice_key=f"domain:{domain}",
                )
                for scale in MODELS
            },
        }

    for operation in REASONING_OPERATION_KEYS:
        subset = rows.loc[rows["operations"].map(lambda values: operation in values)]
        if subset.empty:
            raise RuntimeError(f"IID validation has no rows for operation {operation}")
        analyses["operations"][operation] = {
            "label": REASONING_OPERATION_LABELS[operation],
            **{
                scale: _slice_result(
                    subset,
                    scale=scale,
                    replicates=replicates,
                    bootstrap_seed=bootstrap_seed,
                    chunk_size=chunk_size,
                    slice_key=f"operation:{operation}",
                )
                for scale in MODELS
            },
        }

    for answer_type in ANSWER_LABELS:
        subset = rows.loc[rows["answer_interface"] == answer_type]
        analyses["answer_interfaces"][answer_type] = {
            "label": ANSWER_LABELS[answer_type],
            **{
                scale: _slice_result(
                    subset,
                    scale=scale,
                    replicates=replicates,
                    bootstrap_seed=bootstrap_seed,
                    chunk_size=chunk_size,
                    slice_key=f"answer:{answer_type}",
                )
                for scale in MODELS
            },
        }

    for structure, label in (
        ("single_query", "Single-query tasks"),
        ("multi_query", "Multi-query tasks"),
    ):
        subset = rows.loc[rows["query_structure"] == structure]
        analyses["query_structures"][structure] = {
            "label": label,
            **{
                scale: _slice_result(
                    subset,
                    scale=scale,
                    replicates=replicates,
                    bootstrap_seed=bootstrap_seed,
                    chunk_size=chunk_size,
                    slice_key=f"query:{structure}",
                )
                for scale in MODELS
            },
        }
    return analyses


def _draw_dot_whisker_axis(
    axis: Any,
    entries: list[tuple[str, Mapping[str, Any]]],
    *,
    title: str,
) -> None:
    y = np.arange(len(entries), dtype=float)
    offsets = {"3B": -0.14, "7B": 0.14}
    for scale in ("3B", "7B"):
        points = np.asarray([float(entry[1][scale]["paired_gain"]) for entry in entries])
        lower = np.asarray([float(entry[1][scale]["paired_gain_ci95"][0]) for entry in entries])
        upper = np.asarray([float(entry[1][scale]["paired_gain_ci95"][1]) for entry in entries])
        style = SCALE_STYLES[scale]
        axis.errorbar(
            points,
            y + offsets[scale],
            xerr=np.vstack((points - lower, upper - points)),
            fmt=str(style["marker"]),
            markersize=4.2,
            markerfacecolor=str(style["color"]),
            markeredgecolor="white",
            markeredgewidth=0.45,
            color=str(style["color"]),
            ecolor=str(style["color"]),
            elinewidth=0.9,
            capsize=1.8,
            capthick=0.8,
            label=scale,
            zorder=3,
        )
    labels = [
        f"{entry[1]['label']}  ({int(entry[1]['3B']['tasks'])})"
        for entry in entries
    ]
    axis.set_yticks(y, labels=labels)
    axis.invert_yaxis()
    axis.axvline(0.0, color=PLOT_REFERENCE, linewidth=0.8, linestyle="--", zorder=1)
    axis.grid(axis="x", color=PLOT_GRID, linewidth=0.55)
    axis.grid(axis="y", visible=False)
    axis.set_title(title, loc="left", fontweight="semibold", pad=6)
    axis.set_xlabel("Improvement over base (points)")
    axis.tick_params(axis="y", length=0, pad=3)
    axis.tick_params(axis="x", length=2.5, width=0.5)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.spines["bottom"].set_color(PLOT_REFERENCE)


def _write_figure(path: Path, analyses: Mapping[str, Any]) -> None:
    domain_entries = [(key, analyses["domains"][key]) for key in DOMAIN_LABELS]
    operation_entries = [(key, analyses["operations"][key]) for key in REASONING_OPERATION_KEYS]
    rc = {
        "font.family": "DejaVu Sans",
        "font.size": 7.5,
        "axes.titlesize": 8.5,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.7,
        "legend.fontsize": 7.0,
        "axes.labelcolor": PLOT_INK,
        "xtick.color": PLOT_MUTED,
        "ytick.color": PLOT_INK,
        "text.color": PLOT_INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
    with plt.rc_context(rc), sns.axes_style("white"), sns.plotting_context(
        "paper", rc=rc
    ):
        fig, axes = plt.subplots(1, 2, figsize=(6.55, 4.5), gridspec_kw={"wspace": 0.48})
        _draw_dot_whisker_axis(axes[0], domain_entries, title="(a) Visual domain")
        _draw_dot_whisker_axis(axes[1], operation_entries, title="(b) Operation family")
        handles, labels = axes[0].get_legend_handles_labels()
        for axis in axes:
            legend = axis.get_legend()
            if legend is not None:
                legend.remove()
        fig.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 1.015),
            ncol=2,
            frameon=False,
            handletextpad=0.45,
            columnspacing=1.2,
        )
        fig.subplots_adjust(left=0.16, right=0.99, bottom=0.10, top=0.90, wspace=0.50)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            path,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0.02,
            metadata={"CreationDate": None, "ModDate": None, "Creator": "Trace"},
        )
        plt.close(fig)


def _write_slice_table(path: Path, analyses: Mapping[str, Any]) -> None:
    def result_cells(entry: Mapping[str, Any], scale: str) -> list[str]:
        result = entry[scale]
        return [
            f"{float(result['base_score']):.2f}",
            f"{float(result['trace_score']):.2f}",
            f"{float(result['paired_gain']):+.2f}",
        ]

    groups = (
        (
            "Answer interface",
            [analyses["answer_interfaces"][key] for key in ANSWER_LABELS],
        ),
        (
            "Query structure",
            [
                analyses["query_structures"]["single_query"],
                analyses["query_structures"]["multi_query"],
            ],
        ),
    )
    lines = [
        "% Generated by paper/trace/scripts/build_iid_taxonomy_analysis.py. Do not edit.",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \fontsize{7.5}{8.6}\selectfont",
        r"  \setlength{\tabcolsep}{4.8pt}",
        r"  \caption{Accuracy by answer interface and query structure on the 2,000-instance \trace validation set. Each task contributes two unseen instances and scores use one decoding seed. Rows are analytical slices of the same task inventory.}",
        r"  \label{tab:iid-slice-results}",
        r"  \begin{tabular}{@{}l c c c c c c c@{}}",
        r"    \toprule",
        r"    & & \multicolumn{3}{c}{3B} & \multicolumn{3}{c}{7B} \\",
        r"    \cmidrule(lr){3-5}\cmidrule(l){6-8}",
        r"    Slice & Tasks & Base & After RLVR & $\Delta$ & Base & After RLVR & $\Delta$ \\",
        r"    \midrule",
    ]
    for group_index, (group_label, entries) in enumerate(groups):
        if group_index:
            lines.append(r"    \midrule")
        lines.append(rf"    \multicolumn{{8}}{{@{{}}l}}{{\textit{{{group_label}}}}} \\")
        for entry in entries:
            tasks = int(entry["3B"]["tasks"])
            if tasks != int(entry["7B"]["tasks"]):
                raise RuntimeError(f"IID slice task-count drift: {entry['label']}")
            cells = [str(entry["label"]), str(tasks)]
            cells.extend(result_cells(entry, "3B"))
            cells.extend(result_cells(entry, "7B"))
            lines.append("    " + " & ".join(cells) + r" \\")
    lines.extend(
        [
            r"    \bottomrule",
            r"  \end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    args = _parse_args()
    token = _token(args.token_file)
    source_path, score_paths = _download_inputs(token)
    rows, task_metadata = _joined_rows(source_path, score_paths)
    analyses = _analyze_slices(
        rows,
        replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
        chunk_size=args.bootstrap_chunk_size,
    )
    payload = {
        "schema_version": "trace_iid_taxonomy_analysis_v1",
        "method": {
            "confidence_level": 0.95,
            "interval": "percentile",
            "replicates": args.bootstrap_replicates,
            "seed": args.bootstrap_seed,
            "resampling_unit": "task",
            "cluster_contents": "Both unseen IID instances for the sampled task",
            "operation_rows_overlap": True,
        },
        "source": {
            "dataset": {
                "repository_id": SOURCE_REPO_ID,
                "revision": SOURCE_REVISION,
                "path": SOURCE_PARQUET,
                "rows": EXPECTED_ROWS,
                "tasks": EXPECTED_TASKS,
            },
            "evaluation": {
                "repository_id": EVAL_REPO_ID,
                "revision": EVAL_REVISION,
                "run_id": EVAL_RUN_ID,
                "benchmark_id": EVAL_BENCHMARK_ID,
                "decoding_seed": 42,
            },
            "reasoning_operation_schema": REASONING_OPERATION_SCHEMA_VERSION,
            "source_repository_head": _git_head(),
        },
        "task_metadata": task_metadata,
        "analyses": analyses,
    }
    _write_json(args.output_data, payload)
    _write_figure(args.output_figure, analyses)
    _write_slice_table(args.output_table, analyses)

    generator = Path(__file__).resolve()
    provenance = {
        "schema_version": "trace_iid_taxonomy_analysis_provenance_v1",
        "generator": {
            "path": str(generator.relative_to(REPO_ROOT)),
            "sha256": _sha256(generator),
        },
        "sources": payload["source"],
        "parameters": payload["method"],
        "outputs": {
            str(args.output_data.relative_to(REPO_ROOT)): {
                "sha256": _sha256(args.output_data),
                "bytes": args.output_data.stat().st_size,
            },
            str(args.output_figure.relative_to(REPO_ROOT)): {
                "sha256": _sha256(args.output_figure),
                "bytes": args.output_figure.stat().st_size,
            },
            str(args.output_table.relative_to(REPO_ROOT)): {
                "sha256": _sha256(args.output_table),
                "bytes": args.output_table.stat().st_size,
            },
        },
    }
    _write_json(args.output_provenance, provenance)
    print(f"[ok] wrote {args.output_data}")
    print(f"[ok] wrote {args.output_figure}")
    print(f"[ok] wrote {args.output_table}")
    print(f"[ok] wrote {args.output_provenance}")


if __name__ == "__main__":
    main()
