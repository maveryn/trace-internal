#!/usr/bin/env python3
"""Audit bbox annotation sizes from existing task-review artifacts only."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image

from trace.core.json_io import write_json_file
from trace.core.scene_package_migration import SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES


DEFAULT_DOMAINS = (
    "charts",
    "games",
    "geometry",
    "graph",
    "icons",
    "illustrations",
    "three_d",
)
DEFAULT_REVIEW_ROOT = Path("review/task-reviews")
DEFAULT_OUTPUT_ROOT = Path("review/annotation-quality")
DEFAULT_JSON_REPORT = DEFAULT_OUTPUT_ROOT / "bbox_min_side_from_task_reviews.json"
DEFAULT_MD_REPORT = DEFAULT_OUTPUT_ROOT / "bbox_min_side_from_task_reviews.md"
DEFAULT_MIN_SIDE_PX = 24.0
SCHEMA_ID = "trace_review_bbox_min_side_audit_v1"

BBOX_ANNOTATION_TYPES = frozenset(
    {
        "bbox",
        "bbox_set",
        "bbox_sequence",
        "bbox_map",
        "bbox_set_map",
    }
)
KNOWN_ANNOTATION_TYPES = (
    "bbox_set_map",
    "point_set_map",
    "bbox_sequence",
    "point_sequence",
    "segment_set",
    "bbox_map",
    "point_map",
    "bbox_set",
    "point_set",
    "segment",
    "bbox",
    "point",
)


@dataclass(frozen=True)
class BboxWitness:
    path: str
    bbox: tuple[float, float, float, float]


def flatten_bbox_annotation(annotation_type: str, value: Any) -> tuple[list[BboxWitness], list[str]]:
    """Return every bbox witness from one public bbox-family annotation value."""

    witnesses: list[BboxWitness] = []
    errors: list[str] = []

    def add_box(raw: Any, path: str) -> None:
        box = _coerce_bbox(raw)
        if box is None:
            errors.append(f"{path}: expected [x0, y0, x1, y1]")
            return
        witnesses.append(BboxWitness(path=path, bbox=box))

    if annotation_type == "bbox":
        add_box(value, "annotation")
    elif annotation_type in {"bbox_set", "bbox_sequence"}:
        if not isinstance(value, list):
            errors.append("annotation: expected list of bboxes")
        else:
            for index, item in enumerate(value):
                add_box(item, f"annotation[{index}]")
    elif annotation_type == "bbox_map":
        if not isinstance(value, Mapping):
            errors.append("annotation: expected object mapping keys to bboxes")
        else:
            for key, item in sorted(value.items()):
                add_box(item, f"annotation.{key}")
    elif annotation_type == "bbox_set_map":
        if not isinstance(value, Mapping):
            errors.append("annotation: expected object mapping keys to bbox lists")
        else:
            for key, items in sorted(value.items()):
                if not isinstance(items, list):
                    errors.append(f"annotation.{key}: expected list of bboxes")
                    continue
                for index, item in enumerate(items):
                    add_box(item, f"annotation.{key}[{index}]")
    else:
        errors.append(f"unsupported bbox annotation type: {annotation_type}")
    return witnesses, errors


def collect_bbox_min_side_audit(
    *,
    review_root: Path = DEFAULT_REVIEW_ROOT,
    docs_root: Path = Path("docs/tasks"),
    domains: Sequence[str] = DEFAULT_DOMAINS,
    min_side_px: float = DEFAULT_MIN_SIDE_PX,
) -> dict[str, Any]:
    """Collect bbox-size observations from already-written task-review samples."""

    records: list[dict[str, Any]] = []
    totals = {
        "scene_count": 0,
        "task_count": 0,
        "bbox_task_count": 0,
        "non_bbox_task_count": 0,
        "missing_review_artifact_task_count": 0,
        "sample_count": 0,
        "bbox_count": 0,
        "failing_task_count": 0,
        "invalid_task_count": 0,
        "doc_runtime_mismatch_task_count": 0,
    }

    for domain in domains:
        scenes = sorted(SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES.get(domain, frozenset()))
        for scene_id in scenes:
            totals["scene_count"] += 1
            task_ids = _task_ids_for_scene(docs_root=docs_root, domain=domain, scene_id=scene_id)
            if not task_ids:
                task_ids = _task_ids_from_review_root(review_root=review_root, domain=domain, scene_id=scene_id)
            for task_id in task_ids:
                totals["task_count"] += 1
                record = _audit_task(
                    review_root=review_root,
                    docs_root=docs_root,
                    domain=domain,
                    scene_id=scene_id,
                    task_id=task_id,
                    min_side_px=min_side_px,
                )
                records.append(record)
                totals["sample_count"] += int(record["sample_count"])
                totals["bbox_count"] += int(record["bbox_count"])
                if record["status"] == "missing_review_artifacts":
                    totals["missing_review_artifact_task_count"] += 1
                elif bool(record["bbox_family_runtime"]):
                    totals["bbox_task_count"] += 1
                else:
                    totals["non_bbox_task_count"] += 1
                if int(record["failure_count"]) > 0:
                    totals["failing_task_count"] += 1
                if int(record["invalid_count"]) > 0:
                    totals["invalid_task_count"] += 1
                if bool(record["doc_runtime_mismatch"]):
                    totals["doc_runtime_mismatch_task_count"] += 1

    totals["pass"] = (
        totals["failing_task_count"] == 0
        and totals["invalid_task_count"] == 0
        and totals["missing_review_artifact_task_count"] == 0
    )
    return {
        "schema": SCHEMA_ID,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "review_root": str(review_root),
        "docs_root": str(docs_root),
        "domains": list(domains),
        "min_side_px": float(min_side_px),
        "totals": totals,
        "records": records,
    }


def render_markdown_report(report: Mapping[str, Any]) -> str:
    """Render a compact Markdown report for human review."""

    totals = report.get("totals", {})
    lines = [
        "# Bbox Minimum-Side Audit From Existing Task Reviews",
        "",
        f"- Checked at: `{report.get('checked_at', '')}`",
        f"- Review root: `{report.get('review_root', '')}`",
        f"- Minimum required side: `{report.get('min_side_px', DEFAULT_MIN_SIDE_PX)} px`",
        f"- Scenes: `{totals.get('scene_count', 0)}`",
        f"- Tasks: `{totals.get('task_count', 0)}`",
        f"- Bbox-family runtime tasks: `{totals.get('bbox_task_count', 0)}`",
        f"- Samples inspected: `{totals.get('sample_count', 0)}`",
        f"- Bboxes inspected: `{totals.get('bbox_count', 0)}`",
        f"- Failing bbox tasks: `{totals.get('failing_task_count', 0)}`",
        f"- Invalid bbox tasks: `{totals.get('invalid_task_count', 0)}`",
        f"- Missing review-artifact tasks: `{totals.get('missing_review_artifact_task_count', 0)}`",
        f"- Doc/runtime annotation mismatches: `{totals.get('doc_runtime_mismatch_task_count', 0)}`",
        "",
    ]

    failing = [record for record in report.get("records", []) if int(record.get("failure_count", 0)) > 0]
    invalid = [record for record in report.get("records", []) if int(record.get("invalid_count", 0)) > 0]
    missing = [record for record in report.get("records", []) if record.get("status") == "missing_review_artifacts"]
    if failing or invalid or missing:
        lines.extend(["## Attention Needed", ""])
        for record in failing[:100]:
            lines.append(
                "- FAIL "
                f"`{record['domain']}/{record['scene_id']}/{record['task_id']}`: "
                f"min_side=`{_format_number(record.get('min_side_px_observed'))}` "
                f"failures=`{record.get('failure_count', 0)}`"
            )
        for record in invalid[:100]:
            lines.append(
                "- INVALID "
                f"`{record['domain']}/{record['scene_id']}/{record['task_id']}`: "
                f"invalid=`{record.get('invalid_count', 0)}`"
            )
        for record in missing[:100]:
            lines.append(f"- MISSING `{record['domain']}/{record['scene_id']}/{record['task_id']}`")
        lines.append("")

    lines.extend(
        [
            "## Bbox-Family Task Observations",
            "",
            "| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for record in report.get("records", []):
        if not bool(record.get("bbox_family_runtime")) and record.get("status") != "missing_review_artifacts":
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(record.get("domain", "")),
                    str(record.get("scene_id", "")),
                    f"`{record.get('task_id', '')}`",
                    str(record.get("runtime_annotation_types", [])),
                    str(record.get("sample_count", 0)),
                    str(record.get("bbox_count", 0)),
                    _format_number(record.get("min_width_px_observed")),
                    _format_number(record.get("min_height_px_observed")),
                    _format_number(record.get("min_side_px_observed")),
                    str(record.get("status", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def write_reports(report: Mapping[str, Any], *, json_path: Path = DEFAULT_JSON_REPORT, md_path: Path = DEFAULT_MD_REPORT) -> None:
    """Write JSON and Markdown reports."""

    write_json_file(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown_report(report), encoding="utf-8")


def _audit_task(
    *,
    review_root: Path,
    docs_root: Path,
    domain: str,
    scene_id: str,
    task_id: str,
    min_side_px: float,
) -> dict[str, Any]:
    doc_annotation_type = parse_doc_annotation_type(_read_text(docs_root / domain / scene_id / f"{task_id}.md"))
    sample_paths = sorted((review_root / domain / scene_id / task_id / "data").glob("*/*.json"))
    if not sample_paths:
        return _base_task_record(
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            doc_annotation_type=doc_annotation_type,
            status="missing_review_artifacts",
        )

    runtime_types: set[str] = set()
    query_ids: set[str] = set()
    bbox_count = 0
    empty_bbox_sample_count = 0
    invalids: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    min_width: float | None = None
    min_height: float | None = None
    min_side: float | None = None
    image_missing_count = 0
    out_of_bounds_count = 0

    for sample_path in sample_paths:
        payload = _load_json(sample_path)
        annotation = payload.get("annotation_gt")
        if not isinstance(annotation, Mapping):
            invalids.append(_sample_issue(sample_path, "annotation_gt is missing or not an object"))
            continue
        annotation_type = str(annotation.get("type", ""))
        runtime_types.add(annotation_type)
        query_ids.add(str(payload.get("query_id") or sample_path.parent.name))
        if annotation_type not in BBOX_ANNOTATION_TYPES:
            continue
        witnesses, errors = flatten_bbox_annotation(annotation_type, annotation.get("value"))
        if not witnesses:
            empty_bbox_sample_count += 1
        for error in errors:
            invalids.append(_sample_issue(sample_path, error))
        image_size = _resolve_image_size(review_root=review_root, payload=payload)
        if image_size is None:
            image_missing_count += 1
        for witness in witnesses:
            bbox_count += 1
            x0, y0, x1, y1 = witness.bbox
            width = x1 - x0
            height = y1 - y0
            side = min(width, height)
            min_width = width if min_width is None else min(min_width, width)
            min_height = height if min_height is None else min(min_height, height)
            min_side = side if min_side is None else min(min_side, side)
            issue = {
                "sample_path": str(sample_path),
                "query_id": str(payload.get("query_id") or sample_path.parent.name),
                "annotation_path": witness.path,
                "bbox": list(witness.bbox),
                "width_px": width,
                "height_px": height,
                "side_px": side,
            }
            if width <= 0 or height <= 0:
                invalids.append({**issue, "reason": "non_positive_dimensions"})
            if image_size is not None and not _bbox_inside_image(witness.bbox, image_size):
                out_of_bounds_count += 1
                invalids.append({**issue, "reason": f"bbox_outside_image_{image_size[0]}x{image_size[1]}"})
            if width < min_side_px or height < min_side_px:
                failures.append({**issue, "reason": "bbox_side_below_minimum"})

    bbox_family_runtime = any(annotation_type in BBOX_ANNOTATION_TYPES for annotation_type in runtime_types)
    doc_runtime_mismatch = bool(doc_annotation_type and runtime_types and doc_annotation_type not in runtime_types)
    status = "not_applicable"
    if bbox_family_runtime:
        status = "pass"
    if failures:
        status = "fail"
    if invalids:
        status = "invalid" if not failures else "fail"

    record = _base_task_record(
        domain=domain,
        scene_id=scene_id,
        task_id=task_id,
        doc_annotation_type=doc_annotation_type,
        status=status,
    )
    record.update(
        {
            "runtime_annotation_types": sorted(runtime_types),
            "query_ids": sorted(query_ids),
            "bbox_family_runtime": bbox_family_runtime,
            "sample_count": len(sample_paths),
            "bbox_count": bbox_count,
            "empty_bbox_sample_count": empty_bbox_sample_count,
            "image_missing_count": image_missing_count,
            "out_of_bounds_count": out_of_bounds_count,
            "min_width_px_observed": _round_or_none(min_width),
            "min_height_px_observed": _round_or_none(min_height),
            "min_side_px_observed": _round_or_none(min_side),
            "failure_count": len(failures),
            "invalid_count": len(invalids),
            "doc_runtime_mismatch": doc_runtime_mismatch,
            "failures": failures[:20],
            "invalids": invalids[:20],
        }
    )
    return record


def parse_doc_annotation_type(doc_text: str) -> str:
    """Extract a task doc's declared annotation schema when present."""

    for raw_line in str(doc_text).splitlines():
        line = raw_line.strip()
        if "Annotation schema" not in line and "Annotation type" not in line:
            continue
        for annotation_type in KNOWN_ANNOTATION_TYPES:
            if re.search(rf"`{re.escape(annotation_type)}`|\b{re.escape(annotation_type)}\b", line):
                return annotation_type
    return ""


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--docs-root", type=Path, default=Path("docs/tasks"))
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD_REPORT)
    parser.add_argument("--min-side-px", type=float, default=DEFAULT_MIN_SIDE_PX)
    parser.add_argument("--domains", default=",".join(DEFAULT_DOMAINS))
    parser.add_argument("--fail-on-issue", action="store_true", help="Exit nonzero when bbox failures are found.")
    args = parser.parse_args(argv)

    domains = tuple(item.strip() for item in str(args.domains).split(",") if item.strip())
    report = collect_bbox_min_side_audit(
        review_root=args.review_root,
        docs_root=args.docs_root,
        domains=domains,
        min_side_px=float(args.min_side_px),
    )
    write_reports(report, json_path=args.out_json, md_path=args.out_md)
    totals = report["totals"]
    print(
        "bbox min-side audit: "
        f"tasks={totals['task_count']} bbox_tasks={totals['bbox_task_count']} "
        f"failures={totals['failing_task_count']} invalid={totals['invalid_task_count']} "
        f"missing={totals['missing_review_artifact_task_count']}"
    )
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    if bool(args.fail_on_issue) and (totals["failing_task_count"] or totals["invalid_task_count"]):
        return 1
    return 0


def _base_task_record(*, domain: str, scene_id: str, task_id: str, doc_annotation_type: str, status: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "scene_id": scene_id,
        "task_id": task_id,
        "doc_annotation_type": doc_annotation_type,
        "runtime_annotation_types": [],
        "query_ids": [],
        "bbox_family_runtime": False,
        "sample_count": 0,
        "bbox_count": 0,
        "empty_bbox_sample_count": 0,
        "image_missing_count": 0,
        "out_of_bounds_count": 0,
        "min_width_px_observed": None,
        "min_height_px_observed": None,
        "min_side_px_observed": None,
        "failure_count": 0,
        "invalid_count": 0,
        "doc_runtime_mismatch": False,
        "failures": [],
        "invalids": [],
        "status": status,
    }


def _coerce_bbox(raw: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    try:
        return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    except (TypeError, ValueError):
        return None


def _task_ids_for_scene(*, docs_root: Path, domain: str, scene_id: str) -> list[str]:
    return sorted(path.stem for path in (docs_root / domain / scene_id).glob("task_*.md"))


def _task_ids_from_review_root(*, review_root: Path, domain: str, scene_id: str) -> list[str]:
    scene_dir = review_root / domain / scene_id
    if not scene_dir.exists():
        return []
    return sorted(path.name for path in scene_dir.iterdir() if path.is_dir() and path.name.startswith("task_"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_image_size(*, review_root: Path, payload: Mapping[str, Any]) -> tuple[int, int] | None:
    image = payload.get("image")
    if not isinstance(image, Mapping):
        return None
    image_path = image.get("path")
    if not image_path:
        return None
    path = Path(str(image_path))
    if not path.is_absolute():
        path = review_root / path
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def _bbox_inside_image(bbox: tuple[float, float, float, float], image_size: tuple[int, int]) -> bool:
    x0, y0, x1, y1 = bbox
    width, height = image_size
    return 0 <= x0 <= width and 0 <= x1 <= width and 0 <= y0 <= height and 0 <= y1 <= height


def _sample_issue(sample_path: Path, reason: str) -> dict[str, Any]:
    return {"sample_path": str(sample_path), "reason": reason}


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
