#!/usr/bin/env python3
"""Export one task-review workbook from an existing RLVR parquet + TRACE dataset root.

This is intended for calibration review sets under review/task-reviews/, where we
want the same workbook-style artifact as task-reviews/ but for one exact probe
set that already exists on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import pandas as pd
import zstandard as zstd

from trace.core.review_overlays import resolve_overlay_annotation
from trace.core.taxonomy import resolve_task_query_id, resolve_task_taxonomy
from trace.core.task_review_workbooks import write_inspection_excel as _write_inspection_excel


def _parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export one workbook for an exact task probe set")
    parser.add_argument("--parquet", required=True, help="RLVR parquet for the exact probe set")
    parser.add_argument("--dataset-root", required=True, help="TRACE dataset root that produced the parquet")
    parser.add_argument("--out-root", default="review/task-reviews", help="Output root for workbook artifacts")
    parser.add_argument("--task-id", default="", help="Optional task id override")
    parser.add_argument(
        "--review-label",
        default="",
        help="Optional label suffix for the workbook, e.g. level0_200",
    )
    parser.add_argument(
        "--calibration-baseline",
        default="v0",
        help="Calibration artifact baseline label to write into the review manifest.",
    )
    return parser.parse_args()


def _review_query_id_key(*, query_id: str) -> str:
    """Return the review grouping key for one exported task instance."""

    query_id_text = str(query_id).strip()
    if query_id_text in {"", "default"} and query_id_text:
        return query_id_text
    return query_id_text


def _ensure_link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    try:
        relative_target = os.path.relpath(str(source), start=str(destination.parent))
        destination.symlink_to(relative_target)
    except Exception:
        shutil.copy2(source, destination)


def _load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _load_selected_refs(parquet_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    df = pd.read_parquet(parquet_path, columns=["task", "trace_ref"])
    if len(df) == 0:
        raise ValueError(f"parquet has no rows: {parquet_path}")
    task_ids = sorted({str(item) for item in df["task"].tolist()})
    if len(task_ids) != 1:
        raise ValueError(f"expected exactly one task in parquet, found: {task_ids}")
    selected_refs: List[Dict[str, Any]] = []
    for value in df["trace_ref"].tolist():
        parsed = value if isinstance(value, Mapping) else json.loads(str(value))
        selected_refs.append(
            {
                "shard_id": str(parsed["shard_id"]),
                "line_index": int(parsed["line_index"]),
                "trace_record_hash": str(parsed.get("trace_record_hash", "")),
            }
        )
    return str(task_ids[0]), selected_refs


def _load_train_instance_index(dataset_root: Path) -> Dict[Tuple[str, int], Dict[str, Any]]:
    index: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for row in _load_jsonl(dataset_root / "train_instances.jsonl"):
        trace_ref = row.get("trace_ref", {})
        if not isinstance(trace_ref, Mapping):
            continue
        key = (str(trace_ref.get("shard_id", "")), int(trace_ref.get("line_index", -1)))
        index[key] = row
    return index


def _load_trace_index(dataset_root: Path, selected_refs: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, int], Dict[str, Any]]:
    needed_by_shard: Dict[str, set[int]] = defaultdict(set)
    for ref in selected_refs:
        needed_by_shard[str(ref["shard_id"])].add(int(ref["line_index"]))

    out: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for shard_id, line_indices in needed_by_shard.items():
        shard_path = dataset_root / "traces" / str(shard_id)
        with shard_path.open("rb") as handle:
            reader = zstd.ZstdDecompressor().stream_reader(handle)
            for line_index, raw in enumerate(reader.read().decode("utf-8").splitlines()):
                if line_index not in line_indices:
                    continue
                out[(str(shard_id), int(line_index))] = json.loads(raw)
    return out


def main() -> int:
    args = _parse_cli()
    parquet_path = Path(str(args.parquet)).resolve()
    dataset_root = Path(str(args.dataset_root)).resolve()
    out_root = Path(str(args.out_root)).resolve()

    inferred_task_id, selected_refs = _load_selected_refs(parquet_path)
    task_id = str(args.task_id).strip() or inferred_task_id
    if task_id != inferred_task_id:
        raise ValueError(f"--task-id {task_id} does not match parquet task {inferred_task_id}")

    taxonomy = resolve_task_taxonomy(str(task_id))
    task_dir = out_root / str(taxonomy.domain) / str(taxonomy.scene_id) / task_id
    images_dir = task_dir / "images"
    data_dir = task_dir / "data"
    shutil.rmtree(images_dir, ignore_errors=True)
    shutil.rmtree(data_dir, ignore_errors=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    review_label = str(args.review_label).strip()
    workbook_name = f"{task_id}_{review_label}.xlsx" if review_label else f"{task_id}.xlsx"
    workbook_path = task_dir / workbook_name

    train_index = _load_train_instance_index(dataset_root)
    trace_index = _load_trace_index(dataset_root, selected_refs)

    rows_by_query_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    per_query_id_counts: Dict[str, int] = defaultdict(int)

    for ref in selected_refs:
        key = (str(ref["shard_id"]), int(ref["line_index"]))
        instance = train_index.get(key)
        trace_record = trace_index.get(key)
        if instance is None:
            raise KeyError(f"missing train instance for {key}")
        if trace_record is None:
            raise KeyError(f"missing trace record for {key}")

        query_spec = trace_record.get("query_spec", {}) if isinstance(trace_record, Mapping) else {}
        execution_trace = trace_record.get("execution_trace", {}) if isinstance(trace_record, Mapping) else {}
        query_id = str(query_spec.get("query_id") or execution_trace.get("query_id") or "").strip()
        scene_id = str(instance.get("scene_id") or query_spec.get("scene_id") or taxonomy.scene_id)
        query_id = str(
            instance.get("query_id")
            or query_spec.get("query_id")
            or execution_trace.get("query_id")
            or resolve_task_query_id(query_id=query_id, trace_payload=trace_record)
        )
        review_query_id = _review_query_id_key(query_id=query_id)
        query_id_dir = review_query_id or "default"
        query_id_index = int(per_query_id_counts[query_id_dir])
        per_query_id_counts[query_id_dir] += 1

        image_info = list(instance.get("images", []) or [])
        if not image_info:
            raise ValueError(f"instance missing images for {key}")
        image_source = dataset_root / str(image_info[0].get("path", ""))
        image_destination = images_dir / query_id_dir / f"{query_id_index:04d}.png"
        _ensure_link_or_copy(image_source, image_destination)
        rel_image_path = image_destination.relative_to(out_root).as_posix()

        prompt_variants = dict(instance.get("prompt_variants", {}) or {})
        prompt_answer_only = str(prompt_variants.get("answer_only", instance.get("prompt", "")))
        prompt_answer_and_annotation = str(prompt_variants.get("answer_and_annotation", instance.get("prompt", "")))

        answer_gt = dict(instance.get("answer_gt", {}) or {})
        annotation_gt = dict(instance.get("annotation_gt", {}) or {})
        answer_only_ground_truth = {
            "answer": answer_gt.get("value"),
        }
        canonical_answer = {
            "annotation": annotation_gt.get("value"),
            "answer": answer_gt.get("value"),
        }

        overlay_annotation_type, overlay_annotation_value = resolve_overlay_annotation(
            annotation_type=str(annotation_gt.get("type", "")),
            annotation_value=annotation_gt.get("value"),
            trace_payload={"projected_annotation": trace_record.get("projected_annotation", {})},
        )

        data_payload = {
            "task": task_id,
            "domain": str(taxonomy.domain),
            "scene_id": scene_id,
            "query_id": query_id,
            "instance_seed": int(instance.get("instance_seed", 0)),
            "instance_id": instance.get("instance_id"),
            "prompt": prompt_answer_and_annotation,
            "prompt_answer": prompt_answer_only,
            "prompt_answer_only": prompt_answer_only,
            "prompt_answer_and_annotation": prompt_answer_and_annotation,
            "prompt_variants": prompt_variants,
            "answer_gt": answer_gt,
            "annotation_gt": annotation_gt,
            "reward_contract": instance.get("reward_contract", {}),
            "image": {
                "path": rel_image_path,
                "source_path": str(image_source),
            },
            "trace_ref": instance.get("trace_ref", {}),
            "query_spec": query_spec,
            "execution_trace": execution_trace,
            "projected_annotation": trace_record.get("projected_annotation", {}),
            "versions": instance.get("versions", {}),
        }
        data_path = data_dir / query_id_dir / f"{query_id_index:04d}.json"
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(json.dumps(data_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        rel_data_path = data_path.relative_to(out_root).as_posix()

        rows_by_query_id[review_query_id].append(
            {
                "task": task_id,
                "scene_id": scene_id,
                "query_id": query_id,
                "prompt": prompt_answer_and_annotation,
                "prompt_answer": prompt_answer_only,
                "prompt_answer_only": prompt_answer_only,
                "prompt_answer_and_annotation": prompt_answer_and_annotation,
                "ground_truth_answer": answer_only_ground_truth,
                "ground_truth_answer_and_annotation": canonical_answer,
                "answer": canonical_answer,
                "answer_annotation": annotation_gt.get("value"),
                "answer_type": str(answer_gt.get("type", "")),
                "annotation_type": str(annotation_gt.get("type", "")),
                "instance_seed": int(instance.get("instance_seed", 0)),
                "image_path": rel_image_path,
                "data_path": rel_data_path,
                "overlay_annotation_type": str(overlay_annotation_type),
                "overlay_annotation_value": overlay_annotation_value,
            }
        )

    workbook_sheets = _write_inspection_excel(rows_by_query_id, workbook_path, out_root=out_root)

    manifest = {
        "task_id": task_id,
        "domain": str(taxonomy.domain),
        "scene_id": str(taxonomy.scene_id),
        "calibration_baseline": str(args.calibration_baseline),
        "review_label": review_label,
        "inspection_count": int(sum(len(rows) for rows in rows_by_query_id.values())),
        "query_ids": {
            str(variant): int(len(rows_by_query_id[variant]))
            for variant in sorted(rows_by_query_id.keys())
        },
        "source_parquet": str(parquet_path),
        "source_dataset_root": str(dataset_root),
        "workbook": str(workbook_path.relative_to(out_root).as_posix()),
        "workbook_sheets": dict(workbook_sheets),
    }
    (task_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
