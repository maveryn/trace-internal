#!/usr/bin/env python3
"""Generate task sample images/data plus per-task and per-domain combined review workbooks."""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage
from PIL import ImageDraw as PILImageDraw
from PIL import ImageOps as PILImageOps

from trace.core.json_io import write_json_file
from trace.core.query_types import resolve_query_types
from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY, create_task


_FIELD_LABELS: Dict[str, str] = {
    "domain": "domain",
    "task_group": "task_group",
    "task": "task",
    "sample_index": "sample_index",
    "instance_seed": "instance_seed",
    "query_type": "query_type",
    "image_path": "image_path",
    "data_path": "data_path",
    "prompt": "prompt",
    "prompt_answer_only": "prompt_answer_only",
    "answer": "answer",
    "answer_type": "answer_type",
    "answer_value": "answer_value",
    "evidence_type": "evidence_type",
    "answer_evidence": "answer_evidence",
}

_TASK_SHEET_FIELDS: List[str] = [
    "task",
    "query_type",
    "prompt",
    "prompt_answer_only",
    "answer",
    "answer_evidence",
    "domain",
    "task_group",
    "sample_index",
    "instance_seed",
    "image_path",
    "data_path",
    "answer_type",
    "evidence_type",
]

_COLUMN_WIDTHS_BY_FIELD: Dict[str, float] = {
    "domain": 12,
    "task_group": 16,
    "task": 24,
    "sample_index": 12,
    "instance_seed": 20,
    "query_type": 20,
    "image_path": 22,
    "data_path": 38,
    "prompt": 34,
    "prompt_answer_only": 34,
    "answer": 20,
    "answer_type": 14,
    "answer_value": 12,
    "evidence_type": 14,
    "answer_evidence": 18,
}

_PREVIEW_COLUMN_WIDTH = 56
_INT_FIELDS = {"sample_index", "instance_seed"}
_JSON_FIELDS = {"answer", "answer_value", "answer_evidence"}
_WRAP_FIELDS = {
    "task",
    "image_path",
    "data_path",
    "prompt",
    "prompt_answer_only",
    "answer",
    "answer_value",
    "answer_evidence",
}
_TASK_WRAP_MAX_CHARS = 20

_TASK_PREVIEW_MAX_SIDE = 384
_EVIDENCE_COLORS: List[Tuple[int, int, int]] = [
    (230, 57, 70),
    (69, 123, 157),
    (46, 139, 87),
    (247, 127, 0),
    (126, 87, 194),
    (0, 150, 136),
    (156, 39, 176),
    (255, 111, 0),
]

_UNIFORMITY_THRESHOLDS: Dict[str, float] = {
    "min_samples_per_query": 80.0,
    "mean_z_max": 3.0,
    "max_bin_count_z_max": 4.0,
    "tv_distance_max": 0.20,
    "std_ratio_min": 0.60,
    "std_ratio_max": 1.40,
}


def _parse_json_dict(raw: str, *, arg_name: str) -> Dict[str, Any]:
    """Parse CLI JSON object argument into a dictionary."""
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{arg_name} must be a JSON object")
    return dict(value)


def _resolve_task_ids(raw_tasks: str) -> List[str]:
    """Resolve target task ids from CLI input or registry defaults."""
    if not raw_tasks.strip():
        return sorted(TASK_REGISTRY.keys())
    task_ids = [item.strip() for item in raw_tasks.split(",") if item.strip()]
    if not task_ids:
        raise ValueError("--tasks resolved to an empty list")
    unknown = [task_id for task_id in task_ids if task_id not in TASK_REGISTRY]
    if unknown:
        raise ValueError(f"unknown task ids: {', '.join(sorted(unknown))}")
    return sorted(dict.fromkeys(task_ids))


def _json_cell(value: Any) -> str:
    """Serialize nested values for spreadsheet cells."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    return "" if value is None else str(value)


def _field_value_for_sheet(row: Dict[str, Any], field: str) -> Any:
    """Return one row field value formatted for spreadsheet export."""
    value = row.get(field)
    if field == "task":
        return _wrap_task_label(str(value))
    if field in _INT_FIELDS:
        return int(value)
    if field in _JSON_FIELDS:
        return _json_cell(value)
    return value


def _wrap_task_label(value: str) -> str:
    """Wrap long underscore-separated task ids into multiple lines for readability."""
    text = str(value).strip()
    if not text or "_" not in text:
        return text

    parts = text.split("_")
    lines: List[str] = []
    current = ""
    for idx, part in enumerate(parts):
        suffix = "_" if idx < len(parts) - 1 else ""
        token = f"{part}{suffix}"
        if current and (len(current) + len(token)) > int(_TASK_WRAP_MAX_CHARS):
            lines.append(current)
            current = token
        else:
            current = f"{current}{token}"
    if current:
        lines.append(current)
    return "\n".join(lines)


def _parse_point(value: Any) -> Tuple[float, float] | None:
    """Parse one point-like value as `(x, y)` floats."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        x = _as_float_number(value[0])
        y = _as_float_number(value[1])
        if x is None or y is None:
            return None
        return (float(x), float(y))
    return None


def _parse_bbox(value: Any) -> Tuple[float, float, float, float] | None:
    """Parse one bbox-like value as `(x0, y0, x1, y1)` floats."""
    if isinstance(value, (list, tuple)) and len(value) == 4:
        parsed = [_as_float_number(item) for item in value]
        if any(item is None for item in parsed):
            return None
        x0, y0, x1, y1 = (float(parsed[0]), float(parsed[1]), float(parsed[2]), float(parsed[3]))
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, y0, x1, y1)
    return None


def _extract_points(value: Any) -> List[Tuple[float, float]]:
    """Extract list of points from evidence payload when possible."""
    point = _parse_point(value)
    if point is not None:
        return [point]
    if isinstance(value, list):
        out: List[Tuple[float, float]] = []
        for item in value:
            parsed = _parse_point(item)
            if parsed is not None:
                out.append(parsed)
        return out
    if isinstance(value, dict):
        out: List[Tuple[float, float]] = []
        for item in value.values():
            parsed = _parse_point(item)
            if parsed is not None:
                out.append(parsed)
        return out
    return []


def _extract_point_map(value: Any) -> Dict[str, Tuple[float, float]]:
    """Extract label->point mapping from evidence payload when possible."""
    if not isinstance(value, dict):
        return {}
    out: Dict[str, Tuple[float, float]] = {}
    for key, raw_point in value.items():
        parsed = _parse_point(raw_point)
        if parsed is None:
            continue
        out[str(key)] = (float(parsed[0]), float(parsed[1]))
    return out


def _extract_bboxes(value: Any) -> List[Tuple[float, float, float, float]]:
    """Extract list of bboxes from evidence payload when possible."""
    bbox = _parse_bbox(value)
    if bbox is not None:
        return [bbox]
    if isinstance(value, list):
        out: List[Tuple[float, float, float, float]] = []
        for item in value:
            parsed = _parse_bbox(item)
            if parsed is not None:
                out.append(parsed)
        return out
    return []


def _render_evidence_overlay(source: PILImage.Image, *, evidence_type: str, evidence_value: Any) -> PILImage.Image:
    """Render evidence markers over an RGB source image."""
    image = source.convert("RGB")
    draw = PILImageDraw.Draw(image, mode="RGBA")
    width, height = image.size
    radius = max(3, int(round(min(width, height) * 0.009)))
    line_width = max(2, int(round(min(width, height) * 0.006)))
    query_type = str(evidence_type)

    if query_type in {"point_map", "grid_point_map", "annotation_centers"}:
        point_map = _extract_point_map(evidence_value)
        for idx, (label, point) in enumerate(point_map.items()):
            x, y = float(point[0]), float(point[1])
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(color[0], color[1], color[2], 255),
                outline=(0, 0, 0, 255),
                width=1,
            )
            draw.text(
                (x + float(radius) + 2.0, y - float(radius) - 1.0),
                str(label),
                fill=(color[0], color[1], color[2], 255),
            )
        return image

    if query_type in {"point", "point_set", "point_path"}:
        points = _extract_points(evidence_value)
        if query_type == "point_path" and len(points) >= 2:
            draw.line(points, fill=(220, 20, 60, 180), width=line_width)
        for idx, (x, y) in enumerate(points):
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(color[0], color[1], color[2], 255),
                outline=(0, 0, 0, 255),
                width=1,
            )
        return image

    if query_type in {"bbox", "bbox_set"}:
        bboxes = _extract_bboxes(evidence_value)
        for idx, (x0, y0, x1, y1) in enumerate(bboxes):
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.rectangle([x0, y0, x1, y1], outline=(color[0], color[1], color[2], 255), width=line_width)
        return image

    # Best-effort fallback for unrecognized evidence types.
    points = _extract_points(evidence_value)
    for idx, (x, y) in enumerate(points):
        color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(color[0], color[1], color[2], 255),
            outline=(0, 0, 0, 255),
            width=1,
        )
    bboxes = _extract_bboxes(evidence_value)
    for idx, (x0, y0, x1, y1) in enumerate(bboxes):
        color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
        draw.rectangle([x0, y0, x1, y1], outline=(color[0], color[1], color[2], 255), width=line_width)
    return image


def _build_preview_image(source: PILImage.Image, *, max_image_side: int) -> PILImage.Image:
    """Resize and border one preview image without mutating source image."""
    preview = source.convert("RGB")
    border_px = 1
    inner_max_side = max(1, int(max_image_side) - (2 * border_px))
    preview.thumbnail((inner_max_side, inner_max_side), PILImage.Resampling.LANCZOS)
    return PILImageOps.expand(preview, border=border_px, fill=(0, 0, 0))


def _configure_sheet_columns(sheet: Any, fields: List[str], *, start_col: int = 1) -> None:
    """Apply configured column widths for a field sequence."""
    for idx, field in enumerate(fields, start=start_col):
        letter = get_column_letter(idx)
        sheet.column_dimensions[letter].width = _COLUMN_WIDTHS_BY_FIELD.get(field, 20)


def _populate_task_review_sheet(
    sheet: Any,
    *,
    rows: List[Dict[str, Any]],
    out_root: Path,
    max_image_side: int,
    image_buffers: List[io.BytesIO],
) -> None:
    """Fill one task-style review sheet with preview image columns and row metadata."""
    headers = ["image", "evidence_image", *[_FIELD_LABELS[field] for field in _TASK_SHEET_FIELDS]]
    sheet.append(headers)

    bold = Font(bold=True)
    for column in range(1, len(headers) + 1):
        sheet.cell(row=1, column=column).font = bold

    sheet.column_dimensions["A"].width = _PREVIEW_COLUMN_WIDTH
    sheet.column_dimensions["B"].width = _PREVIEW_COLUMN_WIDTH
    _configure_sheet_columns(sheet, _TASK_SHEET_FIELDS, start_col=3)

    wrap_top = Alignment(wrap_text=True, vertical="top")
    for row_idx, row in enumerate(rows, start=2):
        preview_height = 0
        image_path = out_root / str(row["image_path"])
        if image_path.exists():
            with PILImage.open(image_path) as source:
                source_rgb = source.convert("RGB")
                preview = _build_preview_image(source_rgb, max_image_side=max_image_side)
                evidence_overlay = _render_evidence_overlay(
                    source_rgb,
                    evidence_type=str(row.get("_overlay_evidence_type", row.get("evidence_type", ""))),
                    evidence_value=row.get("_overlay_evidence_value", row.get("answer_evidence")),
                )
                evidence_preview = _build_preview_image(evidence_overlay, max_image_side=max_image_side)
                preview_height = max(int(preview.height), int(evidence_preview.height))

                base_buffer = io.BytesIO()
                preview.save(base_buffer, format="PNG")
                base_buffer.seek(0)
                image_buffers.append(base_buffer)

                evidence_buffer = io.BytesIO()
                evidence_preview.save(evidence_buffer, format="PNG")
                evidence_buffer.seek(0)
                image_buffers.append(evidence_buffer)

            xl_img = XLImage(base_buffer)
            xl_img.anchor = f"A{row_idx}"
            sheet.add_image(xl_img)

            evidence_img = XLImage(evidence_buffer)
            evidence_img.anchor = f"B{row_idx}"
            sheet.add_image(evidence_img)

        for col_idx, field in enumerate(_TASK_SHEET_FIELDS, start=3):
            cell = sheet.cell(row=row_idx, column=col_idx, value=_field_value_for_sheet(row, field))
            if field in _WRAP_FIELDS:
                cell.alignment = wrap_top
        sheet.row_dimensions[row_idx].height = max(60, float(preview_height) * 0.75)

    sheet.freeze_panes = "C2"


def _sanitize_sheet_title(raw: str) -> str:
    """Return an Excel-safe sheet title."""
    title = re.sub(r"[\\/*?:\[\]]+", "_", str(raw).strip())
    if not title:
        return "task"
    return title[:31]


def _dedupe_sheet_title(base: str, used: set[str]) -> str:
    """Return a unique sheet title under Excel's 31-character limit."""
    candidate = _sanitize_sheet_title(base)
    if candidate not in used:
        used.add(candidate)
        return candidate

    suffix_index = 2
    while True:
        suffix = f"_{suffix_index}"
        trimmed = candidate[: max(1, 31 - len(suffix))]
        attempt = f"{trimmed}{suffix}"
        if attempt not in used:
            used.add(attempt)
            return attempt
        suffix_index += 1


def _write_task_excel(
    rows: List[Dict[str, Any]],
    path: Path,
    *,
    out_root: Path,
    max_image_side: int = _TASK_PREVIEW_MAX_SIDE,
) -> None:
    """Write per-task sample review workbook with embedded preview images."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "samples"
    image_buffers: List[io.BytesIO] = []
    _populate_task_review_sheet(
        sheet,
        rows=rows,
        out_root=out_root,
        max_image_side=int(max_image_side),
        image_buffers=image_buffers,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _write_domain_combined_excel(
    rows_by_task: Dict[str, List[Dict[str, Any]]],
    path: Path,
    *,
    out_root: Path,
    max_image_side: int = _TASK_PREVIEW_MAX_SIDE,
) -> None:
    """Write one domain-level combined workbook with one task-format sheet per task."""
    workbook = Workbook()
    used_titles: set[str] = set()
    image_buffers: List[io.BytesIO] = []
    sorted_task_ids = sorted(rows_by_task.keys())
    for idx, task_id in enumerate(sorted_task_ids):
        title = _dedupe_sheet_title(task_id, used_titles)
        if idx == 0:
            sheet = workbook.active
            sheet.title = title
        else:
            sheet = workbook.create_sheet(title=title)
        _populate_task_review_sheet(
            sheet,
            rows=rows_by_task[task_id],
            out_root=out_root,
            max_image_side=int(max_image_side),
            image_buffers=image_buffers,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _as_float_number(value: Any) -> float | None:
    """Parse numeric answer values when possible."""
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


def _build_query_distribution_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build per-query answer distribution metrics and uniformity checks."""
    rows_by_query: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_query[str(row.get("query_type", "default"))].append(row)

    per_query: Dict[str, Any] = {}
    checks_run = 0
    checks_failed = 0
    checks_skipped = 0

    for query_type in sorted(rows_by_query.keys()):
        q_rows = rows_by_query[query_type]
        answer_counter = Counter(_json_cell(row.get("answer_value")) for row in q_rows)
        numeric_answers: List[float] = []
        feasible_signatures: set[Tuple[int, ...]] = set()
        feasible_missing = 0
        for row in q_rows:
            numeric = _as_float_number(row.get("answer_value"))
            if numeric is not None:
                numeric_answers.append(float(numeric))
            feasible_raw = row.get("_feasible_answer_values")
            if isinstance(feasible_raw, list) and feasible_raw:
                parsed = []
                valid = True
                for item in feasible_raw:
                    number = _as_float_number(item)
                    if number is None or not float(number).is_integer():
                        valid = False
                        break
                    parsed.append(int(number))
                if valid:
                    feasible_signatures.add(tuple(sorted(set(parsed))))
                else:
                    feasible_missing += 1
            else:
                feasible_missing += 1

        query_report: Dict[str, Any] = {
            "accepted_samples": len(q_rows),
            "answer_counts": dict(sorted(answer_counter.items())),
            "unique_answers": len(answer_counter),
        }

        if numeric_answers:
            mean = float(sum(numeric_answers) / float(len(numeric_answers)))
            variance = float(sum((value - mean) ** 2 for value in numeric_answers) / float(len(numeric_answers)))
            query_report["answer_numeric"] = {
                "count": len(numeric_answers),
                "mean": mean,
                "std": math.sqrt(max(0.0, variance)),
            }

        uniformity: Dict[str, Any] = {
            "status": "skipped",
            "reason": "",
            "thresholds": dict(_UNIFORMITY_THRESHOLDS),
        }

        if len(feasible_signatures) == 1 and feasible_missing == 0 and numeric_answers:
            support = list(feasible_signatures.pop())
            support_size = len(support)
            numeric_count = len(numeric_answers)
            support_counts: Dict[int, int] = {int(value): 0 for value in support}
            outside_support = 0
            for value in numeric_answers:
                if not float(value).is_integer():
                    outside_support += 1
                    continue
                ivalue = int(value)
                if ivalue in support_counts:
                    support_counts[ivalue] += 1
                else:
                    outside_support += 1

            uniformity.update(
                {
                    "support": [int(value) for value in support],
                    "support_size": int(support_size),
                    "outside_support_count": int(outside_support),
                }
            )

            if support_size <= 1:
                uniformity["reason"] = "support_size<=1"
            elif numeric_count < int(_UNIFORMITY_THRESHOLDS["min_samples_per_query"]):
                uniformity["reason"] = "insufficient_samples"
            elif outside_support > 0:
                uniformity["reason"] = "answers_outside_feasible_support"
            else:
                p = 1.0 / float(support_size)
                expected_count = float(numeric_count) * p
                expected_mean = float(sum(support) / float(support_size))
                expected_variance = float(sum((value - expected_mean) ** 2 for value in support) / float(support_size))
                expected_std = math.sqrt(max(0.0, expected_variance))
                observed_mean = float(sum(numeric_answers) / float(numeric_count))
                observed_variance = float(sum((value - observed_mean) ** 2 for value in numeric_answers) / float(numeric_count))
                observed_std = math.sqrt(max(0.0, observed_variance))
                mean_se = (expected_std / math.sqrt(float(numeric_count))) if expected_std > 0.0 else 0.0
                mean_z = (abs(observed_mean - expected_mean) / mean_se) if mean_se > 0.0 else 0.0
                sigma_count = math.sqrt(float(numeric_count) * p * max(0.0, 1.0 - p))
                max_bin_count_z = 0.0
                tv_distance = 0.0
                for value in support:
                    count = int(support_counts[int(value)])
                    if sigma_count > 0.0:
                        max_bin_count_z = max(max_bin_count_z, abs(float(count) - expected_count) / sigma_count)
                    tv_distance += abs((float(count) / float(numeric_count)) - p)
                tv_distance *= 0.5
                std_ratio = (observed_std / expected_std) if expected_std > 0.0 else None

                passes = (
                    mean_z <= float(_UNIFORMITY_THRESHOLDS["mean_z_max"])
                    and max_bin_count_z <= float(_UNIFORMITY_THRESHOLDS["max_bin_count_z_max"])
                    and tv_distance <= float(_UNIFORMITY_THRESHOLDS["tv_distance_max"])
                    and (
                        std_ratio is None
                        or (
                            float(_UNIFORMITY_THRESHOLDS["std_ratio_min"])
                            <= float(std_ratio)
                            <= float(_UNIFORMITY_THRESHOLDS["std_ratio_max"])
                        )
                    )
                )

                uniformity.update(
                    {
                        "status": ("pass" if passes else "fail"),
                        "reason": "",
                        "expected": {
                            "mean": expected_mean,
                            "std": expected_std,
                            "count_per_answer": expected_count,
                        },
                        "observed": {
                            "mean": observed_mean,
                            "std": observed_std,
                            "count_by_answer": {str(key): int(value) for key, value in sorted(support_counts.items())},
                        },
                        "metrics": {
                            "mean_z": float(mean_z),
                            "std_ratio": (None if std_ratio is None else float(std_ratio)),
                            "max_bin_count_z": float(max_bin_count_z),
                            "tv_distance": float(tv_distance),
                        },
                    }
                )
                checks_run += 1
                if not passes:
                    checks_failed += 1
            if uniformity["status"] == "skipped":
                checks_skipped += 1
        else:
            if len(feasible_signatures) > 1:
                uniformity["reason"] = "inconsistent_feasible_support_metadata"
            elif feasible_missing > 0:
                uniformity["reason"] = "missing_feasible_support_metadata"
            else:
                uniformity["reason"] = "non_numeric_answers"
            checks_skipped += 1

        query_report["uniformity_check"] = uniformity
        per_query[query_type] = query_report

    return {
        "thresholds": dict(_UNIFORMITY_THRESHOLDS),
        "checks_run": int(checks_run),
        "checks_failed": int(checks_failed),
        "checks_skipped": int(checks_skipped),
        "per_query_type": per_query,
    }


def _generate_samples_for_task(
    *,
    task_id: str,
    out_root: Path,
    count: int,
    count_per_query: int | None,
    base_seed: int,
    max_attempts_per_instance: int,
    image_format: str,
    params: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Generate image/data sample artifacts for one task id."""
    task = create_task(task_id)
    task_dir = out_root / task.domain / task.task_group / task.task_id
    image_dir = task_dir / "images"
    data_dir = task_dir / "data"
    image_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    query_types = resolve_query_types(task, params)
    accepted = 0
    attempted_candidates = 0
    max_candidates = 0
    rejections: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []
    accepted_by_query: Dict[str, int] = defaultdict(int)
    attempts_by_query: Dict[str, int] = defaultdict(int)

    def _attempt_sample(query_type: str, *, seed_namespace: str, seed_index: int) -> None:
        nonlocal accepted
        instance_seed = hash64(int(base_seed), seed_namespace, int(seed_index))
        task_params = dict(params)
        task_params["query_type"] = str(query_type)
        task_params["_sampling_index"] = int(seed_index)

        try:
            output = task.generate(
                int(instance_seed),
                params=task_params,
                max_attempts=int(max_attempts_per_instance),
            )
        except Exception as exc:
            reason = type(exc).__name__
            rejections[reason] = rejections.get(reason, 0) + 1
            return

        image_name = f"{accepted:06d}.{image_format}"
        image_path = image_dir / image_name
        output.image.save(image_path, format=image_format.upper())

        rel_image_path = image_path.relative_to(out_root).as_posix()
        data_path = data_dir / f"{accepted:06d}.json"
        rel_data_path = data_path.relative_to(out_root).as_posix()

        prompt_variants = dict(getattr(output, "prompt_variants", {}) or {})
        prompt_answer_only = str(prompt_variants.get("answer_only", output.prompt))
        prompt_answer_and_evidence = str(prompt_variants.get("answer_and_evidence", output.prompt))

        payload = {
            "domain": task.domain,
            "task_group": task.task_group,
            "task": task.task_id,
            "sample_index": int(accepted),
            "instance_seed": int(instance_seed),
            "query_type": str(output.query_type),
            "prompt": prompt_answer_and_evidence,
            "prompt_variants": prompt_variants,
            "answer_gt": output.answer_gt.to_dict(),
            "evidence_gt": output.evidence_gt.to_dict(),
            "complexity": output.complexity.to_dict(),
            "image": {
                "path": rel_image_path,
                "format": image_format,
            },
            "versions": dict(output.task_versions),
            "trace_payload": dict(output.trace_payload),
        }
        write_json_file(data_path, payload)

        exec_trace = output.trace_payload.get("execution_trace", {}) if isinstance(output.trace_payload, dict) else {}
        feasible_values = exec_trace.get("feasible_answer_values", []) if isinstance(exec_trace, dict) else []
        projected_evidence = output.trace_payload.get("projected_evidence", {}) if isinstance(output.trace_payload, dict) else {}
        overlay_evidence_type = str(output.evidence_gt.type)
        overlay_evidence_value = output.evidence_gt.value
        if isinstance(projected_evidence, dict):
            if overlay_evidence_type in {"grid_point_set", "grid_point_path"}:
                pixel_key = "point_path" if overlay_evidence_type == "grid_point_path" else "point_set"
                if pixel_key in projected_evidence:
                    overlay_evidence_type = pixel_key
                    overlay_evidence_value = projected_evidence.get(pixel_key)
            elif overlay_evidence_type == "grid_point_map" and "point_map" in projected_evidence:
                overlay_evidence_type = "point_map"
                overlay_evidence_value = projected_evidence.get("point_map")
            elif overlay_evidence_type == "measurement_ref_map" and "annotation_centers" in projected_evidence:
                overlay_evidence_type = "annotation_centers"
                overlay_evidence_value = projected_evidence.get("annotation_centers")
        canonical_answer = {
            "evidence": output.evidence_gt.value,
            "answer": output.answer_gt.value,
        }
        rows.append(
            {
                "domain": task.domain,
                "task_group": task.task_group,
                "task": task.task_id,
                "sample_index": int(accepted),
                "instance_seed": int(instance_seed),
                "query_type": str(output.query_type),
                "image_path": rel_image_path,
                "data_path": rel_data_path,
                "prompt": prompt_answer_and_evidence,
                "prompt_answer_only": prompt_answer_only,
                "answer": canonical_answer,
                "answer_type": output.answer_gt.type,
                "answer_value": output.answer_gt.value,
                "evidence_type": output.evidence_gt.type,
                "answer_evidence": output.evidence_gt.value,
                "_overlay_evidence_type": overlay_evidence_type,
                "_overlay_evidence_value": overlay_evidence_value,
                "_feasible_answer_values": list(feasible_values) if isinstance(feasible_values, list) else [],
            }
        )
        accepted += 1
        accepted_by_query[str(output.query_type)] += 1

    if count_per_query is not None:
        requested_by_query = {query_type: int(count_per_query) for query_type in query_types}
        for query_type in query_types:
            requested_q = int(requested_by_query[query_type])
            max_candidates_q = max(int(requested_q) * 20, int(requested_q))
            max_candidates += int(max_candidates_q)
            seed_index_q = 0
            while int(accepted_by_query[query_type]) < int(requested_q) and seed_index_q < int(max_candidates_q):
                attempts_by_query[query_type] += 1
                _attempt_sample(
                    query_type,
                    seed_namespace=f"{task_id}:{query_type}:sample_instance_seed",
                    seed_index=seed_index_q,
                )
                seed_index_q += 1
            attempted_candidates += int(seed_index_q)
        requested_samples = int(sum(requested_by_query.values()))
    else:
        requested_by_query = {}
        max_candidates = max(int(count) * 20, int(count))
        seed_index = 0
        while accepted < int(count) and seed_index < int(max_candidates):
            query_type = query_types[seed_index % len(query_types)]
            attempts_by_query[query_type] += 1
            _attempt_sample(
                query_type,
                seed_namespace=f"{task_id}:sample_instance_seed",
                seed_index=seed_index,
            )
            seed_index += 1
        attempted_candidates = int(seed_index)
        requested_samples = int(count)

    distribution_report = _build_query_distribution_report(rows)

    summary = {
        "domain": task.domain,
        "task_group": task.task_group,
        "task": task.task_id,
        "requested_samples": int(requested_samples),
        "accepted_samples": int(accepted),
        "requested_samples_by_query_type": (
            dict(sorted(requested_by_query.items())) if requested_by_query else None
        ),
        "accepted_samples_by_query_type": dict(sorted((k, int(v)) for k, v in accepted_by_query.items())),
        "attempted_candidates_by_query_type": dict(sorted((k, int(v)) for k, v in attempts_by_query.items())),
        "attempted_candidates": int(attempted_candidates),
        "max_candidates": int(max_candidates),
        "query_types": list(query_types),
        "rejections_by_error": dict(sorted(rejections.items())),
        "answer_distribution": dict(distribution_report),
    }
    write_json_file(task_dir / "summary.json", summary)
    write_json_file(task_dir / "distribution_report.json", distribution_report)
    return summary, rows


def main() -> int:
    """Parse CLI args and generate task sample artifacts."""
    parser = argparse.ArgumentParser(
        description="Generate TRACE task sample images/data, per-task Excel files, and per-domain combined workbooks"
    )
    parser.add_argument("--out", default="samples", help="Output root directory")
    parser.add_argument("--tasks", default="", help="Comma-separated task ids (default: all registered tasks)")
    parser.add_argument("--count", type=int, default=50, help="Samples per task (default: 50)")
    parser.add_argument(
        "--count-per-query",
        type=int,
        default=0,
        help="Samples per query type per task (overrides --count when > 0)",
    )
    parser.add_argument("--seed", type=int, default=0, help="Base sampling seed")
    parser.add_argument("--max-attempts-per-instance", type=int, default=100, help="Max generation attempts per instance")
    parser.add_argument("--image-format", default="png", choices=["png", "jpeg", "jpg"], help="Saved image format")
    parser.add_argument("--params", default="", help="Global task params JSON object")
    parser.add_argument("--task-params", default="", help="Per-task params JSON object mapping task_id -> params object")
    parser.add_argument(
        "--combined-excel",
        default="combined_samples.xlsx",
        help="Combined Excel filename written under each domain directory",
    )
    parser.add_argument("--clean", action="store_true", help="Clean only selected task directories before generation")
    parser.add_argument("--clean-all", action="store_true", help="Dangerous: remove entire --out before generation")
    args = parser.parse_args()

    if int(args.count) <= 0:
        raise ValueError("--count must be positive")
    if int(args.count_per_query) < 0:
        raise ValueError("--count-per-query must be >= 0")
    if args.clean and args.clean_all:
        raise ValueError("use only one of --clean or --clean-all")
    if args.clean and not args.tasks.strip():
        raise ValueError("--clean requires --tasks so we only remove explicit task directories")

    task_ids = _resolve_task_ids(args.tasks)
    global_params = _parse_json_dict(args.params, arg_name="--params")
    per_task_params = _parse_json_dict(args.task_params, arg_name="--task-params")
    for task_id, params in per_task_params.items():
        if task_id not in TASK_REGISTRY:
            raise ValueError(f"--task-params includes unknown task_id: {task_id}")
        if not isinstance(params, dict):
            raise ValueError(f"--task-params[{task_id}] must be a JSON object")

    out_root = Path(args.out)
    if args.clean_all and out_root.exists():
        shutil.rmtree(out_root)
    elif args.clean and out_root.exists():
        for task_id in task_ids:
            task = create_task(task_id)
            task_dir = out_root / task.domain / task.task_group / task.task_id
            if task_dir.exists():
                shutil.rmtree(task_dir)

    all_rows: List[Dict[str, Any]] = []
    rows_by_domain_task: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(dict)
    all_summaries: List[Dict[str, Any]] = []
    shortfall_tasks: List[str] = []

    for task_id in task_ids:
        params = dict(global_params)
        params.update(dict(per_task_params.get(task_id, {})))
        summary, rows = _generate_samples_for_task(
            task_id=task_id,
            out_root=out_root,
            count=int(args.count),
            count_per_query=(int(args.count_per_query) if int(args.count_per_query) > 0 else None),
            base_seed=int(args.seed),
            max_attempts_per_instance=int(args.max_attempts_per_instance),
            image_format=("jpeg" if args.image_format == "jpg" else args.image_format),
            params=params,
        )
        all_summaries.append(summary)
        all_rows.extend(rows)
        rows_by_domain_task[str(summary["domain"])][str(summary["task"])] = list(rows)

        task_dir = out_root / str(summary["domain"]) / str(summary["task_group"]) / str(summary["task"])
        task_excel_path = task_dir / "samples.xlsx"
        _write_task_excel(rows, task_excel_path, out_root=out_root)

        if int(summary["accepted_samples"]) < int(summary["requested_samples"]):
            shortfall_tasks.append(str(summary["task"]))
        print(
            f"[task] {summary['task']}: accepted={summary['accepted_samples']}/{summary['requested_samples']} "
            f"attempts={summary['attempted_candidates']}"
        )

    domain_combined_excels: Dict[str, str] = {}
    for domain in sorted(rows_by_domain_task.keys()):
        combined_excel_path = out_root / str(domain) / str(args.combined_excel)
        _write_domain_combined_excel(
            rows_by_domain_task[str(domain)],
            combined_excel_path,
            out_root=out_root,
        )
        domain_combined_excels[str(domain)] = combined_excel_path.relative_to(out_root).as_posix()
        print(f"[done] combined excel ({domain}): {combined_excel_path}")

    summary_payload = {
        "num_tasks": len(task_ids),
        "samples_per_task": (None if int(args.count_per_query) > 0 else int(args.count)),
        "samples_per_query_type": (int(args.count_per_query) if int(args.count_per_query) > 0 else None),
        "total_rows": len(all_rows),
        "domain_combined_excels": dict(sorted(domain_combined_excels.items())),
        "tasks": all_summaries,
    }
    write_json_file(out_root / "summary_all_tasks.json", summary_payload)

    if shortfall_tasks:
        print(
            f"[error] sample shortfall for tasks: {', '.join(sorted(shortfall_tasks))}. "
            "Check task summaries under samples/<domain>/<task_group>/<task>/summary.json",
            file=sys.stderr,
        )
        return 1

    print(f"[done] wrote {len(all_rows)} samples to {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
