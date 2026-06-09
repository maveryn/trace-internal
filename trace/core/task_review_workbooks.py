"""Workbook helpers for task-review inspection artifacts."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage
from PIL import ImageOps as PILImageOps

from .review_overlays import render_annotation_overlay


PREVIEW_MAX_SIDE = 384

INSPECTION_EXCEL_HEADERS: tuple[str, ...] = (
    "image",
    "annotation_image",
    "task",
    "query_id",
    "scene_id",
    "query_id",
    "prompt_answer",
    "ground_truth_answer",
    "prompt_answer_and_annotation",
    "ground_truth_answer_and_annotation",
    "answer_type",
    "annotation_type",
    "instance_seed",
    "image_path",
    "data_path",
)

INSPECTION_EXCEL_COLUMN_WIDTHS: Dict[str, float] = {
    "A": 54,
    "B": 54,
    "C": 28,
    "D": 24,
    "E": 24,
    "F": 24,
    "G": 34,
    "H": 22,
    "I": 40,
    "J": 24,
    "K": 14,
    "L": 16,
    "M": 24,
    "N": 28,
    "O": 28,
}

INSPECTION_EXCEL_WRAP_COLUMNS = {"C", "D", "E", "F", "G", "H", "I", "J", "M", "N", "O"}

MODEL_STATS_HEADERS: tuple[str, ...] = (
    "task",
    "combined_status",
    "model",
    "reasons",
    "hard_frac",
    "easy_frac",
    "band_frac",
    "mean_solve_rate",
    "response_cap_rate",
    "prompt_max",
    "prompt_over_limit_count",
    "rollout_count",
    "prompt_count",
    "max_response_length",
    "solve_workbook",
    "calibration_stats",
    "output_dir",
)

MODEL_STATS_WIDTHS: Dict[str, float] = {
    "A": 56,
    "B": 20,
    "C": 16,
    "D": 34,
    "E": 12,
    "F": 12,
    "G": 12,
    "H": 16,
    "I": 18,
    "J": 12,
    "K": 22,
    "L": 14,
    "M": 14,
    "N": 20,
    "O": 72,
    "P": 72,
    "Q": 72,
}


def json_cell(value: Any) -> str:
    """Serialize nested values for workbook cells."""

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    return "" if value is None else str(value)


def build_preview_image(source: PILImage.Image, *, max_image_side: int = PREVIEW_MAX_SIDE) -> PILImage.Image:
    """Resize and border one preview image for workbook embedding."""

    preview = source.convert("RGB")
    border_px = 1
    inner_max_side = max(1, int(max_image_side) - (2 * border_px))
    preview.thumbnail((inner_max_side, inner_max_side), PILImage.Resampling.LANCZOS)
    return PILImageOps.expand(preview, border=border_px, fill=(0, 0, 0))


def sanitize_sheet_title(raw: str) -> str:
    """Return one Excel-safe sheet title."""

    title = re.sub(r"[\\/*?:\[\]]+", "_", str(raw).strip())
    if not title:
        return "default"
    return title[:31]


def dedupe_sheet_title(base: str, used: set[str]) -> str:
    """Return one unique Excel-safe sheet title."""

    candidate = sanitize_sheet_title(base)
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


def populate_inspection_sheet(
    sheet: Any,
    *,
    rows: Sequence[Mapping[str, Any]],
    out_root: Path,
    image_buffers: list[io.BytesIO],
    max_image_side: int = PREVIEW_MAX_SIDE,
) -> None:
    """Populate one inspection sheet with preview images and metadata rows."""

    sheet.append(list(INSPECTION_EXCEL_HEADERS))

    bold = Font(bold=True)
    for column in range(1, len(INSPECTION_EXCEL_HEADERS) + 1):
        sheet.cell(row=1, column=column).font = bold

    for letter, width in INSPECTION_EXCEL_COLUMN_WIDTHS.items():
        sheet.column_dimensions[str(letter)].width = float(width)

    wrap_top = Alignment(wrap_text=True, vertical="top")

    for row_idx, row in enumerate(rows, start=2):
        image_path = Path(out_root) / str(row.get("image_path", ""))
        if image_path.exists():
            with PILImage.open(image_path) as source:
                source_rgb = source.convert("RGB")
                preview = build_preview_image(source_rgb, max_image_side=max_image_side)
                annotation_preview = build_preview_image(
                    render_annotation_overlay(
                        source_rgb,
                        annotation_type=str(row.get("overlay_annotation_type", row.get("annotation_type", ""))),
                        annotation_value=row.get("overlay_annotation_value", row.get("answer_annotation")),
                    ),
                    max_image_side=max_image_side,
                )
                row_height = max(int(preview.height), int(annotation_preview.height))

                preview_buffer = io.BytesIO()
                preview.save(preview_buffer, format="PNG")
                preview_buffer.seek(0)
                image_buffers.append(preview_buffer)

                annotation_buffer = io.BytesIO()
                annotation_preview.save(annotation_buffer, format="PNG")
                annotation_buffer.seek(0)
                image_buffers.append(annotation_buffer)

            preview_img = XLImage(preview_buffer)
            preview_img.anchor = f"A{row_idx}"
            sheet.add_image(preview_img)

            annotation_img = XLImage(annotation_buffer)
            annotation_img.anchor = f"B{row_idx}"
            sheet.add_image(annotation_img)

            sheet.row_dimensions[row_idx].height = max(60, float(row_height) * 0.75)
        else:
            sheet.row_dimensions[row_idx].height = 60

        values = [
            row.get("task", ""),
            row.get("query_id", ""),
            row.get("scene_id", ""),
            row.get("query_id", ""),
            row.get("prompt_answer", row.get("prompt_answer_only", "")),
            json_cell(row.get("ground_truth_answer", row.get("answer_only"))),
            row.get("prompt_answer_and_annotation", row.get("prompt", "")),
            json_cell(row.get("ground_truth_answer_and_annotation", row.get("answer"))),
            row.get("answer_type", ""),
            row.get("annotation_type", ""),
            int(row.get("instance_seed", 0)),
            row.get("image_path", ""),
            row.get("data_path", ""),
        ]
        for offset, value in enumerate(values, start=3):
            cell = sheet.cell(row=row_idx, column=offset, value=value)
            if get_column_letter(offset) in INSPECTION_EXCEL_WRAP_COLUMNS:
                cell.alignment = wrap_top

    sheet.freeze_panes = "C2"


def write_inspection_excel(
    rows_by_query_id: Mapping[str, Sequence[Mapping[str, Any]]],
    path: Path,
    *,
    out_root: Path,
    max_image_side: int = PREVIEW_MAX_SIDE,
) -> Dict[str, str]:
    """Write one inspection workbook with one sheet per query id."""

    workbook = Workbook()
    image_buffers: list[io.BytesIO] = []
    used_titles: set[str] = set()
    query_id_to_sheet: Dict[str, str] = {}

    sorted_query_ids = sorted(str(variant) for variant in rows_by_query_id.keys())
    if not sorted_query_ids:
        sorted_query_ids = [""]

    for index, query_id in enumerate(sorted_query_ids):
        base_title = str(query_id).strip() or "default"
        sheet_title = dedupe_sheet_title(base_title, used_titles)
        if int(index) == 0:
            sheet = workbook.active
            sheet.title = sheet_title
        else:
            sheet = workbook.create_sheet(title=sheet_title)
        query_id_to_sheet[str(query_id)] = str(sheet_title)
        populate_inspection_sheet(
            sheet,
            rows=list(rows_by_query_id.get(str(query_id), [])),
            out_root=out_root,
            image_buffers=image_buffers,
            max_image_side=int(max_image_side),
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return query_id_to_sheet


def task_sheet_title(task_id: str, *, domain: str) -> str:
    """Return a compact human-readable sheet title for one task id."""

    task_text = str(task_id).strip()
    prefix = f"task_{str(domain).strip()}_"
    if task_text.startswith(prefix):
        return task_text[len(prefix) :]
    if task_text.startswith("task_"):
        return task_text[len("task_") :]
    return task_text


def populate_model_stats_sheet(sheet: Any, rows: Sequence[Mapping[str, Any]]) -> None:
    """Populate the scene-level model stats sheet."""

    sheet.append(list(MODEL_STATS_HEADERS))
    bold = Font(bold=True)
    for column in range(1, len(MODEL_STATS_HEADERS) + 1):
        sheet.cell(row=1, column=column).font = bold
    for letter, width in MODEL_STATS_WIDTHS.items():
        sheet.column_dimensions[str(letter)].width = float(width)

    wrap_top = Alignment(wrap_text=True, vertical="top")
    wrap_columns = {"A", "E", "G", "R", "S", "T"}
    for row_idx, row in enumerate(rows, start=2):
        for column_idx, header in enumerate(MODEL_STATS_HEADERS, start=1):
            value = row.get(header, "")
            cell = sheet.cell(row=row_idx, column=column_idx, value=value)
            if get_column_letter(column_idx) in wrap_columns:
                cell.alignment = wrap_top
    sheet.freeze_panes = "A2"


def write_scene_inspection_excel(
    rows_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    path: Path,
    *,
    out_root: Path,
    domain: str,
    model_stats_rows: Sequence[Mapping[str, Any]] | None = None,
    max_image_side: int = PREVIEW_MAX_SIDE,
) -> tuple[Dict[str, str], str, int]:
    """Write one scene-level workbook with model stats plus one sheet per task."""

    workbook = Workbook()
    image_buffers: list[io.BytesIO] = []
    used_titles: set[str] = set()
    task_to_sheet: Dict[str, str] = {}

    sorted_tasks = sorted(str(task_id) for task_id in rows_by_task.keys())
    if not sorted_tasks:
        sorted_tasks = ["empty"]

    model_stats_rows = list(model_stats_rows or [])
    model_stats_sheet = dedupe_sheet_title("model_stats", used_titles)
    sheet = workbook.active
    sheet.title = model_stats_sheet
    populate_model_stats_sheet(sheet, rows=model_stats_rows)

    for task_id in sorted_tasks:
        sheet_title = dedupe_sheet_title(task_sheet_title(str(task_id), domain=str(domain)), used_titles)
        sheet = workbook.create_sheet(title=sheet_title)
        task_to_sheet[str(task_id)] = str(sheet_title)
        populate_inspection_sheet(
            sheet,
            rows=list(rows_by_task.get(str(task_id), [])),
            out_root=out_root,
            image_buffers=image_buffers,
            max_image_side=int(max_image_side),
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return task_to_sheet, model_stats_sheet, int(len(model_stats_rows))


__all__ = [
    "PREVIEW_MAX_SIDE",
    "build_preview_image",
    "dedupe_sheet_title",
    "json_cell",
    "populate_inspection_sheet",
    "populate_model_stats_sheet",
    "sanitize_sheet_title",
    "task_sheet_title",
    "write_inspection_excel",
    "write_scene_inspection_excel",
]
