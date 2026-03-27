#!/usr/bin/env python3
"""Run task review workflows with distribution reports and manual inspection workbook exports."""

from __future__ import annotations

import argparse
import io
import os
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Sequence

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage
from PIL import ImageOps as PILImageOps

from trace.core.answer_distribution import evaluate_answer_distribution
from trace.core.json_io import write_json_file
from trace.core.review_overlays import render_evidence_overlay, resolve_overlay_evidence
from trace.core.task_review_sampling import collect_variant_samples, generate_random_samples
from trace.tasks import TASK_REGISTRY, create_task


_PREVIEW_MAX_SIDE = 384
_EXCEL_HEADERS: List[str] = [
    "image",
    "evidence_image",
    "task",
    "task_variant",
    "prompt",
    "prompt_answer_only",
    "answer",
    "answer_evidence",
    "answer_type",
    "evidence_type",
    "instance_seed",
    "image_path",
    "data_path",
]

_EXCEL_COLUMN_WIDTHS: Dict[str, float] = {
    "A": 54,
    "B": 54,
    "C": 28,
    "D": 24,
    "E": 40,
    "F": 34,
    "G": 20,
    "H": 20,
    "I": 14,
    "J": 16,
    "K": 16,
    "L": 24,
    "M": 28,
}

_WRAP_COLUMNS = {"C", "D", "E", "F", "G", "H", "L", "M"}


def _resolve_task_ids(raw_tasks: str) -> List[str]:
    """Resolve selected task ids from CLI input."""
    if not str(raw_tasks).strip():
        return sorted(TASK_REGISTRY.keys())
    task_ids = [item.strip() for item in str(raw_tasks).split(",") if item.strip()]
    if not task_ids:
        raise ValueError("--tasks resolved to an empty list")
    unknown = [task_id for task_id in task_ids if task_id not in TASK_REGISTRY]
    if unknown:
        raise ValueError(f"unknown task ids: {', '.join(sorted(unknown))}")
    return sorted(dict.fromkeys(task_ids))


def _parse_cli() -> argparse.Namespace:
    """Parse CLI arguments for task-review workflow execution."""
    parser = argparse.ArgumentParser(description="Run TRACE task review workflow")
    parser.add_argument("--tasks", default="", help="Comma-separated task ids (default: all registered tasks)")
    parser.add_argument(
        "--mode",
        choices=["full", "distribution", "inspection"],
        default="full",
        help="full=random+distribution+inspection, distribution=random+distribution, inspection=excel-only",
    )
    parser.add_argument("--seed", type=int, default=0, help="Base seed")
    parser.add_argument("--out-root", default="task-reviews", help="Output root for task review artifacts")
    parser.add_argument("--random-count", type=int, default=100, help="Random sample count per task")
    parser.add_argument("--count-per-variant", type=int, default=100, help="Target samples per task variant")
    parser.add_argument("--inspection-count-per-variant", type=int, default=25, help="Samples per variant for inspection")
    parser.add_argument("--max-attempts-per-instance", type=int, default=200, help="Max attempts per instance generation")
    parser.add_argument(
        "--max-total-samples-per-task",
        type=int,
        default=30000,
        help="Safety cap while collecting per-variant samples",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, int(os.cpu_count() or 1)),
        help="Thread workers for sampling (default: all visible CPUs)",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="Exit 0 even when one or more distribution checks fail",
    )
    return parser.parse_args()


def _as_float(value: Any) -> float | None:
    """Parse one scalar as float when possible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None
    return None


def _normalize_probability_map(raw: Any) -> Dict[str, float]:
    """Normalize one probability/weight map into a sorted probability map."""
    if not isinstance(raw, Mapping):
        return {}
    parsed: Dict[str, float] = {}
    for key, value in raw.items():
        numeric = _as_float(value)
        if numeric is None:
            continue
        if float(numeric) <= 0.0:
            continue
        parsed[str(key)] = float(numeric)
    total = float(sum(parsed.values()))
    if total <= 0.0:
        return {}
    return {key: (float(parsed[key]) / total) for key in sorted(parsed.keys())}


def _extract_sampling_axes(output: Any) -> Dict[str, Dict[str, Any]]:
    """Extract sampling-axis observed values and expected probabilities from one output."""
    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        trace_payload = {}
    execution_trace = trace_payload.get("execution_trace", {})
    if not isinstance(execution_trace, Mapping):
        execution_trace = {}
    query_spec = trace_payload.get("query_spec", {})
    if not isinstance(query_spec, Mapping):
        query_spec = {}
    query_params = query_spec.get("params", {})
    if not isinstance(query_params, Mapping):
        query_params = {}

    axes: Dict[str, Dict[str, Any]] = {}

    def _set_axis(axis: str, *, observed: Any, expected: Mapping[str, float], source: str) -> None:
        axis_name = str(axis).strip()
        if not axis_name:
            return
        entry = axes.get(axis_name)
        expected_dict = dict(expected)
        if entry is None:
            axes[axis_name] = {
                "observed": "" if observed is None else str(observed),
                "expected_probabilities": expected_dict,
                "expected_source": str(source),
                "expected_conflict": False,
            }
            return
        if entry.get("observed") in {"", None} and observed is not None:
            entry["observed"] = str(observed)
        existing_expected = entry.get("expected_probabilities", {})
        if existing_expected and existing_expected != expected_dict:
            entry["expected_conflict"] = True
        elif (not existing_expected) and expected_dict:
            entry["expected_probabilities"] = expected_dict
            entry["expected_source"] = str(source)

    for source_name, source in (("execution_trace", execution_trace), ("query_params", query_params)):
        if not isinstance(source, Mapping):
            continue
        for key, value in source.items():
            key_text = str(key)
            if not key_text.endswith("_probabilities"):
                continue
            axis = key_text[: -len("_probabilities")]
            probs = _normalize_probability_map(value)
            if not probs:
                continue
            observed = None
            if str(axis) == "task_variant":
                observed = getattr(output, "task_variant", "")
            else:
                observed = execution_trace.get(str(axis), query_params.get(str(axis), ""))
            _set_axis(str(axis), observed=observed, expected=probs, source=str(source_name))

    if "task_variant" not in axes:
        axes["task_variant"] = {
            "observed": str(getattr(output, "task_variant", "") or ""),
            "expected_probabilities": {},
            "expected_source": "",
            "expected_conflict": False,
        }
    return axes


def _random_collector(output: Any, instance_seed: int) -> Dict[str, Any]:
    """Collect task-review fields from one generated output."""
    return {
        "instance_seed": int(instance_seed),
        "task_variant": str(getattr(output, "task_variant", "") or ""),
        "answer_type": str(output.answer_gt.type),
        "answer_value": output.answer_gt.value,
        "sampling_axes": _extract_sampling_axes(output),
    }


def _answer_collector(output: Any, instance_seed: int) -> Dict[str, Any]:
    """Collect answer-only fields for distribution checks."""
    return {
        "instance_seed": int(instance_seed),
        "task_variant": str(getattr(output, "task_variant", "") or ""),
        "answer_type": str(output.answer_gt.type),
        "answer_value": output.answer_gt.value,
    }


def _has_true_variants(variant_counts: Mapping[str, int], expected_probabilities: Mapping[str, float]) -> bool:
    """Return true when a task has more than one meaningful variant."""
    expected_non_empty = [str(key) for key in expected_probabilities.keys() if str(key).strip()]
    if len(expected_non_empty) > 1:
        return True
    observed_non_empty = [str(key) for key, value in variant_counts.items() if str(key).strip() and int(value) > 0]
    return len(observed_non_empty) > 1


def _build_sampling_axis_reports(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build observed/expected sampling distribution report for all discovered axes."""
    axis_names: set[str] = set()
    for row in rows:
        axes = row.get("sampling_axes", {})
        if isinstance(axes, Mapping):
            axis_names.update(str(axis) for axis in axes.keys())

    reports: Dict[str, Dict[str, Any]] = {}
    for axis in sorted(axis_names):
        observed_counts: Dict[str, int] = {}
        expected_map: Dict[str, float] = {}
        expected_conflict = False
        expected_source = ""

        for row in rows:
            axes = row.get("sampling_axes", {})
            axis_entry = axes.get(axis, {}) if isinstance(axes, Mapping) else {}
            observed = axis_entry.get("observed")
            observed_label = str(observed) if observed is not None else ""
            if str(axis) == "task_variant" and not observed_label:
                observed_label = str(row.get("task_variant", "") or "")
            observed_counts[observed_label] = int(observed_counts.get(observed_label, 0) + 1)

            raw_expected = axis_entry.get("expected_probabilities", {}) if isinstance(axis_entry, Mapping) else {}
            normalized_expected = _normalize_probability_map(raw_expected)
            if normalized_expected:
                if not expected_map:
                    expected_map = dict(normalized_expected)
                    expected_source = str(axis_entry.get("expected_source", ""))
                elif expected_map != normalized_expected:
                    expected_conflict = True
            if bool(axis_entry.get("expected_conflict", False)):
                expected_conflict = True

        total = int(sum(observed_counts.values()))
        max_count = int(max(observed_counts.values())) if observed_counts else 0
        reports[str(axis)] = {
            "sample_count": int(total),
            "observed_counts": dict(sorted(observed_counts.items(), key=lambda item: item[0])),
            "max_observed_frequency": (float(max_count) / float(total)) if int(total) > 0 else 0.0,
            "expected_probabilities": dict(expected_map),
            "expected_source": str(expected_source),
            "expected_conflict": bool(expected_conflict),
        }

    return reports


def _build_random_review_report(*, task_id: str, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build random-sample review report for one task."""
    answer_rows = [
        {
            "answer_type": str(row.get("answer_type", "")),
            "answer_value": row.get("answer_value"),
        }
        for row in rows
    ]
    answer_report = evaluate_answer_distribution(answer_rows)
    sampling_axes = _build_sampling_axis_reports(rows)
    variant_axis = sampling_axes.get("task_variant", {})
    variant_counts = variant_axis.get("observed_counts", {}) if isinstance(variant_axis, Mapping) else {}
    variant_expected = variant_axis.get("expected_probabilities", {}) if isinstance(variant_axis, Mapping) else {}
    has_variants = _has_true_variants(variant_counts, variant_expected)

    return {
        "task_id": str(task_id),
        "sample_count": int(len(rows)),
        "answer_distribution": answer_report,
        "sampling_axes": sampling_axes,
        "task_variant_distribution": {
            "has_variants": bool(has_variants),
            "status": "reported" if bool(has_variants) else "skipped_no_variants",
            "observed_counts": dict(variant_counts),
            "expected_probabilities": dict(variant_expected),
            "expected_source": str(variant_axis.get("expected_source", "")) if isinstance(variant_axis, Mapping) else "",
            "expected_conflict": bool(variant_axis.get("expected_conflict", False)) if isinstance(variant_axis, Mapping) else False,
        },
    }


def _evaluate_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Evaluate standard answer-distribution checks for one row slice."""
    answer_rows = [
        {
            "answer_type": str(row.get("answer_type", "")),
            "answer_value": row.get("answer_value"),
        }
        for row in rows
    ]
    if not answer_rows:
        return {
            "sample_count": 0,
            "unique_answers": 0,
            "max_answer_count": 0,
            "max_answer_frequency": 0.0,
            "checks": {
                "min_unique_answers": {"pass": False},
                "max_answer_frequency": {"pass": False},
                "max_five_bin_frequency": {"pass": None, "observed": None, "status": "not_reported_no_samples"},
            },
            "pass": False,
        }
    return evaluate_answer_distribution(answer_rows)


def _build_distribution_review_report(
    *,
    task_id: str,
    task_group: str,
    domain: str,
    random_rows: Sequence[Mapping[str, Any]],
    random_report: Mapping[str, Any],
    variant_rows: Mapping[str, List[Dict[str, Any]]] | None,
    variant_collection_meta: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    """Build distribution review report from random and per-variant samples."""
    variant_distribution = random_report.get("task_variant_distribution", {})
    has_variants = bool(variant_distribution.get("has_variants", False))

    if not has_variants:
        single_report = _evaluate_rows(random_rows)
        return {
            "task_id": str(task_id),
            "domain": str(domain),
            "task_group": str(task_group),
            "mode": "single_sample",
            "has_task_variants": False,
            "overall": dict(single_report),
            "per_task_variant": {"": dict(single_report)},
            "failed_variants": [""] if not bool(single_report.get("pass", False)) else [],
            "incomplete_variants": [],
            "pass": bool(single_report.get("pass", False)),
            "task_variant_distribution": dict(variant_distribution),
            "sampling_axes": dict(random_report.get("sampling_axes", {})),
        }

    variant_rows = variant_rows or {}
    variant_collection_meta = variant_collection_meta or {}
    expected_variants = list(variant_collection_meta.get("expected_variants", []))
    if not expected_variants:
        expected_variants = sorted(variant_rows.keys())
    per_variant: Dict[str, Any] = {}
    combined_rows: List[Dict[str, Any]] = []

    for task_variant in expected_variants:
        rows = list(variant_rows.get(str(task_variant), []))
        combined_rows.extend(rows)
        if rows:
            per_variant[str(task_variant)] = _evaluate_rows(rows)

    overall = _evaluate_rows(combined_rows)
    failed_variants = [
        str(task_variant)
        for task_variant, result in per_variant.items()
        if not bool(result.get("pass", False))
    ]
    incomplete_variants = list(variant_collection_meta.get("incomplete_variants", []))
    no_samples_collected = not bool(combined_rows)
    task_pass = bool((not failed_variants) and (not incomplete_variants) and (not no_samples_collected))

    return {
        "task_id": str(task_id),
        "domain": str(domain),
        "task_group": str(task_group),
        "mode": "per_variant",
        "has_task_variants": True,
        "overall": overall,
        "per_task_variant": per_variant,
        "failed_variants": failed_variants,
        "incomplete_variants": incomplete_variants,
        "no_samples_collected": bool(no_samples_collected),
        "pass": bool(task_pass),
        "task_variant_distribution": dict(variant_distribution),
        "sampling_axes": dict(random_report.get("sampling_axes", {})),
        "collection": {
            "target_count_per_variant": int(variant_collection_meta.get("target_count_per_variant", 0)),
            "total_generated": int(variant_collection_meta.get("total_generated", 0)),
            "expected_variants": list(expected_variants),
            "generated_variant_counts": dict(variant_collection_meta.get("generated_variant_counts", {})),
            "collected_variant_counts": dict(variant_collection_meta.get("collected_variant_counts", {})),
            "generation_error_counts": dict(variant_collection_meta.get("generation_error_counts", {})),
        },
    }


def _build_preview_image(source: PILImage.Image, *, max_image_side: int = _PREVIEW_MAX_SIDE) -> PILImage.Image:
    """Resize and border one preview image for workbook embedding."""
    preview = source.convert("RGB")
    border_px = 1
    inner_max_side = max(1, int(max_image_side) - (2 * border_px))
    preview.thumbnail((inner_max_side, inner_max_side), PILImage.Resampling.LANCZOS)
    return PILImageOps.expand(preview, border=border_px, fill=(0, 0, 0))


def _json_cell(value: Any) -> str:
    """Serialize nested values for workbook cells."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    return "" if value is None else str(value)


def _sanitize_sheet_title(raw: str) -> str:
    """Return one Excel-safe sheet title."""
    title = re.sub(r"[\\\\/*?:\\[\\]]+", "_", str(raw).strip())
    if not title:
        return "default"
    return title[:31]


def _dedupe_sheet_title(base: str, used: set[str]) -> str:
    """Return one unique Excel-safe sheet title."""
    candidate = _sanitize_sheet_title(base)
    if candidate not in used:
        used.add(candidate)
        return candidate
    index = 2
    while True:
        suffix = f"_{index}"
        trimmed = candidate[: max(1, 31 - len(suffix))]
        attempt = f"{trimmed}{suffix}"
        if attempt not in used:
            used.add(attempt)
            return attempt
        index += 1


def _populate_inspection_sheet(
    sheet: Any,
    *,
    rows: Sequence[Mapping[str, Any]],
    out_root: Path,
    image_buffers: List[io.BytesIO],
) -> None:
    """Populate one inspection sheet with preview images and metadata rows."""
    sheet.append(list(_EXCEL_HEADERS))

    bold = Font(bold=True)
    for column in range(1, len(_EXCEL_HEADERS) + 1):
        sheet.cell(row=1, column=column).font = bold

    for letter, width in _EXCEL_COLUMN_WIDTHS.items():
        sheet.column_dimensions[str(letter)].width = float(width)

    wrap_top = Alignment(wrap_text=True, vertical="top")

    for row_idx, row in enumerate(rows, start=2):
        image_path = out_root / str(row.get("image_path", ""))
        if image_path.exists():
            with PILImage.open(image_path) as source:
                source_rgb = source.convert("RGB")
                preview = _build_preview_image(source_rgb)
                evidence_preview = _build_preview_image(
                    render_evidence_overlay(
                        source_rgb,
                        evidence_type=str(row.get("overlay_evidence_type", row.get("evidence_type", ""))),
                        evidence_value=row.get("overlay_evidence_value", row.get("answer_evidence")),
                    )
                )
                row_height = max(int(preview.height), int(evidence_preview.height))

                preview_buffer = io.BytesIO()
                preview.save(preview_buffer, format="PNG")
                preview_buffer.seek(0)
                image_buffers.append(preview_buffer)

                evidence_buffer = io.BytesIO()
                evidence_preview.save(evidence_buffer, format="PNG")
                evidence_buffer.seek(0)
                image_buffers.append(evidence_buffer)

            preview_img = XLImage(preview_buffer)
            preview_img.anchor = f"A{row_idx}"
            sheet.add_image(preview_img)

            evidence_img = XLImage(evidence_buffer)
            evidence_img.anchor = f"B{row_idx}"
            sheet.add_image(evidence_img)

            sheet.row_dimensions[row_idx].height = max(60, float(row_height) * 0.75)
        else:
            sheet.row_dimensions[row_idx].height = 60

        values = [
            row.get("task", ""),
            row.get("task_variant", ""),
            row.get("prompt", ""),
            row.get("prompt_answer_only", ""),
            _json_cell(row.get("answer")),
            _json_cell(row.get("answer_evidence")),
            row.get("answer_type", ""),
            row.get("evidence_type", ""),
            int(row.get("instance_seed", 0)),
            row.get("image_path", ""),
            row.get("data_path", ""),
        ]
        for offset, value in enumerate(values, start=3):
            cell = sheet.cell(row=row_idx, column=offset, value=value)
            if get_column_letter(offset) in _WRAP_COLUMNS:
                cell.alignment = wrap_top

    sheet.freeze_panes = "C2"


def _write_inspection_excel(
    rows_by_variant: Mapping[str, Sequence[Mapping[str, Any]]],
    path: Path,
    *,
    out_root: Path,
) -> Dict[str, str]:
    """Write one inspection workbook with one sheet per task variant."""
    workbook = Workbook()
    image_buffers: List[io.BytesIO] = []
    used_titles: set[str] = set()
    variant_to_sheet: Dict[str, str] = {}

    sorted_variants = sorted(str(variant) for variant in rows_by_variant.keys())
    if not sorted_variants:
        sorted_variants = [""]

    for index, task_variant in enumerate(sorted_variants):
        base_title = str(task_variant).strip() or "default"
        sheet_title = _dedupe_sheet_title(base_title, used_titles)
        if int(index) == 0:
            sheet = workbook.active
            sheet.title = sheet_title
        else:
            sheet = workbook.create_sheet(title=sheet_title)
        variant_to_sheet[str(task_variant)] = str(sheet_title)
        _populate_inspection_sheet(
            sheet,
            rows=list(rows_by_variant.get(str(task_variant), [])),
            out_root=out_root,
            image_buffers=image_buffers,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return variant_to_sheet


def _safe_variant_dir_name(task_variant: str) -> str:
    """Return filesystem-safe variant directory label."""
    value = str(task_variant).strip()
    if not value:
        return "default"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value)


def _build_inspection_rows(
    *,
    task_id: str,
    out_root: Path,
    task_dir: Path,
    seed_rows_by_variant: Mapping[str, Sequence[Mapping[str, Any]]],
    max_attempts_per_instance: int,
) -> Dict[str, Any]:
    """Generate inspection artifacts (images/json/workbook rows) for one task."""
    rows_by_variant: Dict[str, List[Dict[str, Any]]] = {}
    task = create_task(str(task_id))

    for task_variant in sorted(seed_rows_by_variant.keys()):
        variant_dir = _safe_variant_dir_name(str(task_variant))
        image_dir = task_dir / "images" / variant_dir
        data_dir = task_dir / "data" / variant_dir
        image_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        seed_rows = list(seed_rows_by_variant.get(str(task_variant), []))
        for index, seed_row in enumerate(seed_rows):
            instance_seed = int(seed_row.get("instance_seed", 0))
            generation_params: Dict[str, Any] = {}
            if str(task_variant).strip():
                generation_params["task_variant"] = str(task_variant)
            output = task.generate(
                instance_seed,
                params=generation_params,
                max_attempts=int(max_attempts_per_instance),
            )

            image_path = image_dir / f"{index:04d}.png"
            output.image.save(image_path, format="PNG")
            rel_image_path = image_path.relative_to(out_root).as_posix()

            prompt_variants = dict(getattr(output, "prompt_variants", {}) or {})
            prompt_answer_only = str(prompt_variants.get("answer_only", output.prompt))
            prompt_answer_and_evidence = str(prompt_variants.get("answer_and_evidence", output.prompt))

            data_payload = {
                "task": str(task_id),
                "task_variant": str(getattr(output, "task_variant", "") or ""),
                "instance_seed": int(instance_seed),
                "prompt": prompt_answer_and_evidence,
                "prompt_variants": prompt_variants,
                "answer_gt": output.answer_gt.to_dict(),
                "evidence_gt": output.evidence_gt.to_dict(),
                "image": {
                    "path": str(rel_image_path),
                    "format": "png",
                },
                "trace_payload": dict(output.trace_payload),
                "versions": dict(output.task_versions),
            }
            data_path = data_dir / f"{index:04d}.json"
            write_json_file(data_path, data_payload)
            rel_data_path = data_path.relative_to(out_root).as_posix()

            overlay_evidence_type, overlay_evidence_value = resolve_overlay_evidence(
                evidence_type=str(output.evidence_gt.type),
                evidence_value=output.evidence_gt.value,
                trace_payload=output.trace_payload if isinstance(output.trace_payload, Mapping) else {},
            )
            canonical_answer = {
                "evidence": output.evidence_gt.value,
                "answer": output.answer_gt.value,
            }
            output_variant = str(getattr(output, "task_variant", "") or "")
            variant_rows = rows_by_variant.setdefault(str(output_variant), [])
            variant_rows.append(
                {
                    "task": str(task_id),
                    "task_variant": str(output_variant),
                    "prompt": prompt_answer_and_evidence,
                    "prompt_answer_only": prompt_answer_only,
                    "answer": canonical_answer,
                    "answer_evidence": output.evidence_gt.value,
                    "answer_type": str(output.answer_gt.type),
                    "evidence_type": str(output.evidence_gt.type),
                    "instance_seed": int(instance_seed),
                    "image_path": str(rel_image_path),
                    "data_path": str(rel_data_path),
                    "overlay_evidence_type": str(overlay_evidence_type),
                    "overlay_evidence_value": overlay_evidence_value,
                }
            )

    inspection_total = 0
    for task_variant in sorted(rows_by_variant.keys()):
        rows_by_variant[str(task_variant)] = sorted(
            list(rows_by_variant.get(str(task_variant), [])),
            key=lambda item: int(item.get("instance_seed", 0)),
        )
        inspection_total += int(len(rows_by_variant[str(task_variant)]))

    workbook_path = task_dir / f"{task_id}.xlsx"
    workbook_sheets = _write_inspection_excel(rows_by_variant, workbook_path, out_root=out_root)

    manifest = {
        "task_id": str(task_id),
        "inspection_count": int(inspection_total),
        "variants": {
            str(variant): int(len(seed_rows_by_variant.get(str(variant), [])))
            for variant in sorted(seed_rows_by_variant.keys())
        },
        "workbook": str(workbook_path.relative_to(out_root).as_posix()),
        "workbook_sheets": dict(workbook_sheets),
    }
    write_json_file(task_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    """Entry point for task-review workflow execution."""
    args = _parse_cli()
    if int(args.random_count) <= 0:
        raise ValueError("--random-count must be > 0")
    if int(args.count_per_variant) <= 0:
        raise ValueError("--count-per-variant must be > 0")
    if int(args.inspection_count_per_variant) <= 0:
        raise ValueError("--inspection-count-per-variant must be > 0")
    if int(args.max_attempts_per_instance) <= 0:
        raise ValueError("--max-attempts-per-instance must be > 0")
    if int(args.max_total_samples_per_task) <= 0:
        raise ValueError("--max-total-samples-per-task must be > 0")
    if int(args.workers) <= 0:
        raise ValueError("--workers must be > 0")

    task_ids = _resolve_task_ids(str(args.tasks))
    out_root = Path(str(args.out_root)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "config": {
            "mode": str(args.mode),
            "seed": int(args.seed),
            "tasks": list(task_ids),
            "random_count": int(args.random_count),
            "count_per_variant": int(args.count_per_variant),
            "inspection_count_per_variant": int(args.inspection_count_per_variant),
            "max_attempts_per_instance": int(args.max_attempts_per_instance),
            "max_total_samples_per_task": int(args.max_total_samples_per_task),
            "workers": int(args.workers),
        },
        "tasks": [],
    }

    failed_distribution_tasks: List[str] = []

    for task_id in task_ids:
        task = create_task(str(task_id))
        task_dir = out_root / str(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        task_summary: Dict[str, Any] = {
            "task_id": str(task_id),
            "domain": str(task.domain),
            "task_group": str(task.task_group),
            "reports": {},
        }

        random_rows: List[Dict[str, Any]] = []
        random_report: Dict[str, Any] | None = None
        distribution_variant_rows: Dict[str, List[Dict[str, Any]]] | None = None

        if str(args.mode) in {"full", "distribution"}:
            random_rows = generate_random_samples(
                task_id=str(task_id),
                count=int(args.random_count),
                seed=int(args.seed),
                max_attempts_per_instance=int(args.max_attempts_per_instance),
                workers=int(args.workers),
                collector=_random_collector,
            )
            random_report = _build_random_review_report(task_id=str(task_id), rows=random_rows)
            random_path = task_dir / "random_review_100.json"
            write_json_file(random_path, random_report)
            task_summary["reports"]["random_review"] = str(random_path.relative_to(out_root).as_posix())

            has_variants = bool(random_report["task_variant_distribution"]["has_variants"])
            variant_rows: Dict[str, List[Dict[str, Any]]] | None = None
            collection_meta: Dict[str, Any] | None = None
            if has_variants:
                collected = collect_variant_samples(
                    task_id=str(task_id),
                    target_count_per_variant=int(args.count_per_variant),
                    seed=int(args.seed),
                    max_attempts_per_instance=int(args.max_attempts_per_instance),
                    max_total_samples_per_task=int(args.max_total_samples_per_task),
                    workers=int(args.workers),
                    collector=_answer_collector,
                )
                variant_rows = {
                    str(variant): list(collected.get("samples_by_variant", {}).get(str(variant), []))
                    for variant in list(collected.get("expected_variants", []))
                }
                distribution_variant_rows = dict(variant_rows)
                collection_meta = {
                    key: collected.get(key)
                    for key in (
                        "target_count_per_variant",
                        "total_generated",
                        "expected_variants",
                        "generated_variant_counts",
                        "collected_variant_counts",
                        "incomplete_variants",
                        "generation_error_counts",
                    )
                }

            distribution_report = _build_distribution_review_report(
                task_id=str(task_id),
                task_group=str(task.task_group),
                domain=str(task.domain),
                random_rows=random_rows,
                random_report=random_report,
                variant_rows=variant_rows,
                variant_collection_meta=collection_meta,
            )
            dist_path = task_dir / "distribution_review.json"
            write_json_file(dist_path, distribution_report)
            task_summary["reports"]["distribution_review"] = str(dist_path.relative_to(out_root).as_posix())
            task_summary["distribution_pass"] = bool(distribution_report.get("pass", False))
            if not bool(distribution_report.get("pass", False)):
                failed_distribution_tasks.append(str(task_id))

            status = "PASS" if bool(distribution_report.get("pass", False)) else "FAIL"
            print(f"[{status}] {task_id} distribution review")

        if str(args.mode) in {"full", "inspection"}:
            if str(args.mode) == "inspection":
                random_rows_for_inspection = None
            else:
                random_rows_for_inspection = random_rows

            seed_rows_by_variant: Dict[str, List[Dict[str, Any]]]
            if random_report is None:
                inspection_collected = collect_variant_samples(
                    task_id=str(task_id),
                    target_count_per_variant=int(args.inspection_count_per_variant),
                    seed=int(args.seed) + 17,
                    max_attempts_per_instance=int(args.max_attempts_per_instance),
                    max_total_samples_per_task=int(args.max_total_samples_per_task),
                    workers=int(args.workers),
                    collector=_answer_collector,
                )
                expected_variants = list(inspection_collected.get("expected_variants", []))
                if not expected_variants:
                    expected_variants = sorted(inspection_collected.get("samples_by_variant", {}).keys())
                seed_rows_by_variant = {
                    str(variant): list(inspection_collected.get("samples_by_variant", {}).get(str(variant), []))
                    for variant in expected_variants
                }
                if not seed_rows_by_variant:
                    fallback_rows = generate_random_samples(
                        task_id=str(task_id),
                        count=int(args.inspection_count_per_variant),
                        seed=int(args.seed) + 17,
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                    seed_rows_by_variant = {"": list(fallback_rows)}
            elif bool(random_report["task_variant_distribution"]["has_variants"]):
                if distribution_variant_rows is not None and str(args.mode) == "full":
                    seed_rows_by_variant = {
                        str(variant): list(rows[: int(args.inspection_count_per_variant)])
                        for variant, rows in distribution_variant_rows.items()
                    }
                else:
                    inspection_collected = collect_variant_samples(
                        task_id=str(task_id),
                        target_count_per_variant=int(args.inspection_count_per_variant),
                        seed=int(args.seed) + 17,
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        max_total_samples_per_task=int(args.max_total_samples_per_task),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                    seed_rows_by_variant = {
                        str(variant): list(inspection_collected.get("samples_by_variant", {}).get(str(variant), []))
                        for variant in list(inspection_collected.get("expected_variants", []))
                    }
            else:
                if random_rows_for_inspection is None:
                    random_rows_for_inspection = generate_random_samples(
                        task_id=str(task_id),
                        count=int(args.inspection_count_per_variant),
                        seed=int(args.seed) + 17,
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                seed_rows_by_variant = {
                    "": list(random_rows_for_inspection[: int(args.inspection_count_per_variant)]),
                }

            inspection_manifest = _build_inspection_rows(
                task_id=str(task_id),
                out_root=out_root,
                task_dir=task_dir,
                seed_rows_by_variant=seed_rows_by_variant,
                max_attempts_per_instance=int(args.max_attempts_per_instance),
            )
            task_summary["reports"]["inspection_manifest"] = str(
                (task_dir / "manifest.json").relative_to(out_root).as_posix()
            )
            task_summary["inspection_count"] = int(inspection_manifest.get("inspection_count", 0))
            task_summary["inspection_workbook"] = str(inspection_manifest.get("workbook", ""))
            task_summary["inspection_workbook_sheets"] = dict(inspection_manifest.get("workbook_sheets", {}))
            workbook_hint = str(task_summary["inspection_workbook"]) or "none"
            sheet_count = len(task_summary["inspection_workbook_sheets"])
            print(
                f"[done] {task_id} inspection workbook: {workbook_hint} (sheets={sheet_count})"
            )

        summary["tasks"].append(task_summary)

    summary["summary"] = {
        "total_tasks": int(len(task_ids)),
        "distribution_tasks_failed": int(len(failed_distribution_tasks)),
        "failed_distribution_task_ids": sorted(failed_distribution_tasks),
    }
    summary_path = out_root / "review_summary.json"
    write_json_file(summary_path, summary)
    print(f"[done] wrote review summary: {summary_path}")

    if failed_distribution_tasks and str(args.mode) in {"full", "distribution"} and not bool(args.allow_fail):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
