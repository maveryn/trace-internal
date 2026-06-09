#!/usr/bin/env python3
"""Run task review workflows with distribution reports and browser inspection sidecars."""

from __future__ import annotations

import argparse
import os
import json
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Mapping, Sequence

from trace.core.annotation_sanitization import sanitize_trace_payload_for_public_annotation
from trace.core.json_io import write_json_file
from trace.core.review_overlays import resolve_overlay_annotation
from trace.core.seed import hash64
from trace.core.taxonomy import inject_taxonomy_metadata, resolve_task_query_id, resolve_task_taxonomy
from trace.core.task_review_distribution import (
    answer_collector as _answer_collector,
    build_distribution_review_report as _build_distribution_review_report,
    build_random_review_report as _build_random_review_report,
    random_collector as _random_collector,
)
from trace.core.task_review_calibration import (
    CURRENT_CALIBRATION_BASELINE as _CURRENT_CALIBRATION_BASELINE,
    load_scene_model_stats_rows as _load_scene_model_stats_rows,
)
from trace.core.task_review_paths import resolve_task_review_dir as _resolve_task_review_dir
from trace.core.task_review_sampling import collect_query_id_samples, generate_random_samples, resolve_review_query_id
from trace.core.task_review_workbooks import (
    write_inspection_excel as _write_inspection_excel,
    write_scene_inspection_excel as _write_scene_inspection_excel,
)
from trace.tasks import TASK_REGISTRY, create_task


_SCENE_PREVIEW_ROWS_PER_TASK = 100


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
        help="full=random+distribution+inspection, distribution=random+distribution, inspection=browser sidecars plus optional workbook export",
    )
    parser.add_argument("--seed", type=int, default=0, help="Base seed")
    parser.add_argument("--out-root", default="review/task-reviews", help="Output root for task review artifacts")
    parser.add_argument("--random-count", type=int, default=100, help="Random sample count per task")
    parser.add_argument("--count-per-query-id", type=int, default=100, help="Target samples per query id")
    parser.add_argument(
        "--inspection-count-per-query-id",
        type=int,
        default=25,
        help="Source balanced inspection samples per query; used only with --balanced-inspection-by-query",
    )
    parser.add_argument(
        "--balanced-inspection-by-query",
        action="store_true",
        help="Generate balanced inspection sidecars with a fixed sample count per query id instead of --random-count total samples per task",
    )
    parser.add_argument("--max-attempts-per-instance", type=int, default=200, help="Max attempts per instance generation")
    parser.add_argument(
        "--max-total-samples-per-task",
        type=int,
        default=30000,
        help="Safety cap while collecting per-query-id samples",
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
    parser.add_argument(
        "--skip-scene-workbooks",
        action="store_true",
        help="Do not refresh per-scene combined inspection workbooks after inspection export",
    )
    return parser.parse_args()


def _inspection_rows_from_task_dir(*, out_root: Path, task_dir: Path) -> List[Dict[str, Any]]:
    """Load inspection workbook rows from one task's JSON sidecars."""

    data_root = task_dir / "data"
    if not data_root.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for data_path in sorted(data_root.rglob("*.json")):
        try:
            payload = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, Mapping):
            continue

        answer_gt = payload.get("answer_gt", {})
        if not isinstance(answer_gt, Mapping):
            answer_gt = {}
        annotation_gt = payload.get("annotation_gt", {})
        if not isinstance(annotation_gt, Mapping):
            annotation_gt = {}
        image_payload = payload.get("image", {})
        if not isinstance(image_payload, Mapping):
            image_payload = {}
        prompt_variants = payload.get("prompt_variants", {})
        if not isinstance(prompt_variants, Mapping):
            prompt_variants = {}
        trace_payload = payload.get("trace_payload", {})
        if not isinstance(trace_payload, Mapping):
            trace_payload = {}

        annotation_type = str(annotation_gt.get("type", ""))
        annotation_value = annotation_gt.get("value")
        overlay_annotation_type, overlay_annotation_value = resolve_overlay_annotation(
            annotation_type=annotation_type,
            annotation_value=annotation_value,
            trace_payload=trace_payload,
        )

        prompt = str(payload.get("prompt", ""))
        prompt_answer = str(prompt_variants.get("answer_only", prompt))
        prompt_answer_and_annotation = str(prompt_variants.get("answer_and_annotation", prompt))
        image_path = str(image_payload.get("path", ""))
        try:
            rel_data_path = data_path.relative_to(out_root).as_posix()
        except ValueError:
            rel_data_path = data_path.as_posix()

        rows.append(
            {
                "task": str(payload.get("task", task_dir.name)),
                "scene_id": str(payload.get("scene_id", task_dir.parent.name)),
                "query_id": str(payload.get("query_id", "")),
                "prompt": prompt,
                "prompt_answer": prompt_answer,
                "prompt_answer_only": prompt_answer,
                "prompt_answer_and_annotation": prompt_answer_and_annotation,
                "ground_truth_answer": {
                    "answer": answer_gt.get("value"),
                },
                "ground_truth_answer_and_annotation": {
                    "annotation": annotation_value,
                    "answer": answer_gt.get("value"),
                },
                "answer": {
                    "annotation": annotation_value,
                    "answer": answer_gt.get("value"),
                },
                "answer_annotation": annotation_value,
                "answer_type": str(answer_gt.get("type", "")),
                "annotation_type": annotation_type,
                "instance_seed": int(payload.get("instance_seed", 0)),
                "image_path": image_path,
                "data_path": str(rel_data_path),
                "overlay_annotation_type": str(overlay_annotation_type),
                "overlay_annotation_value": overlay_annotation_value,
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            str(item.get("query_id", "")),
            int(item.get("instance_seed", 0)),
            str(item.get("data_path", "")),
        ),
    )


def _scene_preview_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    domain: str,
    scene_id: str,
    task_id: str,
) -> List[Dict[str, Any]]:
    """Return the deterministic 100-row human-preview sample for a scene sheet."""

    resolved = [dict(row) for row in rows]
    if len(resolved) <= _SCENE_PREVIEW_ROWS_PER_TASK:
        return list(resolved)

    ranked = sorted(
        resolved,
        key=lambda row: hash64(
            20260518,
            f"{domain}/{scene_id}/{task_id}/{row.get('data_path', '')}",
            0,
        ),
    )[:_SCENE_PREVIEW_ROWS_PER_TASK]
    return sorted(
        ranked,
        key=lambda item: (
            str(item.get("query_id", "")),
            int(item.get("instance_seed", 0)),
            str(item.get("data_path", "")),
        ),
    )


def build_scene_review_workbook(*, out_root: Path, domain: str, scene_id: str) -> Dict[str, Any]:
    """Build one combined scene workbook with one sheet per task."""

    scene_dir = Path(out_root) / str(domain) / str(scene_id)
    rows_by_task: Dict[str, List[Dict[str, Any]]] = {}
    task_entries: Dict[str, Dict[str, Any]] = {}

    if not scene_dir.exists():
        return {
            "domain": str(domain),
            "scene_id": str(scene_id),
            "calibration_baseline": _CURRENT_CALIBRATION_BASELINE,
            "task_count": 0,
            "inspection_count": 0,
            "workbook": "",
            "tasks": {},
        }

    for task_dir in sorted(path for path in scene_dir.iterdir() if path.is_dir() and path.name.startswith("task_")):
        task_id = str(task_dir.name)
        if task_id not in TASK_REGISTRY:
            continue
        task = create_task(task_id)
        taxonomy = resolve_task_taxonomy(
            task_id,
            source_domain=str(getattr(task, "domain", "")),
            source_task_group=str(getattr(task, "task_group", "")),
        )
        if str(taxonomy.domain) != str(domain) or str(taxonomy.scene_id) != str(scene_id):
            continue
        all_rows = _inspection_rows_from_task_dir(out_root=Path(out_root), task_dir=task_dir)
        if not all_rows:
            continue
        rows = _scene_preview_rows(
            all_rows,
            domain=str(domain),
            scene_id=str(scene_id),
            task_id=str(task_id),
        )
        rows_by_task[task_id] = rows
        manifest_path = task_dir / "manifest.json"
        task_entries[task_id] = {
            "inspection_count": int(len(rows)),
            "source_inspection_count": int(len(all_rows)),
            "scene_preview_rows_per_task": int(_SCENE_PREVIEW_ROWS_PER_TASK),
            "task_manifest": str(manifest_path.relative_to(out_root).as_posix()) if manifest_path.exists() else "",
            "task_workbook": str((task_dir / f"{task_id}.xlsx").relative_to(out_root).as_posix())
            if (task_dir / f"{task_id}.xlsx").exists()
            else "",
        }

    workbook_path = scene_dir / "scene_review.xlsx"
    if not rows_by_task:
        if workbook_path.exists():
            workbook_path.unlink()
        manifest = {
            "domain": str(domain),
            "scene_id": str(scene_id),
            "calibration_baseline": _CURRENT_CALIBRATION_BASELINE,
            "task_count": 0,
            "inspection_count": 0,
            "workbook": "",
            "tasks": {},
        }
        write_json_file(scene_dir / "scene_review_manifest.json", manifest)
        return manifest

    model_stats_rows = _load_scene_model_stats_rows(
        out_root=Path(out_root),
        domain=str(domain),
        scene_id=str(scene_id),
        task_ids=sorted(rows_by_task.keys()),
    )
    task_sheets, model_stats_sheet, model_stats_count = _write_scene_inspection_excel(
        rows_by_task,
        workbook_path,
        out_root=Path(out_root),
        domain=str(domain),
        model_stats_rows=model_stats_rows,
    )
    for task_id, sheet_name in task_sheets.items():
        task_entries.setdefault(str(task_id), {})["sheet"] = str(sheet_name)

    manifest = {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "calibration_baseline": _CURRENT_CALIBRATION_BASELINE,
        "task_count": int(len(rows_by_task)),
        "inspection_count": int(sum(len(rows) for rows in rows_by_task.values())),
        "workbook": str(workbook_path.relative_to(out_root).as_posix()),
        "model_stats_sheet": str(model_stats_sheet),
        "model_stats_count": int(model_stats_count),
        "tasks": task_entries,
    }
    write_json_file(scene_dir / "scene_review_manifest.json", manifest)
    return manifest


def build_scene_review_workbooks(*, out_root: Path, scene_keys: Sequence[tuple[str, str]] | None = None) -> Dict[str, Any]:
    """Build combined scene workbooks for selected or all scenes under out_root."""

    root = Path(out_root)
    if scene_keys is None:
        discovered: List[tuple[str, str]] = []
        for domain_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            for scene_dir in sorted(path for path in domain_dir.iterdir() if path.is_dir()):
                discovered.append((str(domain_dir.name), str(scene_dir.name)))
        scene_keys = discovered

    scene_manifests: Dict[str, Any] = {}
    for domain, scene_id in sorted({(str(domain), str(scene_id)) for domain, scene_id in scene_keys}):
        manifest = build_scene_review_workbook(out_root=root, domain=str(domain), scene_id=str(scene_id))
        if int(manifest.get("task_count", 0)) <= 0:
            continue
        scene_key = f"{domain}/{scene_id}"
        scene_manifests[scene_key] = manifest
        print(
            f"[done] scene workbook: {manifest['workbook']} "
            f"(tasks={manifest['task_count']}, rows={manifest['inspection_count']})"
        )
    return scene_manifests


def _safe_query_id_dir_name(query_id: str) -> str:
    """Return filesystem-safe query-id directory label."""
    value = str(query_id).strip()
    if not value:
        return "default"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value)


def _build_inspection_rows(
    *,
    task_id: str,
    out_root: Path,
    task_dir: Path,
    seed_rows_by_query_id: Mapping[str, Sequence[Mapping[str, Any]]],
    max_attempts_per_instance: int,
) -> Dict[str, Any]:
    """Generate inspection artifacts (images/json/workbook rows) for one task."""
    rows_by_query_id: Dict[str, List[Dict[str, Any]]] = {}
    task = create_task(str(task_id))
    taxonomy = resolve_task_taxonomy(
        str(task_id),
        source_domain=str(getattr(task, "domain", "")),
        source_task_group=str(getattr(task, "task_group", "")),
    )
    for artifact_subdir in ("images", "data"):
        shutil.rmtree(task_dir / artifact_subdir, ignore_errors=True)

    for query_id in sorted(seed_rows_by_query_id.keys()):
        query_id_dir = _safe_query_id_dir_name(str(query_id))
        image_dir = task_dir / "images" / query_id_dir
        data_dir = task_dir / "data" / query_id_dir
        image_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        seed_rows = list(seed_rows_by_query_id.get(str(query_id), []))
        for index, seed_row in enumerate(seed_rows):
            instance_seed = int(seed_row.get("instance_seed", 0))
            generation_params = dict(seed_row.get("generation_params", {}) or {})
            generation_param_candidates: List[Dict[str, Any]] = []
            if str(query_id).strip():
                forced_task_params = dict(generation_params)
                forced_task_params["query_id"] = str(query_id)
                generation_param_candidates.append(forced_task_params)

                query_only_params = dict(generation_params)
                query_only_params.pop("query_id", None)
                query_only_params["query_id"] = str(query_id)
                generation_param_candidates.append(query_only_params)

                replay_params = dict(generation_params)
                replay_params.setdefault("query_id", str(query_id))
                generation_param_candidates.append(replay_params)
            else:
                # For single-sheet public tasks, trace params often include
                # resolved scene facts plus diagnostic query bookkeeping. Those
                # values are useful in review JSON but are not a stable replay
                # contract for narrowed wrapper tasks, so regenerate from the
                # sampled seed with task defaults.
                generation_param_candidates.append({})

            deduped_generation_param_candidates: List[Dict[str, Any]] = []
            seen_generation_param_candidates: set[str] = set()
            for candidate_params in generation_param_candidates:
                candidate_key = repr(sorted(candidate_params.items()))
                if candidate_key in seen_generation_param_candidates:
                    continue
                seen_generation_param_candidates.add(candidate_key)
                deduped_generation_param_candidates.append(dict(candidate_params))

            output = None
            final_seed = int(instance_seed)
            last_error: Exception | None = None
            candidate_seeds = [int(instance_seed)]
            candidate_seeds.extend(
                int(hash64(int(instance_seed), f"{str(task_id)}|{str(query_id)}|inspection", retry_index))
                for retry_index in range(1, 33)
            )
            for candidate_seed in candidate_seeds:
                for candidate_params in deduped_generation_param_candidates:
                    try:
                        candidate_output = task.generate(
                            int(candidate_seed),
                            params=dict(candidate_params),
                            max_attempts=int(max_attempts_per_instance),
                        )
                    except Exception as exc:
                        last_error = exc
                        continue
                    if str(query_id).strip() and resolve_review_query_id(candidate_output) != str(query_id):
                        continue
                    output = candidate_output
                    final_seed = int(candidate_seed)
                    break
                if output is not None:
                    break
            if output is None:
                raise RuntimeError(
                    f"{task_id} failed to build inspection row for query id {query_id!r} "
                    f"after {len(candidate_seeds)} deterministic seed attempts"
                ) from last_error

            image_path = image_dir / f"{index:04d}.png"
            output.image.save(image_path, format="PNG")
            rel_image_path = image_path.relative_to(out_root).as_posix()

            prompt_variants = dict(getattr(output, "prompt_variants", {}) or {})
            prompt_answer = str(prompt_variants.get("answer_only", output.prompt))
            prompt_answer_and_annotation = str(prompt_variants.get("answer_and_annotation", output.prompt))

            sanitized_trace_payload = sanitize_trace_payload_for_public_annotation(
                output.trace_payload if isinstance(output.trace_payload, Mapping) else {},
                annotation_gt=output.annotation_gt,
            )
            output_query_id = str(getattr(output, "query_id", "") or "")
            review_query_id = resolve_review_query_id(output)
            query_id = str(
                getattr(output, "query_id", "")
                or resolve_task_query_id(query_id=output_query_id, trace_payload=sanitized_trace_payload)
            )
            sanitized_trace_payload = inject_taxonomy_metadata(
                sanitized_trace_payload,
                task_id=str(task_id),
                taxonomy=taxonomy,
                query_id=query_id,
                registered_domain=str(getattr(task, "domain", "")),
                registered_task_group=str(getattr(task, "task_group", "")),
            )
            data_payload = {
                "task": str(task_id),
                "domain": str(taxonomy.domain),
                "scene_id": str(taxonomy.scene_id),
                "query_id": query_id,
                "instance_seed": int(final_seed),
                "prompt": prompt_answer_and_annotation,
                "prompt_variants": prompt_variants,
                "answer_gt": output.answer_gt.to_dict(),
                "annotation_gt": output.annotation_gt.to_dict(),
                "image": {
                    "path": str(rel_image_path),
                    "format": "png",
                },
                "trace_payload": sanitized_trace_payload,
                "versions": dict(output.task_versions),
            }
            data_path = data_dir / f"{index:04d}.json"
            write_json_file(data_path, data_payload)
            rel_data_path = data_path.relative_to(out_root).as_posix()

            overlay_annotation_type, overlay_annotation_value = resolve_overlay_annotation(
                annotation_type=str(output.annotation_gt.type),
                annotation_value=output.annotation_gt.value,
                trace_payload=sanitized_trace_payload,
            )
            canonical_answer = {
                "annotation": output.annotation_gt.value,
                "answer": output.answer_gt.value,
            }
            answer_only_ground_truth = {
                "answer": output.answer_gt.value,
            }
            query_params = {}
            if isinstance(sanitized_trace_payload, Mapping):
                query_spec = sanitized_trace_payload.get("query_spec")
                if isinstance(query_spec, Mapping):
                    raw_query_params = query_spec.get("params")
                    if isinstance(raw_query_params, Mapping):
                        query_params = dict(raw_query_params)
            query_id_rows = rows_by_query_id.setdefault(str(review_query_id), [])
            query_id_rows.append(
                {
                    "task": str(task_id),
                    "scene_id": str(taxonomy.scene_id),
                    "query_id": query_id,
                    "prompt": prompt_answer_and_annotation,
                    "prompt_answer": prompt_answer,
                    "prompt_answer_only": prompt_answer,
                    "prompt_answer_and_annotation": prompt_answer_and_annotation,
                    "ground_truth_answer": answer_only_ground_truth,
                    "ground_truth_answer_and_annotation": canonical_answer,
                    "answer": canonical_answer,
                    "answer_annotation": output.annotation_gt.value,
                    "answer_type": str(output.answer_gt.type),
                    "answer_support": query_params.get("answer_support"),
                    "annotation_type": str(output.annotation_gt.type),
                    "instance_seed": int(final_seed),
                    "image_path": str(rel_image_path),
                    "data_path": str(rel_data_path),
                    "overlay_annotation_type": str(overlay_annotation_type),
                    "overlay_annotation_value": overlay_annotation_value,
                }
            )

    inspection_total = 0
    for query_id in sorted(rows_by_query_id.keys()):
        rows_by_query_id[str(query_id)] = sorted(
            list(rows_by_query_id.get(str(query_id), [])),
            key=lambda item: int(item.get("instance_seed", 0)),
        )
        inspection_total += int(len(rows_by_query_id[str(query_id)]))

    workbook_path = task_dir / f"{task_id}.xlsx"
    workbook_sheets = _write_inspection_excel(rows_by_query_id, workbook_path, out_root=out_root)

    manifest = {
        "task_id": str(task_id),
        "calibration_baseline": _CURRENT_CALIBRATION_BASELINE,
        "inspection_count": int(inspection_total),
        "query_ids": {
            str(variant): int(len(seed_rows_by_query_id.get(str(variant), [])))
            for variant in sorted(seed_rows_by_query_id.keys())
        },
        "workbook": str(workbook_path.relative_to(out_root).as_posix()),
        "workbook_sheets": dict(workbook_sheets),
    }
    write_json_file(task_dir / "manifest.json", manifest)
    return manifest


def _group_random_inspection_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group one public-task random sample for workbook sheets without changing total sample count."""

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        review_key = str(
            row.get("review_query_id")
            or row.get("query_id")
            or row.get("query_id")
            or ""
        )
        grouped.setdefault(str(review_key), []).append(dict(row))
    return {str(key): list(value) for key, value in sorted(grouped.items(), key=lambda item: item[0])}


def main() -> int:
    """Entry point for task-review workflow execution."""
    args = _parse_cli()
    if int(args.random_count) <= 0:
        raise ValueError("--random-count must be > 0")
    if int(args.count_per_query_id) <= 0:
        raise ValueError("--count-per-query-id must be > 0")
    if int(args.inspection_count_per_query_id) <= 0:
        raise ValueError("--inspection-count-per-query-id must be > 0")
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
            "calibration_baseline": _CURRENT_CALIBRATION_BASELINE,
            "mode": str(args.mode),
            "seed": int(args.seed),
            "tasks": list(task_ids),
            "random_count": int(args.random_count),
            "count_per_query_id": int(args.count_per_query_id),
            "inspection_count_per_query_id": int(args.inspection_count_per_query_id),
            "balanced_inspection_by_query": bool(args.balanced_inspection_by_query),
            "max_attempts_per_instance": int(args.max_attempts_per_instance),
            "max_total_samples_per_task": int(args.max_total_samples_per_task),
            "workers": int(args.workers),
        },
        "tasks": [],
    }

    failed_distribution_tasks: List[str] = []
    touched_scene_keys: set[tuple[str, str]] = set()

    for task_id in task_ids:
        task = create_task(str(task_id))
        taxonomy = resolve_task_taxonomy(
            str(task_id),
            source_domain=str(getattr(task, "domain", "")),
            source_task_group=str(getattr(task, "task_group", "")),
        )
        task_dir = _resolve_task_review_dir(out_root=out_root, task_id=str(task_id), task_obj=task)
        task_dir.mkdir(parents=True, exist_ok=True)

        task_summary: Dict[str, Any] = {
            "task_id": str(task_id),
            "domain": str(taxonomy.domain),
            "scene_id": str(taxonomy.scene_id),
            "source_domain": str(task.domain),
            "task_group": str(task.task_group),
            "reports": {},
        }
        touched_scene_keys.add((str(taxonomy.domain), str(taxonomy.scene_id)))

        random_rows: List[Dict[str, Any]] = []
        random_report: Dict[str, Any] | None = None
        distribution_query_id_rows: Dict[str, List[Dict[str, Any]]] | None = None

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

            has_query_ids = bool(random_report["query_id_distribution"]["has_query_ids"])
            query_id_rows: Dict[str, List[Dict[str, Any]]] | None = None
            collection_meta: Dict[str, Any] | None = None
            if has_query_ids:
                collected = collect_query_id_samples(
                    task_id=str(task_id),
                    target_count_per_query_id=int(args.count_per_query_id),
                    seed=int(args.seed),
                    max_attempts_per_instance=int(args.max_attempts_per_instance),
                    max_total_samples_per_task=int(args.max_total_samples_per_task),
                    workers=int(args.workers),
                    collector=_answer_collector,
                )
                query_id_rows = {
                    str(variant): list(collected.get("samples_by_query_id", {}).get(str(variant), []))
                    for variant in list(collected.get("expected_query_ids", []))
                }
                distribution_query_id_rows = dict(query_id_rows)
                collection_meta = {
                    key: collected.get(key)
                    for key in (
                        "target_count_per_query_id",
                        "total_generated",
                        "expected_query_ids",
                        "generated_query_id_counts",
                        "collected_query_id_counts",
                        "incomplete_query_ids",
                        "generation_error_counts",
                    )
                }

            distribution_report = _build_distribution_review_report(
                task_id=str(task_id),
                task_group=str(task.task_group),
                domain=str(taxonomy.domain),
                scene_id=str(taxonomy.scene_id),
                random_rows=random_rows,
                random_report=random_report,
                query_id_rows=query_id_rows,
                query_id_collection_meta=collection_meta,
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
            seed_rows_by_query_id: Dict[str, List[Dict[str, Any]]]
            random_rows_for_inspection: List[Dict[str, Any]] | None = None
            if not bool(args.balanced_inspection_by_query):
                random_rows_for_inspection = list(random_rows)
                if not random_rows_for_inspection:
                    random_rows_for_inspection = generate_random_samples(
                        task_id=str(task_id),
                        count=int(args.random_count),
                        seed=int(args.seed),
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                seed_rows_by_query_id = _group_random_inspection_rows(random_rows_for_inspection)
            elif random_report is None:
                inspection_collected = collect_query_id_samples(
                    task_id=str(task_id),
                    target_count_per_query_id=int(args.inspection_count_per_query_id),
                    seed=int(args.seed) + 17,
                    max_attempts_per_instance=int(args.max_attempts_per_instance),
                    max_total_samples_per_task=int(args.max_total_samples_per_task),
                    workers=int(args.workers),
                    collector=_answer_collector,
                )
                expected_query_ids = list(inspection_collected.get("expected_query_ids", []))
                if not expected_query_ids:
                    expected_query_ids = sorted(inspection_collected.get("samples_by_query_id", {}).keys())
                seed_rows_by_query_id = {
                    str(variant): list(inspection_collected.get("samples_by_query_id", {}).get(str(variant), []))
                    for variant in expected_query_ids
                }
                if not seed_rows_by_query_id:
                    fallback_rows = generate_random_samples(
                        task_id=str(task_id),
                        count=int(args.inspection_count_per_query_id),
                        seed=int(args.seed) + 17,
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                    seed_rows_by_query_id = {"": list(fallback_rows)}
            elif bool(random_report["query_id_distribution"]["has_query_ids"]):
                if distribution_query_id_rows is not None and str(args.mode) == "full":
                    seed_rows_by_query_id = {
                        str(variant): list(rows[: int(args.inspection_count_per_query_id)])
                        for variant, rows in distribution_query_id_rows.items()
                    }
                else:
                    inspection_collected = collect_query_id_samples(
                        task_id=str(task_id),
                        target_count_per_query_id=int(args.inspection_count_per_query_id),
                        seed=int(args.seed) + 17,
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        max_total_samples_per_task=int(args.max_total_samples_per_task),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                    seed_rows_by_query_id = {
                        str(variant): list(inspection_collected.get("samples_by_query_id", {}).get(str(variant), []))
                        for variant in list(inspection_collected.get("expected_query_ids", []))
                    }
            else:
                if random_rows_for_inspection is None:
                    random_rows_for_inspection = generate_random_samples(
                        task_id=str(task_id),
                        count=int(args.inspection_count_per_query_id),
                        seed=int(args.seed) + 17,
                        max_attempts_per_instance=int(args.max_attempts_per_instance),
                        workers=int(args.workers),
                        collector=_answer_collector,
                    )
                seed_rows_by_query_id = {
                    "": list(random_rows_for_inspection[: int(args.inspection_count_per_query_id)]),
                }

            inspection_manifest = _build_inspection_rows(
                task_id=str(task_id),
                out_root=out_root,
                task_dir=task_dir,
                seed_rows_by_query_id=seed_rows_by_query_id,
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
    if str(args.mode) in {"full", "inspection"} and not bool(args.skip_scene_workbooks):
        summary["scene_workbooks"] = build_scene_review_workbooks(
            out_root=out_root,
            scene_keys=sorted(touched_scene_keys),
        )
    summary_path = out_root / "review_summary.json"
    write_json_file(summary_path, summary)
    print(f"[done] wrote review summary: {summary_path}")

    if failed_distribution_tasks and str(args.mode) in {"full", "distribution"} and not bool(args.allow_fail):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
