#!/usr/bin/env python3
"""Inventory tasks for scalar point/bbox annotation review.

The inventory is static-first by design. It reads docs/ACTIVE_TASK_INVENTORY.md
and task docs without importing the global task registry, because global
inventory imports may be blocked by unrelated broken task modules.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import traceback
from typing import Any, Iterable, Mapping


DEFAULT_ACTIVE_INVENTORY = Path("docs/ACTIVE_TASK_INVENTORY.md")
DEFAULT_OUTPUT_ROOT = Path("review/scalar-annotation")
DEFAULT_JSON = DEFAULT_OUTPUT_ROOT / "stage2_inventory.json"
DEFAULT_MD = DEFAULT_OUTPUT_ROOT / "stage2_inventory.md"

SCHEMA_ID = "trace_scalar_annotation_inventory_v0"

SCALAR_TYPES = {"point", "bbox", "segment"}
SET_TYPES = {"point_set", "bbox_set", "segment_set"}
SEQUENCE_TYPES = {"point_sequence", "bbox_sequence"}
KEYED_TYPES = {
    "point_map",
    "bbox_map",
    "point_set_map",
    "bbox_set_map",
}
KNOWN_ANNOTATION_TYPES = SCALAR_TYPES | SET_TYPES | SEQUENCE_TYPES | KEYED_TYPES
SCALAR_CANDIDATE_CLASSIFICATIONS = {
    "scalar_point_candidate",
    "scalar_bbox_candidate",
    "scalar_segment_candidate",
}

COUNT_OBJECTIVE_RE = re.compile(r"(^|_)count($|_)|count_", re.IGNORECASE)
SCALAR_HINT_RE = re.compile(
    r"\b(exactly one|one pixel point|one pixel box|marks one|mark one|single "
    r"(?:point|box|bbox|mark|witness)|selected [^.\n]*(?:point|box|bbox|mark|item|interval|region|tile))\b",
    re.IGNORECASE,
)
VARIABLE_HINT_RE = re.compile(
    r"\b(all|every|counted|matching|qualifying|included|path|route|sequence|multiple|zero or more|one or more)\b",
    re.IGNORECASE,
)
MULTI_WITNESS_HINT_RE = re.compile(
    r"\b("
    r"centers of every|"
    r"row-clue rail box, column-clue rail box, and|"
    r"marked row clue box, marked row box, and|"
    r"contains bboxes for|"
    r"selected option box followed by|"
    r"target-duration note bbox and|"
    r"followed by ordered"
    r")\b",
    re.IGNORECASE,
)
ROLE_HINT_RE = re.compile(
    r"\b(source|target|reference|selected_option|selected option|input|output|before|after|left|right|start|end|endpoint|operand)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TaskRef:
    domain: str
    scene_id: str
    task_id: str


@dataclass(frozen=True)
class StatusSummary:
    path: str
    exists: bool
    passed: bool | None


@dataclass(frozen=True)
class InventoryRecord:
    domain: str
    scene_id: str
    task_id: str
    doc_path: str
    source_path: str
    annotation_type_doc: str
    annotation_type_generated: str
    answer_schema_doc: str
    scene_package_registered: bool
    review_target_scene: bool
    manual_code_audit: StatusSummary
    taxonomy_review: StatusSummary
    source_layout_test: StatusSummary
    classification: str
    rationale: str
    classification_sources: list[str]
    generated_ok: bool | None
    blocked_error: str


def parse_active_inventory(text: str) -> list[TaskRef]:
    """Parse task refs from docs/ACTIVE_TASK_INVENTORY.md."""

    records: list[TaskRef] = []
    domain = ""
    scene_id = ""
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        domain_match = re.match(r"^###\s+([a-z0-9_]+)\s*$", line)
        if domain_match:
            domain = str(domain_match.group(1))
            scene_id = ""
            continue
        scene_match = re.match(r"^####\s+([a-z0-9_]+)\s+\(\d+\)\s*$", line)
        if scene_match:
            scene_id = str(scene_match.group(1))
            continue
        task_match = re.match(r"^-\s+`(task_[^`]+)`\s*$", line)
        if task_match and domain and scene_id:
            task_id = str(task_match.group(1))
            records.append(TaskRef(domain=domain, scene_id=scene_id, task_id=task_id))
    return records


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _status_summary(path: Path) -> StatusSummary:
    data = _load_json(path)
    passed = bool(data.get("passed")) if "passed" in data else None
    return StatusSummary(path=str(path), exists=path.exists(), passed=passed)


def _first_regex(text: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return str(match.group(1)).strip()
    return ""


def parse_doc_annotation_type(doc_text: str) -> str:
    """Return the first explicit annotation schema/type from one task doc."""

    for raw_line in str(doc_text).splitlines():
        line = raw_line.strip()
        if "Annotation schema" not in line and "Annotation type" not in line:
            continue
        for annotation_type in sorted(KNOWN_ANNOTATION_TYPES, key=len, reverse=True):
            if re.search(rf"`{re.escape(annotation_type)}`|\b{re.escape(annotation_type)}\b", line):
                return annotation_type

    contract = re.search(r"## Annotation Contract\s*(.*?)(?:\n## |\Z)", doc_text, flags=re.IGNORECASE | re.DOTALL)
    if contract:
        contract_text = str(contract.group(1))
        for annotation_type in sorted(KNOWN_ANNOTATION_TYPES, key=len, reverse=True):
            if re.search(rf"`{re.escape(annotation_type)}`|\b{re.escape(annotation_type)}\b", contract_text):
                return annotation_type

    return _first_regex(
        doc_text,
        (
            r"Annotation schema:\s*`?([a-z0-9_]+)`?",
            r"`annotation_gt\.type\s*=\s*([a-z0-9_]+)`",
            r"annotation_gt\.type`?:\s*`?([a-z0-9_]+)`?",
            r"Annotation type:\s*`?(?:annotation_gt\.type\s*=\s*)?([a-z0-9_]+)`?",
        ),
    )


def parse_doc_answer_schema(doc_text: str) -> str:
    """Return the first explicit answer schema/type from one task doc."""

    return _first_regex(
        doc_text,
        (
            r"Answer schema:\s*`?([a-z0-9_]+)`?",
            r"Answer type:\s*`?([a-z0-9_]+)`?",
            r"`answer_gt\.type\s*=\s*([a-z0-9_]+)`",
            r"answer_gt\.type`?:\s*`?([a-z0-9_]+)`?",
        ),
    )


def _program_contract_text(doc_text: str) -> str:
    match = re.search(r"## Program Contract\s*(.*?)(?:\n## |\Z)", doc_text, flags=re.IGNORECASE | re.DOTALL)
    return str(match.group(1)).strip() if match else ""


def classify_annotation_contract(
    *,
    task_id: str,
    annotation_type: str,
    doc_text: str,
    generated_annotation_type: str = "",
) -> tuple[str, str, list[str]]:
    """Classify one task's current annotation contract for scalar rollout."""

    sources = ["doc"] if annotation_type else []
    if generated_annotation_type:
        sources.append("generated_sample")
    effective_type = str(generated_annotation_type or annotation_type).strip()
    objective = str(task_id).rsplit("__", 1)[-1]
    lower_doc = str(doc_text).lower()
    program = _program_contract_text(doc_text).lower()

    if not effective_type:
        return "needs_manual_decision", "No annotation schema was found in the task doc or generated sample.", sources
    if effective_type in SCALAR_TYPES:
        return "already_scalar", f"Task already uses scalar `{effective_type}` annotation.", sources
    if effective_type in SEQUENCE_TYPES:
        return "stay_set_or_sequence", f"`{effective_type}` is ordered and is not a scalar witness.", sources
    if effective_type in {"point_set_map", "bbox_set_map"}:
        return "stay_map", f"`{effective_type}` binds key-grouped witness collections.", sources
    if effective_type in {"point_map", "bbox_map"}:
        if ROLE_HINT_RE.search(program) or ROLE_HINT_RE.search(lower_doc):
            return "stay_map", f"`{effective_type}` appears to bind semantic roles.", sources
        return (
            "needs_manual_decision",
            f"`{effective_type}` may be a single selected witness encoded as a map; verify key binding manually.",
            sources,
        )
    if effective_type not in SET_TYPES:
        return "needs_manual_decision", f"Unsupported or unknown annotation type `{effective_type}`.", sources

    if COUNT_OBJECTIVE_RE.search(objective) or "count(" in program:
        return "stay_set_or_sequence", "Count-like task; set cardinality remains part of the contract.", sources
    if MULTI_WITNESS_HINT_RE.search(lower_doc):
        return "stay_set_or_sequence", "Task doc describes multiple annotation witnesses.", sources
    if VARIABLE_HINT_RE.search(lower_doc) and not SCALAR_HINT_RE.search(lower_doc):
        return "stay_set_or_sequence", "Task doc uses variable-cardinality witness language.", sources
    if SCALAR_HINT_RE.search(lower_doc) or SCALAR_HINT_RE.search(program):
        target_by_set_type = {
            "point_set": "scalar_point_candidate",
            "bbox_set": "scalar_bbox_candidate",
            "segment_set": "scalar_segment_candidate",
        }
        scalar_type_by_set_type = {
            "point_set": "point",
            "bbox_set": "bbox",
            "segment_set": "segment",
        }
        target = target_by_set_type[str(effective_type)]
        scalar_type = scalar_type_by_set_type[str(effective_type)]
        return target, f"`{effective_type}` doc describes exactly one witness; migrate to `{scalar_type}`.", sources
    if "string_label" in lower_doc or "option_letter" in lower_doc:
        return (
            "needs_manual_decision",
            f"`{effective_type}` with label/option answer may be single-selection, but docs do not prove fixed cardinality.",
            sources,
        )
    return "needs_manual_decision", f"`{effective_type}` requires manual cardinality review.", sources


def _source_path_for_task(task: TaskRef) -> Path:
    objective = task.task_id.rsplit("__", 1)[-1]
    return Path("trace/tasks") / task.domain / task.scene_id / f"{objective}.py"


def _doc_path_for_task(task: TaskRef) -> Path:
    return Path("docs/tasks") / task.domain / task.scene_id / f"{task.task_id}.md"


def classify_scalar_annotation_task_docs(
    *,
    domain: str,
    scene_id: str,
    task_ids: Iterable[str],
    docs_root: Path = Path("docs/tasks"),
) -> list[dict[str, Any]]:
    """Classify scalar annotation status for explicit task docs.

    This helper is intentionally static and import-free. Review-generation gates
    use it before writing artifacts, when unrelated task modules may be broken.
    """

    records: list[dict[str, Any]] = []
    for task_id in sorted({str(task_id) for task_id in task_ids if str(task_id).strip()}):
        doc_path = Path(docs_root) / str(domain) / str(scene_id) / f"{task_id}.md"
        doc_text = _read_text(doc_path)
        annotation_type = parse_doc_annotation_type(doc_text)
        classification, rationale, sources = classify_annotation_contract(
            task_id=str(task_id),
            annotation_type=str(annotation_type),
            doc_text=doc_text,
        )
        records.append(
            {
                "domain": str(domain),
                "scene_id": str(scene_id),
                "task_id": str(task_id),
                "doc_path": str(doc_path),
                "annotation_type": str(annotation_type),
                "classification": str(classification),
                "rationale": str(rationale),
                "classification_sources": list(sources),
            }
        )
    return records


def scalar_annotation_review_failures_for_tasks(
    *,
    domain: str,
    scene_id: str,
    task_ids: Iterable[str],
    docs_root: Path = Path("docs/tasks"),
) -> list[str]:
    """Return blocking scalar-annotation failures for explicit task docs."""

    failures: list[str] = []
    for record in classify_scalar_annotation_task_docs(
        domain=str(domain),
        scene_id=str(scene_id),
        task_ids=task_ids,
        docs_root=docs_root,
    ):
        if str(record.get("classification", "")) not in SCALAR_CANDIDATE_CLASSIFICATIONS:
            continue
        failures.append(
            f"{record['domain']}/{record['scene_id']} -> {record['doc_path']} "
            f"still classified as {record['classification']}: {record['rationale']}"
        )
    return failures


def _smoke_task(task_id: str, *, max_attempts: int) -> dict[str, Any]:
    try:
        from trace.core.seed import hash64
        from trace.tasks import create_task

        instance_seed = int(hash64(0, f"{task_id}:scalar_annotation_inventory", 0))
        output = create_task(task_id).generate(instance_seed, params={}, max_attempts=max_attempts)
        return {
            "ok": True,
            "annotation_type": str(getattr(getattr(output, "annotation_gt", None), "type", "")),
            "answer_type": str(getattr(getattr(output, "answer_gt", None), "type", "")),
        }
    except Exception as exc:  # pragma: no cover - exact task failures vary with worktree state.
        return {
            "ok": False,
            "annotation_type": "",
            "answer_type": "",
            "error": "".join(traceback.format_exception_only(type(exc), exc)).strip(),
        }


def _scene_package_maps() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    from trace.core.source_layout_policy import (
        SCENE_PACKAGE_SOURCE_LAYOUT_SCENES,
        SCENE_PACKAGE_REVIEW_TARGET_SCENES,
    )

    migrated = {str(domain): {str(scene) for scene in scenes} for domain, scenes in SCENE_PACKAGE_SOURCE_LAYOUT_SCENES.items()}
    review = {str(domain): {str(scene) for scene in scenes} for domain, scenes in SCENE_PACKAGE_REVIEW_TARGET_SCENES.items()}
    return migrated, review


def build_inventory(
    *,
    active_inventory_path: Path = DEFAULT_ACTIVE_INVENTORY,
    review_root: Path = Path("review/task-reviews"),
    smoke_tasks: set[str] | None = None,
    smoke_samples: int = 0,
    max_attempts: int = 20,
) -> dict[str, Any]:
    """Build the scalar annotation inventory payload."""

    smoke_tasks = set(smoke_tasks or set())
    tasks = parse_active_inventory(_read_text(active_inventory_path))
    migrated_scenes, review_scenes = _scene_package_maps()
    records: list[InventoryRecord] = []

    for task in tasks:
        doc_path = _doc_path_for_task(task)
        source_path = _source_path_for_task(task)
        doc_text = _read_text(doc_path)
        doc_annotation_type = parse_doc_annotation_type(doc_text)
        doc_answer_schema = parse_doc_answer_schema(doc_text)

        generated_annotation_type = ""
        generated_ok: bool | None = None
        blocked_error = ""
        should_smoke = smoke_samples > 0 and (not smoke_tasks or task.task_id in smoke_tasks)
        if should_smoke:
            smoke = _smoke_task(task.task_id, max_attempts=max_attempts)
            generated_ok = bool(smoke.get("ok"))
            generated_annotation_type = str(smoke.get("annotation_type", ""))
            if not generated_ok:
                blocked_error = str(smoke.get("error", ""))

        classification, rationale, classification_sources = classify_annotation_contract(
            task_id=task.task_id,
            annotation_type=doc_annotation_type,
            doc_text=doc_text,
            generated_annotation_type=generated_annotation_type,
        )
        if generated_ok is False:
            classification = "blocked"
            rationale = f"Direct smoke generation failed: {blocked_error}"
            classification_sources = sorted(set([*classification_sources, "blocked_error"]))

        scene_dir = review_root / task.domain / task.scene_id
        records.append(
            InventoryRecord(
                domain=task.domain,
                scene_id=task.scene_id,
                task_id=task.task_id,
                doc_path=str(doc_path),
                source_path=str(source_path),
                annotation_type_doc=doc_annotation_type,
                annotation_type_generated=generated_annotation_type,
                answer_schema_doc=doc_answer_schema,
                scene_package_registered=task.scene_id in migrated_scenes.get(task.domain, set()),
                review_target_scene=task.scene_id in review_scenes.get(task.domain, set()),
                manual_code_audit=_status_summary(scene_dir / "manual_code_audit_status.json"),
                taxonomy_review=_status_summary(scene_dir / "taxonomy_review_status.json"),
                source_layout_test=_status_summary(scene_dir / "source_layout_test_status.json"),
                classification=classification,
                rationale=rationale,
                classification_sources=classification_sources,
                generated_ok=generated_ok,
                blocked_error=blocked_error,
            )
        )

    classification_counts = Counter(record.classification for record in records)
    domain_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        domain_counts[record.domain][record.classification] += 1

    return {
        "schema": SCHEMA_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_inventory_path": str(active_inventory_path),
        "smoke_samples": int(smoke_samples),
        "total_tasks": len(records),
        "classification_counts": dict(sorted(classification_counts.items())),
        "domain_classification_counts": {
            domain: dict(sorted(counter.items()))
            for domain, counter in sorted(domain_counts.items())
        },
        "records": [asdict(record) for record in records],
    }


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return lines


def _task_link(record: Mapping[str, Any]) -> str:
    return f"`{record.get('task_id', '')}`"


def render_markdown(inventory: Mapping[str, Any]) -> str:
    """Render a compact Markdown inventory report."""

    records = list(inventory.get("records", []))
    classification_counts = inventory.get("classification_counts", {})
    if not isinstance(classification_counts, Mapping):
        classification_counts = {}

    lines = [
        "# Scalar Annotation Stage 2 Inventory",
        "",
        f"- Schema: `{inventory.get('schema', '')}`",
        f"- Generated at: `{inventory.get('generated_at', '')}`",
        f"- Active inventory: `{inventory.get('active_inventory_path', '')}`",
        f"- Total tasks: `{inventory.get('total_tasks', 0)}`",
        f"- Smoke samples per task: `{inventory.get('smoke_samples', 0)}`",
        "",
        "## Classification Summary",
        "",
    ]
    lines.extend(
        _markdown_table(
            ["Classification", "Tasks"],
            [[key, value] for key, value in sorted(classification_counts.items())],
        )
    )

    domain_counts = inventory.get("domain_classification_counts", {})
    if isinstance(domain_counts, Mapping):
        lines.extend(["", "## Domain Summary", ""])
        domain_rows = []
        for domain, counts in sorted(domain_counts.items()):
            if isinstance(counts, Mapping):
                domain_rows.append([domain, sum(int(value) for value in counts.values()), json.dumps(dict(sorted(counts.items())), sort_keys=True)])
        lines.extend(_markdown_table(["Domain", "Tasks", "Classifications"], domain_rows))

    priority_classes = {"scalar_point_candidate", "scalar_bbox_candidate", "needs_manual_decision", "blocked"}
    for classification in sorted(priority_classes):
        rows = [
            [
                record.get("domain", ""),
                record.get("scene_id", ""),
                _task_link(record),
                record.get("annotation_type_doc", "") or record.get("annotation_type_generated", ""),
                record.get("rationale", ""),
            ]
            for record in records
            if isinstance(record, Mapping) and record.get("classification") == classification
        ]
        if rows:
            lines.extend(["", f"## {classification}", ""])
            lines.extend(_markdown_table(["Domain", "Scene", "Task", "Annotation", "Rationale"], rows))

    migrated_rows = [
        [
            record.get("domain", ""),
            record.get("scene_id", ""),
            _task_link(record),
            record.get("classification", ""),
            record.get("annotation_type_doc", ""),
        ]
        for record in records
        if isinstance(record, Mapping)
        and record.get("scene_package_registered")
        and record.get("classification") in {"scalar_point_candidate", "scalar_bbox_candidate", "needs_manual_decision", "blocked"}
    ]
    if migrated_rows:
        lines.extend(["", "## Migrated/Review-Candidate Follow-Up", ""])
        lines.extend(_markdown_table(["Domain", "Scene", "Task", "Classification", "Annotation"], migrated_rows))

    return "\n".join(lines).rstrip() + "\n"


def _parse_task_filter(raw: str) -> set[str]:
    return {item.strip() for item in str(raw).split(",") if item.strip()}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory scalar annotation migration candidates")
    parser.add_argument("--active-inventory", default=str(DEFAULT_ACTIVE_INVENTORY))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_MD))
    parser.add_argument("--review-root", default="review/task-reviews")
    parser.add_argument("--tasks", default="", help="Comma-separated task ids to smoke-generate when --smoke-samples > 0.")
    parser.add_argument("--smoke-samples", type=int, default=0, help="Set to 1 for direct task smoke generation. Default is static-only.")
    parser.add_argument("--max-attempts", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="Build and print summary without writing reports.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    inventory = build_inventory(
        active_inventory_path=Path(args.active_inventory),
        review_root=Path(args.review_root),
        smoke_tasks=_parse_task_filter(args.tasks),
        smoke_samples=max(0, int(args.smoke_samples)),
        max_attempts=max(1, int(args.max_attempts)),
    )
    rendered = render_markdown(inventory)

    if args.dry_run:
        print(rendered)
        return 0

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(rendered, encoding="utf-8")
    print(f"wrote {output_json}")
    print(f"wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
