#!/usr/bin/env python3
"""Generate task sample images/data and a combined Excel review file."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY, create_task


def _to_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parse_json_dict(raw: str, *, arg_name: str) -> Dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{arg_name} must be a JSON object")
    return dict(value)


def _resolve_task_ids(raw_tasks: str) -> List[str]:
    if not raw_tasks.strip():
        return sorted(TASK_REGISTRY.keys())
    task_ids = [item.strip() for item in raw_tasks.split(",") if item.strip()]
    if not task_ids:
        raise ValueError("--tasks resolved to an empty list")
    unknown = [task_id for task_id in task_ids if task_id not in TASK_REGISTRY]
    if unknown:
        raise ValueError(f"unknown task ids: {', '.join(sorted(unknown))}")
    return sorted(dict.fromkeys(task_ids))


def _resolve_query_types(task: Any, params: Dict[str, Any]) -> List[str]:
    if "query_type" in params:
        return [str(params["query_type"])]

    supported_fn = getattr(task, "supported_query_types", None)
    if not callable(supported_fn):
        return ["default"]

    values = [str(item) for item in supported_fn(dict(params))]
    deduped: List[str] = []
    seen: set[str] = set()
    for query_type in values:
        if query_type not in seen:
            deduped.append(query_type)
            seen.add(query_type)
    return deduped or ["default"]


def _json_cell(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    return "" if value is None else str(value)


def _generate_samples_for_task(
    *,
    task_id: str,
    out_root: Path,
    count: int,
    base_seed: int,
    max_attempts_per_instance: int,
    image_format: str,
    params: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    task = create_task(task_id)
    task_dir = out_root / task.domain / task.task_group / task.task_id
    image_dir = task_dir / "images"
    data_dir = task_dir / "data"
    image_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    query_types = _resolve_query_types(task, params)
    accepted = 0
    seed_index = 0
    rejections: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []
    max_candidates = max(int(count) * 20, int(count))

    while accepted < int(count) and seed_index < max_candidates:
        instance_seed = hash64(int(base_seed), f"{task_id}:sample_instance_seed", seed_index)
        query_type = query_types[seed_index % len(query_types)]
        seed_index += 1

        task_params = dict(params)
        task_params["query_type"] = query_type

        try:
            output = task.generate(
                int(instance_seed),
                params=task_params,
                max_attempts=int(max_attempts_per_instance),
            )
        except Exception as exc:
            reason = type(exc).__name__
            rejections[reason] = rejections.get(reason, 0) + 1
            continue

        image_name = f"{accepted:06d}.{image_format}"
        image_path = image_dir / image_name
        output.image.save(image_path, format=image_format.upper())

        rel_image_path = image_path.relative_to(out_root).as_posix()
        data_path = data_dir / f"{accepted:06d}.json"
        rel_data_path = data_path.relative_to(out_root).as_posix()

        payload = {
            "domain": task.domain,
            "task_group": task.task_group,
            "task": task.task_id,
            "sample_index": int(accepted),
            "instance_seed": int(instance_seed),
            "query_type": str(output.query_type),
            "prompt": output.prompt,
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
        _to_json_file(data_path, payload)

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
                "prompt": output.prompt,
                "answer_type": output.answer_gt.type,
                "answer_value": output.answer_gt.value,
                "evidence_type": output.evidence_gt.type,
                "evidence_value": output.evidence_gt.value,
            }
        )
        accepted += 1

    summary = {
        "domain": task.domain,
        "task_group": task.task_group,
        "task": task.task_id,
        "requested_samples": int(count),
        "accepted_samples": int(accepted),
        "attempted_candidates": int(seed_index),
        "max_candidates": int(max_candidates),
        "query_types": list(query_types),
        "rejections_by_error": dict(sorted(rejections.items())),
    }
    _to_json_file(task_dir / "summary.json", summary)
    return summary, rows


def _write_combined_excel(rows: List[Dict[str, Any]], path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "samples"

    headers = [
        "domain",
        "task_group",
        "task",
        "sample_index",
        "instance_seed",
        "query_type",
        "image_path",
        "data_path",
        "prompt",
        "answer_type",
        "answer_value",
        "evidence_type",
        "evidence_value",
    ]
    sheet.append(headers)

    bold = Font(bold=True)
    for column in range(1, len(headers) + 1):
        sheet.cell(row=1, column=column).font = bold

    column_widths = {
        "A": 12,
        "B": 16,
        "C": 32,
        "D": 12,
        "E": 20,
        "F": 20,
        "G": 60,
        "H": 60,
        "I": 90,
        "J": 14,
        "K": 20,
        "L": 14,
        "M": 24,
    }
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width

    wrap_top = Alignment(wrap_text=True, vertical="top")
    for row_idx, row in enumerate(rows, start=2):
        sheet.cell(row=row_idx, column=1, value=row["domain"])
        sheet.cell(row=row_idx, column=2, value=row["task_group"])
        sheet.cell(row=row_idx, column=3, value=row["task"])
        sheet.cell(row=row_idx, column=4, value=int(row["sample_index"]))
        sheet.cell(row=row_idx, column=5, value=int(row["instance_seed"]))
        sheet.cell(row=row_idx, column=6, value=row["query_type"])
        sheet.cell(row=row_idx, column=7, value=row["image_path"]).alignment = wrap_top
        sheet.cell(row=row_idx, column=8, value=row["data_path"]).alignment = wrap_top
        sheet.cell(row=row_idx, column=9, value=row["prompt"]).alignment = wrap_top
        sheet.cell(row=row_idx, column=10, value=row["answer_type"])
        sheet.cell(row=row_idx, column=11, value=_json_cell(row["answer_value"])).alignment = wrap_top
        sheet.cell(row=row_idx, column=12, value=row["evidence_type"])
        sheet.cell(row=row_idx, column=13, value=_json_cell(row["evidence_value"])).alignment = wrap_top
        sheet.row_dimensions[row_idx].height = 60

    sheet.freeze_panes = "A2"
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate TRACE task sample images/data and a combined Excel sheet")
    parser.add_argument("--out", default="samples", help="Output root directory")
    parser.add_argument("--tasks", default="", help="Comma-separated task ids (default: all registered tasks)")
    parser.add_argument("--count", type=int, default=50, help="Samples per task (default: 50)")
    parser.add_argument("--seed", type=int, default=0, help="Base sampling seed")
    parser.add_argument("--max-attempts-per-instance", type=int, default=100, help="Max generation attempts per instance")
    parser.add_argument("--image-format", default="png", choices=["png", "jpeg", "jpg"], help="Saved image format")
    parser.add_argument("--params", default="", help="Global task params JSON object")
    parser.add_argument("--task-params", default="", help="Per-task params JSON object mapping task_id -> params object")
    parser.add_argument("--combined-excel", default="combined_samples.xlsx", help="Combined Excel filename under --out")
    parser.add_argument("--clean", action="store_true", help="Clean only selected task directories before generation")
    parser.add_argument("--clean-all", action="store_true", help="Dangerous: remove entire --out before generation")
    args = parser.parse_args()

    if int(args.count) <= 0:
        raise ValueError("--count must be positive")
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
    all_summaries: List[Dict[str, Any]] = []
    shortfall_tasks: List[str] = []

    for task_id in task_ids:
        params = dict(global_params)
        params.update(dict(per_task_params.get(task_id, {})))
        summary, rows = _generate_samples_for_task(
            task_id=task_id,
            out_root=out_root,
            count=int(args.count),
            base_seed=int(args.seed),
            max_attempts_per_instance=int(args.max_attempts_per_instance),
            image_format=("jpeg" if args.image_format == "jpg" else args.image_format),
            params=params,
        )
        all_summaries.append(summary)
        all_rows.extend(rows)
        if int(summary["accepted_samples"]) < int(summary["requested_samples"]):
            shortfall_tasks.append(str(summary["task"]))
        print(
            f"[task] {summary['task']}: accepted={summary['accepted_samples']}/{summary['requested_samples']} "
            f"attempts={summary['attempted_candidates']}"
        )

    combined_excel_path = out_root / args.combined_excel
    _write_combined_excel(all_rows, combined_excel_path)

    summary_payload = {
        "num_tasks": len(task_ids),
        "samples_per_task": int(args.count),
        "total_rows": len(all_rows),
        "combined_excel": combined_excel_path.relative_to(out_root).as_posix(),
        "tasks": all_summaries,
    }
    _to_json_file(out_root / "summary_all_tasks.json", summary_payload)

    if shortfall_tasks:
        print(
            f"[error] sample shortfall for tasks: {', '.join(sorted(shortfall_tasks))}. "
            "Check task summaries under samples/<domain>/<task_group>/<task>/summary.json",
            file=sys.stderr,
        )
        return 1

    print(f"[done] wrote {len(all_rows)} samples to {out_root}")
    print(f"[done] combined excel: {combined_excel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
