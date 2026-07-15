#!/usr/bin/env python3
"""Analyze CharXiv chart coverage gaps against Trace chart tasks.

CharXiv data, machine-readable summaries, and local markdown reports are written
under external/, which is ignored by the repository.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


DATASET_ID = "princeton-nlp/CharXiv"
DEFAULT_CACHE_ROOT = Path("external/datasets/charxiv")
DEFAULT_SUMMARY = DEFAULT_CACHE_ROOT / "analysis" / "charxiv_summary.json"
DEFAULT_REPORT = DEFAULT_CACHE_ROOT / "analysis" / "charxiv_expansion_report.md"

DESC_JUDGED = Path(
    "runs/charxivdesc/qwen3-vl-4b-instruct/"
    "vlmevalkit_defaults_qwen32b_judge/CharXiv_descriptive_val_judged_qwen3_32b.xlsx"
)
REASON_JUDGED = Path(
    "runs/charxivreason/qwen3-vl-4b-instruct/"
    "vlmevalkit_defaults_qwen32b_judge/CharXiv_reasoning_val_judged_qwen3_32b.xlsx"
)


DESC_QID_LABELS: dict[int, str] = {
    1: "subplot_title_lookup",
    2: "x_axis_label_lookup",
    3: "y_axis_label_lookup",
    4: "x_axis_leftmost_tick",
    5: "x_axis_rightmost_tick",
    6: "y_axis_lowest_tick",
    7: "y_axis_highest_tick",
    8: "x_axis_tick_spacing",
    9: "y_axis_tick_spacing",
    10: "line_count",
    11: "line_intersection_boolean",
    12: "legend_label_count",
    13: "legend_label_order_list",
    14: "colorbar_tick_range",
    15: "colorbar_tick_max",
    16: "overall_trend_description",
    17: "total_axis_tick_count",
    18: "subplot_layout_label",
    19: "subplot_count",
}

REASON_PATTERNS: dict[str, Sequence[str]] = {
    "cross_panel_or_subfigure_comparison": (
        r"\bsubplot\b",
        r"\bpanel\b",
        r"across panels",
        r"which subplot",
        r"among all .*subplots",
    ),
    "line_intersection_or_crossing": (
        r"\bintersect",
        r"\bcross(?:es|ing|ed)?\b",
    ),
    "point_predicate_count": (
        r"how many data points",
        r"number of data points",
        r"points? (?:lie|fall|are)",
    ),
    "trend_decline_slope_compare": (
        r"greater decline",
        r"greater increase",
        r"\bdecline\b",
        r"\bincrease\b",
        r"\bslope\b",
        r"\btrend\b",
        r"zig-?zag",
    ),
    "correlation_or_relation_direction": (
        r"correlat",
        r"positive(?:ly)? relation",
        r"negative(?:ly)? relation",
        r"relation with",
    ),
    "nearest_farthest_reference": (
        r"closest",
        r"nearest",
        r"furthest",
        r"farthest",
        r"away from",
    ),
    "distribution_shape_or_density": (
        r"density",
        r"variance",
        r"spread",
        r"spread-out",
        r"cluster",
        r"variability",
        r"smoother transition",
        r"skew",
    ),
    "axis_or_tick_reasoning": (
        r"x-axis",
        r"y-axis",
        r"\btick",
        r"\baxis\b",
    ),
    "legend_color_marker_style": (
        r"\blegend\b",
        r"color scheme",
        r"\bmarker",
        r"\bdashed\b",
        r"\bsolid\b",
        r"line style",
    ),
    "surface_or_contour_field": (
        r"\bsurface\b",
        r"\bcontour\b",
        r"\bheatmap\b",
        r"highest to lowest values",
    ),
}

TRACE_COVERAGE_KEYWORDS: dict[str, Sequence[str]] = {
    "axis metadata / tick OCR": ("axis", "tick", "title", "legend", "colorbar"),
    "scientific multipanel line plots": ("curve_panels", "subplot", "panel", "line"),
    "line/scatter value reasoning": ("single_series", "multiseries", "scatter_readout", "combo_mark"),
    "scatter clusters/regression": ("scatter_cluster", "scatter_regression", "correlation"),
    "error bars / uncertainty": ("error_interval", "uncertainty_band"),
    "heatmap / matrix": ("heatmap", "matrix"),
    "contour / density / hexbin": ("contour", "density", "hexbin"),
    "3D surface": ("surface_3d", "3d", "surface"),
}


@dataclass(frozen=True)
class JudgedSheet:
    name: str
    path: Path
    rows: int
    accuracy: float | None
    columns: tuple[str, ...]
    df: pd.DataFrame | None


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _counter_table(counter: Counter[Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    rows = counter.most_common(limit)
    return [{"value": str(key), "count": int(count)} for key, count in rows]


def _score(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return int(value)
    except Exception:
        return None


def _load_charxiv_splits(cache_root: Path, *, skip_download: bool) -> dict[str, Any]:
    """Load CharXiv splits through datasets and return lightweight summaries."""

    if skip_download:
        return {
            "dataset_id": DATASET_ID,
            "downloaded": False,
            "reason": "skipped by --skip-download",
            "splits": {},
        }

    try:
        from datasets import Image, load_dataset
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "dataset_id": DATASET_ID,
            "downloaded": False,
            "reason": f"datasets import failed: {exc}",
            "splits": {},
        }

    split_summaries: dict[str, Any] = {}
    for split in ("validation", "test"):
        ds = load_dataset(DATASET_ID, split=split, cache_dir=str(cache_root / "hf_cache"))
        if "image" in ds.column_names:
            ds = ds.cast_column("image", Image(decode=False))
        category = Counter()
        year = Counter()
        num_subplots = Counter()
        subplot_loc = Counter()
        desc_qids = Counter()
        desc_answer_status = Counter()
        reasoning_source = Counter()
        reasoning_answer_type = Counter()
        reasoning_patterns = Counter()
        sample_rows: list[dict[str, Any]] = []

        for idx, row in enumerate(ds):
            category[str(row.get("category", ""))] += 1
            year[str(row.get("year", ""))] += 1
            num_subplots[int(row.get("num_subplots") or 0)] += 1
            subplot_loc[str(row.get("subplot_loc", ""))] += 1
            for key in ("descriptive_q1", "descriptive_q2", "descriptive_q3", "descriptive_q4"):
                qid = row.get(key)
                if qid is not None:
                    desc_qids[int(qid)] += 1
            for key in ("descriptive_a1", "descriptive_a2", "descriptive_a3", "descriptive_a4"):
                answer = row.get(key)
                if answer is None or str(answer).strip() == "":
                    desc_answer_status["missing_or_null"] += 1
                elif str(answer).strip().lower() == "not applicable":
                    desc_answer_status["not_applicable"] += 1
                else:
                    desc_answer_status["present"] += 1
            reasoning_source[str(row.get("reasoning_q_source", ""))] += 1
            reasoning_answer_type[str(row.get("reasoning_a_type", ""))] += 1
            question = str(row.get("reasoning_q") or "")
            for bucket, regexes in REASON_PATTERNS.items():
                if any(re.search(regex, question, re.IGNORECASE) for regex in regexes):
                    reasoning_patterns[bucket] += 1
            if len(sample_rows) < 8:
                sample_rows.append(
                    {
                        "index": idx,
                        "figure_path": row.get("figure_path"),
                        "category": row.get("category"),
                        "num_subplots": row.get("num_subplots"),
                        "reasoning_q": row.get("reasoning_q"),
                        "reasoning_a": row.get("reasoning_a"),
                    }
                )

        split_summaries[split] = {
            "rows": int(len(ds)),
            "features": list(ds.column_names),
            "category": _counter_table(category),
            "year": _counter_table(year),
            "num_subplots": _counter_table(num_subplots),
            "subplot_loc": _counter_table(subplot_loc, limit=12),
            "descriptive_qids": [
                {
                    "qid": int(qid),
                    "label": DESC_QID_LABELS.get(int(qid), f"qid_{qid}"),
                    "count": int(count),
                }
                for qid, count in sorted(desc_qids.items())
            ],
            "descriptive_answer_status": _counter_table(desc_answer_status),
            "reasoning_source": _counter_table(reasoning_source),
            "reasoning_answer_type": _counter_table(reasoning_answer_type),
            "reasoning_patterns": _counter_table(reasoning_patterns),
            "sample_rows": sample_rows,
        }

    return {
        "dataset_id": DATASET_ID,
        "downloaded": True,
        "cache_root": str(cache_root),
        "splits": split_summaries,
    }


def _read_judged_sheet(name: str, path: Path) -> JudgedSheet:
    if not path.exists():
        return JudgedSheet(name=name, path=path, rows=0, accuracy=None, columns=(), df=None)
    df = pd.read_excel(path)
    accuracy = None
    if "score" in df.columns:
        scores = [_score(value) for value in df["score"]]
        valid_scores = [value for value in scores if value is not None]
        if valid_scores:
            accuracy = float(sum(valid_scores) / len(valid_scores))
    return JudgedSheet(name=name, path=path, rows=int(len(df)), accuracy=accuracy, columns=tuple(str(c) for c in df.columns), df=df)


def _parse_chart_type(raw: Any) -> list[str]:
    if raw is None:
        return ["<missing>"]
    if isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
    return [str(raw)]


def _question_bucket_counts(df: pd.DataFrame, *, include_failure: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket, regexes in REASON_PATTERNS.items():
        mask = df["question"].fillna("").astype(str).apply(
            lambda value: any(re.search(regex, value, re.IGNORECASE) for regex in regexes)
        )
        count = int(mask.sum())
        if not count:
            continue
        item: dict[str, Any] = {"bucket": bucket, "rows": count}
        if "score" in df.columns:
            acc = float(df.loc[mask, "score"].mean())
            item["accuracy"] = round(acc, 4)
            if include_failure:
                item["wrong"] = int((df.loc[mask, "score"] == 0).sum())
        rows.append(item)
    rows.sort(key=lambda item: (item.get("accuracy", 999.0), -int(item["rows"])))
    return rows


def _judged_summary(sheet: JudgedSheet) -> dict[str, Any]:
    if sheet.df is None:
        return {
            "path": str(sheet.path),
            "present": False,
            "rows": 0,
            "accuracy": None,
        }
    df = sheet.df
    chart_type = Counter()
    chart_combo = Counter()
    for raw in df.get("chart_type", []):
        types = tuple(_parse_chart_type(raw))
        chart_combo[types] += 1
        for chart in types:
            chart_type[chart] += 1

    summary: dict[str, Any] = {
        "path": str(sheet.path),
        "present": True,
        "rows": sheet.rows,
        "accuracy": sheet.accuracy,
        "columns": list(sheet.columns),
        "chart_types": _counter_table(chart_type, limit=30),
        "chart_type_combos": [{"value": ", ".join(key), "count": int(count)} for key, count in chart_combo.most_common(20)],
        "num_subplots": _counter_table(Counter(int(value) for value in df.get("num_subplots", []) if not pd.isna(value)), limit=20),
        "question_buckets": _question_bucket_counts(df, include_failure=True),
    }

    if "qid" in df.columns:
        qid_rows: list[dict[str, Any]] = []
        for qid, group in sorted(df.groupby("qid"), key=lambda item: int(item[0])):
            qid_int = int(qid)
            example = " ".join(str(group.iloc[0].get("question", "")).split())
            qid_rows.append(
                {
                    "qid": qid_int,
                    "label": DESC_QID_LABELS.get(qid_int, f"qid_{qid_int}"),
                    "rows": int(len(group)),
                    "accuracy": round(float(group["score"].mean()), 4) if "score" in group.columns else None,
                    "example": example,
                }
            )
        summary["descriptive_qids"] = qid_rows

    if "inst_category" in df.columns:
        summary["inst_category"] = _counter_table(Counter(str(value) for value in df["inst_category"]), limit=20)
    if "category" in df.columns:
        summary["category"] = _counter_table(Counter(str(value) for value in df["category"]), limit=20)

    examples_by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if "score" in df.columns and "question" in df.columns:
        for _, row in df.loc[df["score"] == 0].iterrows():
            question = str(row.get("question", ""))
            for bucket, regexes in REASON_PATTERNS.items():
                if len(examples_by_bucket[bucket]) >= 3:
                    continue
                if any(re.search(regex, question, re.IGNORECASE) for regex in regexes):
                    examples_by_bucket[bucket].append(
                        {
                            "question": " ".join(question.split())[:260],
                            "answer": str(row.get("answer", ""))[:120],
                            "prediction": str(row.get("prediction", ""))[:160],
                            "chart_type": str(row.get("chart_type", "")),
                            "num_subplots": None if pd.isna(row.get("num_subplots", None)) else int(row.get("num_subplots")),
                        }
                    )
        summary["incorrect_examples_by_bucket"] = dict(examples_by_bucket)

    return summary


def _trace_inventory() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from trace.tasks.registry import list_default_task_ids
    except Exception as exc:
        return {"available": False, "reason": str(exc), "chart_tasks": 0, "scenes": []}

    chart_ids = [task_id for task_id in list_default_task_ids() if task_id.startswith("task_charts__")]
    scenes = Counter(task_id.split("__")[1] for task_id in chart_ids if len(task_id.split("__")) >= 3)
    all_text = "\n".join(chart_ids).lower()
    keyword_coverage = {
        label: any(keyword.lower() in all_text for keyword in keywords)
        for label, keywords in TRACE_COVERAGE_KEYWORDS.items()
    }
    return {
        "available": True,
        "chart_tasks": int(len(chart_ids)),
        "scene_count": int(len(scenes)),
        "scenes": [{"scene": scene, "tasks": int(count)} for scene, count in sorted(scenes.items())],
        "keyword_coverage": keyword_coverage,
    }


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(lines)


def _fmt_acc(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.3f}"
    except Exception:
        return str(value)


def _make_report(summary: Mapping[str, Any]) -> str:
    trace = summary["trace_inventory"]
    hf = summary["hf_dataset"]
    desc = summary["judged"]["descriptive"]
    reason = summary["judged"]["reasoning"]

    split_rows = []
    for split, item in hf.get("splits", {}).items():
        split_rows.append(
            [
                split,
                item.get("rows", 0),
                ", ".join(f"{row['value']}={row['count']}" for row in item.get("category", [])[:4]),
                ", ".join(f"{row['value']}={row['count']}" for row in item.get("num_subplots", [])[:6]),
            ]
        )

    scene_rows = [[row["scene"], row["tasks"]] for row in trace.get("scenes", [])]

    desc_qid_rows = []
    for row in desc.get("descriptive_qids", []):
        desc_qid_rows.append([row["qid"], row["label"], row["rows"], _fmt_acc(row.get("accuracy"))])

    reason_bucket_rows = []
    for row in reason.get("question_buckets", [])[:14]:
        reason_bucket_rows.append([row["bucket"], row["rows"], row.get("wrong", ""), _fmt_acc(row.get("accuracy"))])

    chart_type_rows = []
    for row in reason.get("chart_types", [])[:18]:
        chart_type_rows.append([row["value"], row["count"]])

    recommendations = [
        [
            "P0",
            "existing scene/style",
            "scientific_paper style preset",
            "Apply to line, multiseries, scatter, curve_panels, heatmap, error_interval, uncertainty_band, surface_3d.",
            "CharXiv figures are arXiv/MATLAB-like: small fonts, thin axes, dense ticks, legends outside/inside, markers, grayscale/dashed variants, colorbars, subplot letters.",
        ],
        [
            "P0",
            "new scene",
            "scientific_axis_metadata",
            "axis label lookup, tick extremum, tick spacing, total tick count, subplot title lookup.",
            "Trace mostly asks data reasoning over marks; CharXiv descriptive questions heavily test chart-frame metadata and tick OCR.",
        ],
        [
            "P0",
            "existing scene expansion",
            "curve_panels",
            "subplot layout/count, subplot title lookup, cross-panel decline/slope comparison, panel-local point predicate count.",
            "Current curve_panels has method-curve reasoning but not CharXiv-style figure layout and subplot-frame questions.",
        ],
        [
            "P0",
            "new scene or heatmap/surface expansion",
            "colorbar_field",
            "colorbar max/min/range/tick spacing; heatmap/contour/surface variants with continuous legends.",
            "Descriptive qids 14/15 and many failures involve continuous legends; current heatmap tasks reason over cells, not colorbar metadata.",
        ],
        [
            "P1",
            "new scene",
            "contour_density",
            "densest region label, nearest contour cluster to coordinate, level-set crossing/count, spread/variance option selection.",
            "CharXiv contains density, contour, hexbin, QQ-like scientific plots not represented by current scatter_cluster/readout tasks.",
        ],
        [
            "P1",
            "existing scene expansion",
            "error_interval / uncertainty_band",
            "scientific errorbar point predicate count, interval overlap at x, line-with-errorbar extremum.",
            "CharXiv scientific plots often combine markers/lines with error bars; Trace has interval scenes but not arXiv-style marker-series integration.",
        ],
        [
            "P1",
            "new scene",
            "scientific_style_legend",
            "map color/marker/line-style condition to legend label; count legend entries; identify curve by dashed/marker style.",
            "Many arXiv plots use line style and marker shape as semantic encodings, not just color.",
        ],
        [
            "P2",
            "existing scene expansion",
            "surface_3d",
            "smoothness/variation option selection, subplot surface transition comparison, colorbar-backed extremum.",
            "Reasoning failures include subjective-but-visual surface comparisons; use rendered options to keep answers verifier-friendly.",
        ],
    ]

    caution_rows = [
        [
            "Licensing",
            "Use CharXiv images only for analysis/inspection. Do not copy arXiv chart images into Trace assets or training data; synthesize styles/tasks instead.",
        ],
        [
            "Answer format",
            "Avoid free-form long legend lists as default RLVR tasks unless we define a strict list schema. Prefer count, selected label, option label, or bounded string answer first.",
        ],
        [
            "Not Applicable",
            "CharXiv frequently uses Not Applicable. Trace should add explicit unanswerable branches only where distribution and verifier semantics are clean.",
        ],
        [
            "Prompt options",
            "If a CharXiv-style choice question is adapted, options must be rendered in the image, not listed only in prompt text.",
        ],
    ]

    lines = [
        "# CharXiv-Driven Chart Coverage Report",
        "",
        "## Inputs reviewed",
        "",
        f"- Hugging Face dataset: `{DATASET_ID}`.",
        "- Linked split focus: `test`; validation is also loaded to align with existing judged Trace benchmark artifacts.",
        "- Dataset card metadata: 2.32k total rows, validation 1k, test 1.32k, license `cc-by-sa-4.0`.",
        f"- Local cache root: `{hf.get('cache_root', DEFAULT_CACHE_ROOT)}`.",
        f"- Existing descriptive judged sheet: `{desc.get('path')}`.",
        f"- Existing reasoning judged sheet: `{reason.get('path')}`.",
        "",
        "## Dataset summary",
        "",
        _markdown_table(["Split", "Rows", "Top categories", "Top subplot counts"], split_rows),
        "",
        "## Current Trace chart inventory",
        "",
        f"- Active chart tasks: {trace.get('chart_tasks', 0)}.",
        f"- Active chart scenes: {trace.get('scene_count', 0)}.",
        "",
        _markdown_table(["Scene", "Tasks"], scene_rows),
        "",
        "## Local CharXiv model-failure signal",
        "",
        f"- Descriptive validation rows: {desc.get('rows', 0)}, Qwen3-VL-4B judged accuracy: {_fmt_acc(desc.get('accuracy'))}.",
        f"- Reasoning validation rows: {reason.get('rows', 0)}, Qwen3-VL-4B judged accuracy: {_fmt_acc(reason.get('accuracy'))}.",
        "- Descriptive is comparatively high overall, but still stresses axis ticks, legends, colorbars, subplot layouts, and total tick counts.",
        "- Reasoning is the stronger expansion signal: it is much lower accuracy and concentrates on scientific multi-panel line/scatter/field plots.",
        "",
        "### Descriptive qid breakdown",
        "",
        _markdown_table(["QID", "Interpreted pattern", "Rows", "Accuracy"], desc_qid_rows),
        "",
        "### Reasoning failure buckets",
        "",
        _markdown_table(["Bucket", "Rows", "Wrong", "Accuracy"], reason_bucket_rows),
        "",
        "### Reasoning chart-type pressure",
        "",
        _markdown_table(["Chart type", "Rows"], chart_type_rows),
        "",
        "## Coverage interpretation",
        "",
        "- Trace already has broad chart coverage and an existing `curve_panels` scientific multipanel line-grid implementation.",
        "- The main unsupported CharXiv capability is not generic line/bar/scatter charts; it is scientific-paper rendering plus chart-frame metadata and subplot-local reasoning.",
        "- Axis labels, tick values, tick spacing, total tick counts, legend entry order/count, colorbar ticks, and subplot titles are underrepresented because Trace mostly asks data-mark reasoning.",
        "- CharXiv also pressures dense scientific styles: MATLAB-like colors, black/gray line styles, markers, dashed/dotted curves, outside legends, tight grids, small fonts, and colorbars.",
        "",
        "## Recommended expansions",
        "",
        _markdown_table(["Priority", "Kind", "Target", "Candidate tasks", "Why this is not already covered"], recommendations),
        "",
        "## Implementation cautions",
        "",
        _markdown_table(["Area", "Guidance"], caution_rows),
        "",
        "## Suggested implementation order",
        "",
        "1. Add a shared `scientific_paper` chart style preset and enable it first in existing line/scatter/panel scientific scenes.",
        "2. Add `scientific_axis_metadata` with bounded answer schemas for tick/title/axis/legend/colorbar readout.",
        "3. Expand `curve_panels` with subplot layout/count/title and cross-panel decline/slope comparisons.",
        "4. Add `colorbar_field` or extend heatmap/surface renderers with explicit colorbar readout tasks.",
        "5. Add `contour_density` only after reviewing generated samples, because contour/density questions can become too subjective without rendered options.",
        "",
        "## Machine-readable summary",
        "",
        f"A JSON summary was also written to `{summary.get('summary_path', DEFAULT_SUMMARY)}`.",
        "",
    ]
    return "\n".join(lines)


def build_summary(cache_root: Path, *, skip_download: bool) -> dict[str, Any]:
    hf_summary = _load_charxiv_splits(cache_root, skip_download=skip_download)
    desc_sheet = _read_judged_sheet("descriptive", DESC_JUDGED)
    reason_sheet = _read_judged_sheet("reasoning", REASON_JUDGED)
    return {
        "hf_dataset": hf_summary,
        "judged": {
            "descriptive": _judged_summary(desc_sheet),
            "reasoning": _judged_summary(reason_sheet),
        },
        "trace_inventory": _trace_inventory(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT, help="Ignored local CharXiv cache root.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Markdown report path.")
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY, help="Ignored machine-readable summary path.")
    parser.add_argument("--skip-download", action="store_true", help="Analyze only local judged sheets without loading HF data.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_summary(args.cache_root, skip_download=bool(args.skip_download))
    summary["summary_path"] = str(args.summary_json)

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(_make_report(summary), encoding="utf-8")
    print(f"wrote {args.report}")
    print(f"wrote {args.summary_json}")


if __name__ == "__main__":
    main()
