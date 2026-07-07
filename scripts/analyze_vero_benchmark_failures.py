#!/usr/bin/env python3
"""Summarize sampled VERO failures and map question patterns to TRACE coverage."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from run_vero_sampled_benchmark import BENCHMARK_SPECS, DEFAULT_RUN_ROOT, REPO_ROOT, SPEC_BY_KEY, json_default


DEFAULT_ANALYSIS_ROOT = REPO_ROOT / "review/external_benchmark_failure_analysis/qwen25vl7b"
TRACE_TASK_DOCS = {path.stem for path in (REPO_ROOT / "docs/tasks").rglob("task_*.md")}

SAMPLE_RE = re.compile(r".*_samples_(.+)\.jsonl$")

BASE_SAMPLE_KEYS = {
    "doc_id",
    "doc_hash",
    "input",
    "target",
    "filtered_resps",
    "resps",
    "image",
    "category",
    "conversation",
    "turn",
    "message_index",
}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=json_default) + "\n")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def resolve_run_dir(run_root: Path, run_id: str | None) -> Path:
    if run_id:
        candidate = run_root / run_id
        return candidate if candidate.exists() else Path(run_id)
    if (run_root / "RUN_MANIFEST.json").exists() or any(run_root.glob("*/sample_summary.json")):
        return run_root
    children = sorted([path for path in run_root.iterdir() if path.is_dir()]) if run_root.exists() else []
    if not children:
        raise SystemExit(f"No run directories found under {run_root}")
    return children[-1]


def output_root_for_run(analysis_root: Path, run_dir: Path) -> Path:
    if analysis_root.name == run_dir.name:
        return analysis_root
    return analysis_root / run_dir.name


def task_name_from_sample_path(path: Path) -> str:
    match = SAMPLE_RE.match(path.name)
    if not match:
        return path.stem
    return match.group(1)


def effective_judge_deferred(spec: Any, run_summary: dict[str, Any]) -> bool:
    if run_summary.get("judge_metrics_enabled") or run_summary.get("judge_direct_from_samples"):
        return False
    return bool(spec.judge_deferred)


def sample_files_for_analysis(bench_dir: Path, run_summary: dict[str, Any]) -> list[Path]:
    judged = run_summary.get("judge_samples_path")
    if judged:
        judged_path = Path(judged)
        if judged_path.exists():
            return [judged_path]
    sample_files = sorted(bench_dir.glob("*_samples_*.jsonl"))
    latest_by_task: dict[str, Path] = {}
    for sample_path in sample_files:
        latest_by_task[task_name_from_sample_path(sample_path)] = sample_path
    return sorted(latest_by_task.values())


def first_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        for item in value:
            text = first_text(item)
            if text:
                return text
        return ""
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, default=json_default)


def compact(text: Any, max_len: int = 160) -> str:
    value = first_text(text) if not isinstance(text, str) else text
    value = " ".join(value.split())
    return value[: max_len - 3] + "..." if len(value) > max_len else value


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "correct", "1"}:
            return True
        if lowered in {"false", "no", "incorrect", "0"}:
            return False
    return None


def numeric_values(value: Any) -> list[float]:
    if isinstance(value, bool):
        return [1.0 if value else 0.0]
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        out: list[float] = []
        for sub_value in value.values():
            out.extend(numeric_values(sub_value))
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for sub_value in value:
            out.extend(numeric_values(sub_value))
        return out
    return []


def metric_to_score(metric_name: str, value: Any) -> tuple[bool | None, float | None]:
    if metric_name == "bypass":
        return None, None
    if isinstance(value, dict):
        for key in ("is_correct", "correct", "true_false"):
            if key in value:
                parsed = parse_bool(value[key])
                if parsed is not None:
                    return parsed, 1.0 if parsed else 0.0
        for key in ("score", "accuracy", "acc", "exact_match"):
            if key in value and isinstance(value[key], (int, float, bool)):
                score = float(value[key])
                return score > 0.5, score
        if "scores" in value:
            nums = numeric_values(value["scores"])
            if nums:
                score = sum(nums) / len(nums)
                return score > 0.5, score
        nums = numeric_values(value)
        if nums:
            score = sum(nums) / len(nums)
            return score > 0.5, score
        return None, None
    if isinstance(value, bool):
        return value, 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        score = float(value)
        threshold = 0.5
        if metric_name == "anls":
            threshold = 0.5
        return score > threshold, score
    return None, None


PREFERRED_METRICS = (
    "individual_score",
    "relaxed_overall",
    "accuracy",
    "exact_match",
    "anls",
    "blink_acc",
    "erqa_acc",
    "embspatial_acc",
    "game_qa_acc",
    "vstar_overall_acc",
    "screenspot_PointInBox_ACC",
    "aerialvg_acc@0.5",
    "mmmu_acc",
    "mathvision_standard_eval",
    "llm_as_judge_eval",
    "judge_accuracy",
    "simplevqa_acc",
)


def extract_metrics(sample: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in sample.items() if key not in BASE_SAMPLE_KEYS}


def infer_correctness(sample: dict[str, Any], judge_deferred: bool) -> tuple[bool | None, float | None, str]:
    if judge_deferred:
        return None, None, "judge_deferred"
    metrics = extract_metrics(sample)
    for metric_name in PREFERRED_METRICS:
        if metric_name in metrics:
            correct, score = metric_to_score(metric_name, metrics[metric_name])
            if correct is not None:
                return correct, score, metric_name
    for metric_name, value in metrics.items():
        correct, score = metric_to_score(metric_name, value)
        if correct is not None:
            return correct, score, metric_name
    return None, None, "unparsed"


def classify_intent(question: str, benchmark_key: str, task_name: str) -> str:
    text = f"{question} {task_name}".lower()
    if any(token in text for token in ("bbox", "bounding box", "box around", "coordinates")):
        return "grounding_bbox"
    if any(token in text for token in ("click", "point", "tap", "locate", "where is")):
        return "grounding_point"
    if any(token in text for token in ("how many", "number of", "count", "tally")):
        return "counting"
    if any(token in text for token in ("largest", "smallest", "highest", "lowest", "most", "least", "maximum", "minimum")):
        return "comparison_extreme"
    if any(token in text for token in ("difference", "sum", "total", "average", "mean", "ratio", "percentage")):
        return "arithmetic"
    if any(token in text for token in ("increase", "decrease", "trend", "before", "after", "between years", "over time")):
        return "trend_temporal"
    if any(token in text for token in ("left", "right", "above", "below", "behind", "front", "between", "closer", "farther")):
        return "spatial_relation"
    if any(token in text for token in ("path", "route", "reachable", "shortest", "navigate", "move")):
        return "path_or_navigation"
    if any(token in text for token in ("chart", "bar", "line graph", "axis", "legend", "plot")) or benchmark_key in {"chartqapro", "chartmuseum", "evochart"}:
        return "chart_reasoning"
    if benchmark_key in {"infovqa", "simplevqaen"} or any(token in text for token in ("document", "page", "form", "table", "paragraph")):
        return "document_or_ocr"
    if benchmark_key in {"mathvista_testmini", "mathvision", "mmmu_pro_vision"}:
        return "math_diagram_reasoning"
    if benchmark_key == "game_qa_lite":
        return "game_state_reasoning"
    if benchmark_key in {"blink", "erqa", "embspatial"}:
        return "visual_spatial_reasoning"
    return "other"


def metadata_label(sample: dict[str, Any], manifest: dict[str, Any]) -> str:
    candidates = []
    for obj in (sample, manifest.get("doc_preview", {})):
        if not isinstance(obj, dict):
            continue
        for key in ("sub_task", "category", "question_type", "answer_type", "source", "subject", "game_name", "state", "task"):
            if obj.get(key) not in (None, ""):
                candidates.append(f"{key}={compact(obj[key], 80)}")
    for value in extract_metrics(sample).values():
        if isinstance(value, dict):
            for key in ("sub_task", "category", "game_name", "state", "type"):
                if value.get(key) not in (None, ""):
                    candidates.append(f"{key}={compact(value[key], 80)}")
    return candidates[0] if candidates else "unspecified"


def existing_tasks(candidates: list[str]) -> list[str]:
    return [task for task in candidates if task in TRACE_TASK_DOCS]


def trace_mapping(benchmark_key: str, intent: str, label: str) -> dict[str, Any]:
    if benchmark_key in {"chartqapro", "chartmuseum", "evochart"}:
        tasks = existing_tasks(
            [
                "task_charts__single_series__threshold_value_count",
                "task_charts__single_series__interval_value_count",
                "task_charts__single_series__endpoint_change_value",
                "task_charts__single_series__interval_rate_value",
                "task_charts__table__column_summary_value",
                "task_charts__multiseries__ranked_change_extremum_label",
                "task_charts__multiseries__ranked_pair_ratio_extremum_label",
                "task_charts__multiseries__ranked_series_share_extremum_label",
                "task_charts__scatter_readout__series_pair_value_gap_at_x",
                "task_charts__scatter_readout__series_y_anchor_other_series_value",
            ]
        )
        return {
            "status": "covered" if intent in {"chart_reasoning", "counting", "comparison_extreme", "arithmetic", "trend_temporal"} else "partial",
            "closest": tasks,
            "suggestion": "Use chart scenes first; add chart-style variants if failures cluster around unusual museum or infographic styles.",
        }
    if benchmark_key == "infovqa":
        tasks = existing_tasks(
            [
                "task_pages__control_board__control_state_condition_count",
                "task_pages__paired_forms__total_amount_delta_value",
                "task_pages__paired_forms__sum_absolute_quantity_differences_value",
                "task_pages__form_section__two_amount_arithmetic_value",
                "task_charts__table__threshold_count",
                "task_charts__table__interval_value_count",
                "task_charts__table__categorical_value_count",
                "task_charts__table__column_summary_value",
            ]
        )
        return {
            "status": "partial",
            "closest": tasks,
            "suggestion": "Map structured pages to pages scenes and table-like numeric displays to chart table scenes; long OCR-heavy pages remain a scene gap.",
        }
    if benchmark_key in {"mmmu_pro_vision", "mathvista_testmini", "mathvision"}:
        tasks = existing_tasks(
            [
                "task_geometry__graph_paper__angle_extremum_label",
                "task_geometry__graph_paper__polygon_area_value",
                "task_physics__circuit_equivalent__total_resistance_value",
                "task_charts__curve_panels__curve_intersection_count",
                "task_puzzles__raven_matrix__raven_position_progression_label",
            ]
        )
        return {
            "status": "partial",
            "closest": tasks,
            "suggestion": "Split by visual family: geometry, physics, charts, chart table scenes, and puzzle/page diagrams are covered separately; broad exam-style mixtures need per-pattern triage.",
        }
    if benchmark_key in {"blink", "erqa", "embspatial"}:
        tasks = existing_tasks(
            [
                "task_three_d__object_scene__object_relation_label",
                "task_three_d__object_scene__between_references_label",
                "task_icons__reference_canvas__anchor_position_count",
                "task_geometry__shape_reference__reflection_match",
                "task_geometry__shape_reference__rotation_match",
                "task_geometry__shape_reference__translation_match",
            ]
        )
        status = "partial" if intent in {"spatial_relation", "visual_spatial_reasoning"} else "gap"
        return {
            "status": status,
            "closest": tasks,
            "suggestion": "Synthetic spatial and correspondence tasks cover the reasoning form; natural-image appearance matching is outside current TRACE scope.",
        }
    if benchmark_key == "game_qa_lite":
        tasks = existing_tasks(
            [
                "task_games__snake__safe_direction_count",
                "task_games__pacman__next_item_label",
                "task_games__space_shooter__safe_lane_count",
                "task_games__crossing__moving_object_direction_count",
                "task_puzzles__cell_board__reachable_region_size",
                "task_puzzles__cell_board__largest_component_size",
                "task_puzzles__cell_board__shortest_path_length_value",
            ]
        )
        return {
            "status": "partial",
            "closest": tasks,
            "suggestion": "Map board and grid state logic to games and cell-board puzzle scenes; add a new scene only for repeated unsupported mini-game mechanics.",
        }
    if benchmark_key == "countqa":
        tasks = existing_tasks(
            [
                "task_icons__reference_canvas__reference_type_color_rotation_match_count",
                "task_icons__named_field__multi_attribute_and_count",
                "task_illustrations__environment__feature_relation_object_count",
            ]
        )
        return {
            "status": "partial",
            "closest": tasks,
            "suggestion": "Counting with synthetic icons and illustrations is covered; natural-image object recognition remains only partially mapped.",
        }
    if benchmark_key == "vstarbench":
        tasks = existing_tasks(
            [
                "task_icons__overlap_grid__occlusion_order_count",
                "task_icons__reference_canvas__anchor_position_count",
                "task_illustrations__indoor_room__furniture_side_count",
                "task_three_d__object_scene__reference_nearest_label",
            ]
        )
        return {
            "status": "partial",
            "closest": tasks,
            "suggestion": "Use relation and spatial scenes for reasoning shape; add targeted scene variants if VStar failures are mostly fine-grained real-object attributes.",
        }
    if benchmark_key == "screenspotpro":
        tasks = existing_tasks(
            [
                "task_pages__web_action__action_target_label",
                "task_pages__web_action__guide_code_target_count",
                "task_pages__workspace__control_label",
                "task_pages__workspace__context_control_count",
                "task_pages__workspace__context_guide_control_label",
                "task_pages__schema__field_role_count",
            ]
        )
        return {
            "status": "covered" if intent in {"grounding_point", "document_or_ocr"} else "partial",
            "closest": tasks,
            "suggestion": "GUI target selection maps to pages relation tasks; coverage may need richer desktop/app chrome variants.",
        }
    if benchmark_key == "aerialvg":
        return {
            "status": "gap",
            "closest": existing_tasks(
                [
                    "task_pages__map__destination_after_directions_label",
                    "task_pages__map__landmark_after_route_step_label",
                ]
            ),
            "suggestion": "Consider a pages/aerial_map_canvas scene with landmark bboxes, zones, and region-relative grounding.",
        }
    if benchmark_key == "simplevqaen":
        return {
            "status": "out_of_scope",
            "closest": [],
            "suggestion": "This is mostly open visual knowledge and recognition; only structured visual-reasoning subsets should become TRACE tasks.",
        }
    return {"status": "gap", "closest": [], "suggestion": "Needs manual taxonomy triage."}


def load_manifest(bench_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    manifest_path = bench_dir / "sample_manifest.jsonl"
    if not manifest_path.exists():
        return {}
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for row in read_jsonl(manifest_path):
        out[(row.get("task_name", ""), int(row.get("sample_doc_id", -1)))] = row
    return out


def normalize_benchmark_samples(run_dir: Path, benchmark_key: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = SPEC_BY_KEY[benchmark_key]
    bench_dir = run_dir / benchmark_key
    run_summary = read_json(bench_dir / "run_summary.json", {})
    judge_deferred = effective_judge_deferred(spec, run_summary)
    manifest = load_manifest(bench_dir)
    sample_files = sample_files_for_analysis(bench_dir, run_summary)
    rows: list[dict[str, Any]] = []
    for sample_path in sample_files:
        task_name = task_name_from_sample_path(sample_path)
        for sample in read_jsonl(sample_path):
            doc_id = int(sample.get("doc_id", -1))
            manifest_row = manifest.get((task_name, doc_id), {})
            question = first_text(sample.get("input")) or compact(manifest_row.get("doc_preview", {}).get("question", ""))
            correct, score, scoring_mode = infer_correctness(sample, judge_deferred)
            intent = classify_intent(question, benchmark_key, task_name)
            label = metadata_label(sample, manifest_row)
            mapping = trace_mapping(benchmark_key, intent, label)
            rows.append(
                {
                    "benchmark": benchmark_key,
                    "benchmark_display": spec.display,
                    "task_name": task_name,
                    "doc_id": doc_id,
                    "original_index": manifest_row.get("original_index"),
                    "target": sample.get("target"),
                    "response": first_text(sample.get("filtered_resps")),
                    "question": question,
                    "is_correct": correct,
                    "score": score,
                    "scoring_mode": scoring_mode,
                    "intent": intent,
                    "metadata_label": label,
                    "trace_status": mapping["status"],
                    "trace_closest": mapping["closest"],
                    "trace_suggestion": mapping["suggestion"],
                    "metrics": extract_metrics(sample),
                    "manifest": manifest_row,
                }
            )
    summary = {
        "benchmark": benchmark_key,
        "display": spec.display,
        "sample_files": [str(path) for path in sample_files],
        "items": len(rows),
        "judge_deferred": judge_deferred,
    }
    return rows, summary


def build_patterns(rows: list[dict[str, Any]], judge_deferred: bool) -> list[dict[str, Any]]:
    selected = rows if judge_deferred else [row for row in rows if row["is_correct"] is False]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        key = (row["intent"], row["metadata_label"], row["trace_status"])
        grouped[key].append(row)
    patterns = []
    for (intent, label, status), group_rows in grouped.items():
        examples = []
        for row in group_rows[:3]:
            examples.append(
                {
                    "task_name": row["task_name"],
                    "doc_id": row["doc_id"],
                    "question": compact(row["question"], 180),
                    "target": compact(row["target"], 80),
                    "response": compact(row["response"], 80),
                }
            )
        closest_counter = Counter(task for row in group_rows for task in row["trace_closest"])
        suggestion = group_rows[0]["trace_suggestion"] if group_rows else ""
        patterns.append(
            {
                "intent": intent,
                "metadata_label": label,
                "count": len(group_rows),
                "trace_status": status,
                "closest_trace_tasks": [task for task, _ in closest_counter.most_common(6)],
                "suggestion": suggestion,
                "examples": examples,
            }
        )
    patterns.sort(key=lambda row: (-row["count"], row["intent"], row["metadata_label"]))
    return patterns[:20]


def markdown_for_benchmark(
    benchmark_key: str,
    rows: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    spec = SPEC_BY_KEY[benchmark_key]
    scored = [row for row in rows if row["is_correct"] is not None]
    wrong = [row for row in scored if row["is_correct"] is False]
    correct = [row for row in scored if row["is_correct"] is True]
    accuracy = (len(correct) / len(scored)) if scored else None
    lines = [
        f"# {spec.display}",
        "",
        f"- Samples analyzed: {len(rows)}",
        f"- Scored samples: {len(scored)}",
        f"- Incorrect scored samples: {len(wrong)}",
    ]
    if accuracy is not None:
        lines.append(f"- Rule-based accuracy: {accuracy:.3f}")
    if summary.get("judge_deferred"):
        lines.append("- Judge status: deferred. Patterns below summarize generated items pending later Qwen3-32B judging, not confirmed failures.")
    lines.extend(["", "## Top Patterns", "", "| Rank | Pattern | Count | TRACE Status | Closest TRACE Tasks | Suggested Action |", "|---:|---|---:|---|---|---|"])
    if not patterns:
        lines.append("| 1 | No parsed failures | 0 | n/a | n/a | n/a |")
    for index, pattern in enumerate(patterns, start=1):
        closest = ", ".join(f"`{task}`" for task in pattern["closest_trace_tasks"]) or "none"
        pattern_name = f"{pattern['intent']} / {pattern['metadata_label']}"
        lines.append(
            f"| {index} | {pattern_name} | {pattern['count']} | {pattern['trace_status']} | {closest} | {pattern['suggestion']} |"
        )
    lines.extend(["", "## Examples", ""])
    for index, pattern in enumerate(patterns[:5], start=1):
        lines.append(f"### {index}. {pattern['intent']} / {pattern['metadata_label']}")
        for example in pattern["examples"]:
            lines.append(f"- `{example['task_name']}:{example['doc_id']}` Q: {example['question']} | target: `{example['target']}` | response: `{example['response']}`")
        lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `normalized_items.jsonl` contains per-sample responses, scores, inferred pattern labels, and TRACE mapping fields.")
    lines.append("- `failure_patterns.jsonl` contains the pattern rows used for this markdown.")
    lines.append("")
    lines.append(f"Raw VERO sample files: {len(summary.get('sample_files', []))}")
    return "\n".join(lines)


def analyze_run(run_dir: Path, analysis_dir: Path, benchmarks: list[str]) -> None:
    root_rows = []
    root_lines = [
        "# Qwen2.5-VL-7B Sampled VERO Failure Analysis",
        "",
        f"Run root: `{run_dir}`",
        "",
        "Manual + automated coverage review: [CURATED_PATTERN_REVIEW.md](CURATED_PATTERN_REVIEW.md)",
        "",
        "| Benchmark | Items | Scored | Incorrect | Accuracy | Notes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for key in benchmarks:
        bench_dir = run_dir / key
        if not bench_dir.exists():
            root_lines.append(f"| {SPEC_BY_KEY[key].display} | 0 | 0 | 0 |  | missing run directory |")
            continue
        rows, summary = normalize_benchmark_samples(run_dir, key)
        judge_deferred = bool(summary.get("judge_deferred"))
        patterns = build_patterns(rows, judge_deferred)
        out_dir = analysis_dir / key
        write_jsonl(out_dir / "normalized_items.jsonl", rows)
        write_jsonl(out_dir / "failure_patterns.jsonl", patterns)
        (out_dir / f"{key}.md").write_text(markdown_for_benchmark(key, rows, patterns, summary), encoding="utf-8")
        scored = [row for row in rows if row["is_correct"] is not None]
        wrong = [row for row in scored if row["is_correct"] is False]
        correct = [row for row in scored if row["is_correct"] is True]
        accuracy = (len(correct) / len(scored)) if scored else None
        notes = "judge deferred" if judge_deferred else ""
        root_lines.append(
            f"| [{SPEC_BY_KEY[key].display}]({key}/{key}.md) | {len(rows)} | {len(scored)} | {len(wrong)} | {'' if accuracy is None else f'{accuracy:.3f}'} | {notes} |"
        )
        root_rows.append(
            {
                "benchmark": key,
                "display": SPEC_BY_KEY[key].display,
                "items": len(rows),
                "scored": len(scored),
                "incorrect": len(wrong),
                "accuracy": accuracy,
                "judge_deferred": judge_deferred,
                "patterns": patterns,
            }
        )
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / "README.md").write_text("\n".join(root_lines) + "\n", encoding="utf-8")
    write_json(analysis_dir / "summary.json", root_rows)
    print(f"[wrote] {analysis_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    parser.add_argument("--benchmarks", nargs="*", default=["all"])
    return parser.parse_args()


def normalize_keys(values: list[str]) -> list[str]:
    keys: list[str] = []
    for value in values:
        keys.extend(part.strip() for part in value.split(",") if part.strip())
    if not keys or "all" in keys:
        return [spec.key for spec in BENCHMARK_SPECS]
    unknown = [key for key in keys if key not in SPEC_BY_KEY]
    if unknown:
        raise SystemExit(f"Unknown benchmark key(s): {', '.join(unknown)}")
    return keys


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args.run_root, args.run_id)
    analysis_dir = output_root_for_run(args.analysis_root, run_dir)
    analyze_run(run_dir, analysis_dir, normalize_keys(args.benchmarks))


if __name__ == "__main__":
    main()
