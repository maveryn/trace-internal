"""Index active TRACE task-review sidecars for browser inspection."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping

from trace.core.scene_package_migration import is_scene_package_review_target_scene
from trace.core.taxonomy import ACTIVE_DOMAINS

from .models import DomainRecord, ReviewIndex, SampleRecord, SceneRecord, SolveStats, TaskRecord


CURRENT_CALIBRATION_BASELINE = "v0"
CURRENT_MODEL_SLUGS = {"qwen25vl7b"}
MODEL_IDS = {
    "qwen25vl7b": "Qwen/Qwen2.5-VL-7B-Instruct",
    "qwen3vl8b": "Qwen/Qwen3-VL-8B-Instruct",
    "qwen3vl4b": "Qwen/Qwen3-VL-4B-Instruct",
}
MODEL_RESPONSE_CAP_THRESHOLDS = {
    "qwen25vl7b": 0.25,
    "qwen3vl8b": 0.25,
    "qwen3vl4b": 0.25,
}
DIFFICULTY_TAIL_THRESHOLD = 0.50


def build_review_index(
    review_root: Path | str,
    *,
    repo_root: Path | str | None = None,
    enforce_migration_registry: bool = True,
) -> ReviewIndex:
    """Build an in-memory review index from ``review/task-reviews`` artifacts."""

    root = Path(review_root).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else _infer_repo_root(root)
    index = ReviewIndex(
        root=root,
        repo_root=resolved_repo_root,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    if not root.exists():
        index.errors.append(f"review root does not exist: {root}")
        return index

    for domain in ACTIVE_DOMAINS:
        domain_dir = root / domain
        if not domain_dir.is_dir():
            continue
        domain_record = DomainRecord(domain=domain)
        for scene_dir in sorted(path for path in domain_dir.iterdir() if path.is_dir()):
            scene_id = scene_dir.name
            if bool(enforce_migration_registry) and not is_scene_package_review_target_scene(domain, scene_id):
                continue
            index.domains.setdefault(domain, domain_record)
            _scan_scene(index=index, domain=domain, scene_id=scene_id, scene_dir=scene_dir)

    _attach_solve_stats(index)
    _finalize_counts(index)
    return index


def build_review_scene_index(
    review_root: Path | str,
    *,
    domain: str,
    scene_id: str,
    repo_root: Path | str | None = None,
    enforce_migration_registry: bool = True,
) -> ReviewIndex:
    """Build an index containing only one review scene, if it is currently eligible."""

    root = Path(review_root).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else _infer_repo_root(root)
    index = ReviewIndex(
        root=root,
        repo_root=resolved_repo_root,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    if not root.exists():
        index.errors.append(f"review root does not exist: {root}")
        return index

    domain_name = str(domain)
    scene_name = str(scene_id)
    if domain_name not in ACTIVE_DOMAINS:
        index.errors.append(f"unknown active domain: {domain_name}")
        return index
    if bool(enforce_migration_registry) and not is_scene_package_review_target_scene(domain_name, scene_name):
        return index

    scene_dir = root / domain_name / scene_name
    if not scene_dir.is_dir():
        return index

    index.domains.setdefault(domain_name, DomainRecord(domain=domain_name))
    _scan_scene(index=index, domain=domain_name, scene_id=scene_name, scene_dir=scene_dir)
    _attach_solve_stats(index)
    _finalize_counts(index)
    return index


def merge_review_scene_index(current: ReviewIndex, scene_index: ReviewIndex, *, domain: str, scene_id: str) -> ReviewIndex:
    """Return ``current`` with one scene replaced by ``scene_index`` content."""

    domain_name = str(domain)
    scene_name = str(scene_id)
    merged = copy.deepcopy(current)
    _remove_scene_from_index(merged, domain=domain_name, scene_id=scene_name)

    for key, scene in scene_index.scenes.items():
        merged.scenes[key] = copy.deepcopy(scene)
    for key, task in scene_index.tasks.items():
        merged.tasks[key] = copy.deepcopy(task)
    for key, sample in scene_index.samples.items():
        merged.samples[key] = copy.deepcopy(sample)
    for key, sample_uids in scene_index.samples_by_task.items():
        merged.samples_by_task[key] = list(sample_uids)
    for key, sample_uids in scene_index.samples_by_query.items():
        merged.samples_by_query[key] = list(sample_uids)
    for key, path in scene_index.media.items():
        merged.media[key] = path
    for key, domain_record in scene_index.domains.items():
        existing = merged.domains.setdefault(key, DomainRecord(domain=domain_record.domain))
        existing.scenes.extend(scene_id for scene_id in domain_record.scenes if scene_id not in existing.scenes)

    merged.built_at = scene_index.built_at
    merged.errors = [
        error
        for error in merged.errors
        if f"{domain_name}/{scene_name}" not in str(error) and f"{domain_name}/{scene_name}/" not in str(error)
    ] + list(scene_index.errors)
    _reset_counts(merged)
    _finalize_counts(merged)
    return merged


def load_sample_payload(index: ReviewIndex, sample: SampleRecord) -> Dict[str, Any]:
    """Load one sample JSON payload from the review root."""

    path = _safe_join(index.root, sample.data_rel_path)
    if path is None or not path.exists():
        raise FileNotFoundError(sample.data_rel_path)
    return _load_json(path)


def _infer_repo_root(review_root: Path) -> Path:
    parts = review_root.parts
    if len(parts) >= 2 and parts[-2:] == ("review", "task-reviews"):
        return review_root.parents[1]
    return Path.cwd().resolve()


def _scan_scene(*, index: ReviewIndex, domain: str, scene_id: str, scene_dir: Path) -> None:
    scene_key = ReviewIndex.scene_key(domain, scene_id)
    scene_manifest_path = scene_dir / "scene_review_manifest.json"
    scene_manifest = _load_json_safe(scene_manifest_path, index.errors)
    migration_test_status_path = scene_dir / "migration_test_status.json"
    migration_test_status = _load_json_safe(migration_test_status_path, index.errors)
    manual_code_audit_status_path = scene_dir / "manual_code_audit_status.json"
    manual_code_audit_status = _load_json_safe(manual_code_audit_status_path, index.errors)
    taxonomy_review_status_path = scene_dir / "taxonomy_review_status.json"
    taxonomy_review_status = _load_json_safe(taxonomy_review_status_path, index.errors)
    scene_record = SceneRecord(
        domain=domain,
        scene_id=scene_id,
        manifest_rel_path=_rel_or_empty(scene_manifest_path, index.root),
        workbook_rel_path=str(scene_manifest.get("workbook", "") if isinstance(scene_manifest, Mapping) else ""),
        model_stats_count=int(scene_manifest.get("model_stats_count", 0) if isinstance(scene_manifest, Mapping) else 0),
        migration_test_status_rel_path=(
            _rel_or_empty(migration_test_status_path, index.root) if migration_test_status_path.exists() else ""
        ),
        migration_test_pass=(
            bool(migration_test_status.get("passed"))
            if isinstance(migration_test_status, Mapping) and "passed" in migration_test_status
            else None
        ),
        migration_test_summary=_migration_test_summary(migration_test_status),
        manual_code_audit_status_rel_path=(
            _rel_or_empty(manual_code_audit_status_path, index.root) if manual_code_audit_status_path.exists() else ""
        ),
        manual_code_audit_pass=(
            bool(manual_code_audit_status.get("passed"))
            if isinstance(manual_code_audit_status, Mapping) and "passed" in manual_code_audit_status
            else None
        ),
        manual_code_audit_summary=_manual_code_audit_summary(manual_code_audit_status),
        taxonomy_review_status_rel_path=(
            _rel_or_empty(taxonomy_review_status_path, index.root) if taxonomy_review_status_path.exists() else ""
        ),
        taxonomy_review_pass=(
            bool(taxonomy_review_status.get("passed"))
            if isinstance(taxonomy_review_status, Mapping) and "passed" in taxonomy_review_status
            else None
        ),
        taxonomy_review_summary=_taxonomy_review_summary(taxonomy_review_status),
    )
    index.scenes[scene_key] = scene_record
    index.domains.setdefault(domain, DomainRecord(domain=domain)).scenes.append(scene_id)

    task_dirs = [path for path in scene_dir.iterdir() if path.is_dir() and path.name.startswith("task_")]
    for task_dir in sorted(task_dirs):
        task_record = _scan_task(index=index, domain=domain, scene_id=scene_id, task_dir=task_dir)
        if task_record is None:
            continue
        scene_record.tasks.append(task_record.task_id)
        if not scene_record.preview_uid and task_record.preview_uid:
            scene_record.preview_uid = task_record.preview_uid


def _migration_test_summary(status: Any) -> Dict[str, Any]:
    """Normalize a scene migration test-status artifact for template rendering."""

    if not isinstance(status, Mapping):
        return {}
    test_files = status.get("test_files", [])
    if isinstance(test_files, str):
        test_files = [test_files]
    elif not isinstance(test_files, Iterable):
        test_files = []
    return {
        "schema": str(status.get("schema", "")),
        "status": str(status.get("status", "")),
        "passed": bool(status.get("passed")) if "passed" in status else None,
        "summary": str(status.get("summary", "")),
        "command": str(status.get("command", "")),
        "checked_at": str(status.get("checked_at", status.get("timestamp", ""))),
        "test_files": [str(item) for item in test_files if str(item).strip()],
    }


def _manual_code_audit_summary(status: Any) -> Dict[str, Any]:
    """Normalize a pre-review manual code audit artifact for template rendering."""

    if not isinstance(status, Mapping):
        return {}
    files_reviewed = status.get("files_reviewed", [])
    if isinstance(files_reviewed, str):
        files_reviewed = [files_reviewed]
    elif not isinstance(files_reviewed, Iterable):
        files_reviewed = []
    checklist = status.get("checklist", {})
    if not isinstance(checklist, Mapping):
        checklist = {}
    return {
        "schema": str(status.get("schema", "")),
        "status": str(status.get("status", "")),
        "passed": bool(status.get("passed")) if "passed" in status else None,
        "summary": str(status.get("summary", "")),
        "checked_at": str(status.get("checked_at", status.get("timestamp", ""))),
        "checked_by": str(status.get("checked_by", status.get("auditor", ""))),
        "notes": str(status.get("notes", "")),
        "files_reviewed": [str(item) for item in files_reviewed if str(item).strip()],
        "checklist": {str(key): bool(value) for key, value in checklist.items()},
    }


def _taxonomy_review_summary(status: Any) -> Dict[str, Any]:
    """Normalize a pre-review taxonomy audit artifact for template rendering."""

    if not isinstance(status, Mapping):
        return {}
    task_ids = status.get("task_ids", [])
    if isinstance(task_ids, str):
        task_ids = [task_ids]
    elif not isinstance(task_ids, Iterable):
        task_ids = []
    checklist = status.get("checklist", {})
    if not isinstance(checklist, Mapping):
        checklist = {}
    return {
        "schema": str(status.get("schema", "")),
        "status": str(status.get("status", "")),
        "passed": bool(status.get("passed")) if "passed" in status else None,
        "summary": str(status.get("summary", "")),
        "checked_at": str(status.get("checked_at", status.get("timestamp", ""))),
        "checked_by": str(status.get("checked_by", status.get("auditor", ""))),
        "notes": str(status.get("notes", "")),
        "task_ids": [str(item) for item in task_ids if str(item).strip()],
        "checklist": {str(key): bool(value) for key, value in checklist.items()},
    }


def _scan_task(*, index: ReviewIndex, domain: str, scene_id: str, task_dir: Path) -> TaskRecord | None:
    task_id = task_dir.name
    task_key = ReviewIndex.task_key(domain, scene_id, task_id)
    manifest_path = task_dir / "manifest.json"
    manifest = _load_json_safe(manifest_path, index.errors)
    distribution_path = task_dir / "distribution_review.json"
    distribution = _load_json_safe(distribution_path, index.errors)
    random_path = task_dir / "random_review_100.json"

    workbook_rel = ""
    if isinstance(manifest, Mapping):
        workbook_rel = str(manifest.get("workbook", ""))
    if not workbook_rel and (task_dir / f"{task_id}.xlsx").exists():
        workbook_rel = _rel_or_empty(task_dir / f"{task_id}.xlsx", index.root)

    query_counts: Dict[str, int] = {}
    workbook_sheets: Dict[str, str] = {}
    if isinstance(manifest, Mapping):
        query_counts.update({str(key): int(value) for key, value in dict(manifest.get("query_ids", {})).items()})
        workbook_sheets.update({str(key): str(value) for key, value in dict(manifest.get("workbook_sheets", {})).items()})

    task_record = TaskRecord(
        domain=domain,
        scene_id=scene_id,
        task_id=task_id,
        manifest_rel_path=_rel_or_empty(manifest_path, index.root),
        workbook_rel_path=workbook_rel,
        distribution_rel_path=_rel_or_empty(distribution_path, index.root) if distribution_path.exists() else "",
        random_review_rel_path=_rel_or_empty(random_path, index.root) if random_path.exists() else "",
        query_counts=query_counts,
        workbook_sheets=workbook_sheets,
        distribution_mode=str(distribution.get("mode", "") if isinstance(distribution, Mapping) else ""),
        distribution_pass=bool(distribution.get("pass")) if isinstance(distribution, Mapping) and "pass" in distribution else None,
        distribution_summary=_distribution_summary(distribution),
    )
    index.tasks[task_key] = task_record

    samples = _scan_task_samples(index=index, domain=domain, scene_id=scene_id, task_id=task_id, task_dir=task_dir)
    index.samples_by_task[task_key] = samples
    task_record.sample_count = len(samples)
    if samples:
        task_record.preview_uid = samples[0]
    actual_counts: Dict[str, int] = {}
    for uid in samples:
        sample = index.samples[uid]
        actual_counts[sample.query_id] = int(actual_counts.get(sample.query_id, 0) + 1)
    if actual_counts:
        task_record.query_counts = dict(sorted(actual_counts.items()))
    task_record.taxonomy_summary = _task_taxonomy_summary(index=index, task=task_record, sample_uids=samples)
    return task_record


def _task_taxonomy_summary(*, index: ReviewIndex, task: TaskRecord, sample_uids: list[str]) -> Dict[str, Any]:
    """Return condensed task taxonomy and schema metadata for the review UI."""

    doc_path = index.repo_root / "docs" / "tasks" / task.domain / task.scene_id / f"{task.task_id}.md"
    doc_summary = _parse_task_doc_taxonomy(doc_path)
    answer_schemas = sorted(
        {
            str(index.samples[uid].answer_type)
            for uid in sample_uids
            if uid in index.samples and str(index.samples[uid].answer_type).strip()
        }
    )
    annotation_schemas = sorted(
        {
            str(index.samples[uid].annotation_type)
            for uid in sample_uids
            if uid in index.samples and str(index.samples[uid].annotation_type).strip()
        }
    )
    query_ids = list(doc_summary.get("query_ids", [])) or sorted(task.query_counts)
    return {
        "domain": str(doc_summary.get("domain") or task.domain),
        "scene_id": str(doc_summary.get("scene_id") or task.scene_id),
        "task_id": task.task_id,
        "query_ids": query_ids,
        "answer_schema": str(doc_summary.get("answer_schema") or ", ".join(answer_schemas)),
        "annotation_schema": str(doc_summary.get("annotation_schema") or ", ".join(annotation_schemas)),
        "program_contract": str(doc_summary.get("program_contract", "")),
        "doc_rel_path": _rel_or_empty(doc_path, index.repo_root) if doc_path.exists() else "",
    }


def _parse_task_doc_taxonomy(doc_path: Path) -> Dict[str, Any]:
    if not doc_path.exists():
        return {}
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    summary: Dict[str, Any] = {}
    contract_body = _markdown_section(text, "Contract")
    for raw_line in contract_body.splitlines():
        line = raw_line.strip()
        match = re.match(r"(?:[-*]|\d+\.)\s*([^:]+):\s*(.+)$", line)
        if not match:
            continue
        key = match.group(1).strip().lower().replace(" ", "_")
        value = _clean_markdown_value(match.group(2))
        if key == "domain":
            summary["domain"] = value
        elif key == "scene_id":
            summary["scene_id"] = value
        elif key in {"query_id", "query_ids"}:
            summary["query_ids"] = _split_markdown_values(value)
        elif key == "answer_schema":
            summary["answer_schema"] = value
        elif key == "annotation_schema":
            summary["annotation_schema"] = value

    program_body = _markdown_section(text, "Program Contract")
    program_contract = _extract_program_contract(program_body)
    if program_contract:
        summary["program_contract"] = program_contract
    return summary


def _extract_program_contract(program_body: str) -> str:
    """Extract the concrete program schema from a task-doc Program Contract section."""

    fallback = ""
    for raw_line in program_body.splitlines():
        line = _clean_markdown_value(re.sub(r"^[-*]\s*", "", raw_line.strip()))
        if not line:
            continue
        match = re.match(r"Program schema:\s*(.+)$", line, flags=re.IGNORECASE)
        if match:
            return _clean_markdown_value(match.group(1))
        if not fallback:
            fallback = line
    return fallback


def _markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return str(match.group("body")) if match else ""


def _clean_markdown_value(value: str) -> str:
    cleaned = str(value).strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and cleaned.count("`") == 2:
        cleaned = cleaned[1:-1]
    return cleaned.replace("`", "").strip()


def _split_markdown_values(value: str) -> list[str]:
    text = _clean_markdown_value(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"\s*,\s*|\s*\|\s*", text) if part.strip()]


def _scan_task_samples(
    *,
    index: ReviewIndex,
    domain: str,
    scene_id: str,
    task_id: str,
    task_dir: Path,
) -> list[str]:
    data_root = task_dir / "data"
    if not data_root.exists():
        return []
    sample_uids: list[str] = []
    for data_path in sorted(data_root.rglob("*.json")):
        try:
            payload = _load_json(data_path)
            sample = _sample_from_payload(
                index=index,
                domain=domain,
                scene_id=scene_id,
                task_id=task_id,
                data_path=data_path,
                payload=payload,
            )
        except Exception as exc:
            index.errors.append(f"failed to load sample {data_path}: {exc}")
            continue
        index.samples[sample.uid] = sample
        sample_uids.append(sample.uid)
        query_key = ReviewIndex.query_key(domain, scene_id, task_id, sample.query_id)
        index.samples_by_query.setdefault(query_key, []).append(sample.uid)
        if sample.media_id:
            media_path = _safe_join(index.root, sample.image_rel_path)
            if media_path is not None:
                index.media[sample.media_id] = media_path
    return sorted(
        sample_uids,
        key=lambda uid: (
            index.samples[uid].query_id,
            index.samples[uid].instance_seed,
            index.samples[uid].data_rel_path,
        ),
    )


def _sample_from_payload(
    *,
    index: ReviewIndex,
    domain: str,
    scene_id: str,
    task_id: str,
    data_path: Path,
    payload: Mapping[str, Any],
) -> SampleRecord:
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

    data_rel_path = _rel_or_empty(data_path, index.root)
    query_id = str(payload.get("query_id", "") or data_path.parent.name or "default")
    if not query_id:
        query_id = "default"
    image_rel_path = str(image_payload.get("path", ""))
    if not image_rel_path:
        image_rel_path = _derive_image_rel_path(data_rel_path)
    image_path = _safe_join(index.root, image_rel_path)
    image_exists = bool(image_path is not None and image_path.exists())
    image_mtime_ns = int(image_path.stat().st_mtime_ns) if image_exists and image_path is not None else 0
    media_id = _hash_text(f"media:{image_rel_path}") if image_rel_path else ""
    instance_seed = int(payload.get("instance_seed", 0) or 0)
    prompt = str(payload.get("prompt", ""))
    prompt_answer_only = str(prompt_variants.get("answer_only", prompt))
    prompt_answer_and_annotation = str(prompt_variants.get("answer_and_annotation", prompt))

    identity_payload = {
        "domain": domain,
        "scene_id": scene_id,
        "task_id": task_id,
        "query_id": query_id,
        "data_rel_path": data_rel_path,
        "image_rel_path": image_rel_path,
        "instance_seed": instance_seed,
        "prompt": prompt,
        "answer_gt": answer_gt,
        "annotation_gt": annotation_gt,
    }
    content_hash = _stable_hash(identity_payload)
    return SampleRecord(
        uid=content_hash[:24],
        content_hash=content_hash,
        domain=domain,
        scene_id=scene_id,
        task_id=task_id,
        query_id=query_id,
        instance_seed=instance_seed,
        data_rel_path=data_rel_path,
        image_rel_path=image_rel_path,
        media_id=media_id,
        image_exists=image_exists,
        image_mtime_ns=image_mtime_ns,
        prompt=prompt,
        prompt_answer_only=prompt_answer_only,
        prompt_answer_and_annotation=prompt_answer_and_annotation,
        answer_type=str(answer_gt.get("type", "")),
        answer_value=answer_gt.get("value"),
        annotation_type=str(annotation_gt.get("type", "")),
        annotation_value=annotation_gt.get("value"),
    )


def _derive_image_rel_path(data_rel_path: str) -> str:
    path = Path(data_rel_path)
    parts = list(path.parts)
    try:
        data_index = parts.index("data")
    except ValueError:
        return ""
    parts[data_index] = "images"
    if parts[-1].endswith(".json"):
        parts[-1] = f"{Path(parts[-1]).stem}.png"
    return Path(*parts).as_posix()


def _attach_solve_stats(index: ReviewIndex) -> None:
    status_records = _load_calibration_status_records(index)
    fallback_stats = _latest_stats_files_by_task_model(index)
    for task_key, task in index.tasks.items():
        rows: Dict[tuple[str, str], SolveStats] = {}
        status_record = status_records.get(task.task_id, {})
        combined_status = ""
        if isinstance(status_record, Mapping) and status_record.get("domain") == task.domain and status_record.get("scene_id") == task.scene_id:
            combined_status = str(status_record.get("status", ""))
            models = status_record.get("models", {})
            if isinstance(models, Mapping):
                for model_slug, model_record in sorted(models.items()):
                    if str(model_slug) not in CURRENT_MODEL_SLUGS or not isinstance(model_record, Mapping):
                        continue
                    row = _solve_stats_from_model_record(
                        task_id=task.task_id,
                        model_slug=str(model_slug),
                        combined_status=combined_status,
                        model_record=model_record,
                    )
                    if row is not None:
                        rows[(task.task_id, str(model_slug))] = row

        for (task_id, model_slug), stats_path in fallback_stats.items():
            if task_id != task.task_id:
                continue
            row = _solve_stats_from_stats_file(
                stats_path=stats_path,
                model_slug=model_slug,
                combined_status=combined_status,
            )
            if row is not None:
                rows[(task_id, model_slug)] = row
        task.solve_stats = [rows[key] for key in sorted(rows)]


def _load_calibration_status_records(index: ReviewIndex) -> Mapping[str, Any]:
    candidates = [
        index.root.parent / "calibration_sweep_status.json",
        index.repo_root / "review" / "calibration_sweep_status.json",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = _load_json(candidate)
        except Exception:
            continue
        config = payload.get("config", {}) if isinstance(payload, Mapping) else {}
        if isinstance(config, Mapping) and str(config.get("calibration_baseline", "")) != CURRENT_CALIBRATION_BASELINE:
            continue
        tasks = payload.get("tasks", {}) if isinstance(payload, Mapping) else {}
        if isinstance(tasks, Mapping):
            return tasks
    return {}


def _latest_stats_files_by_task_model(index: ReviewIndex) -> Dict[tuple[str, str], Path]:
    probe_root = index.repo_root / "rlvr" / "outputs" / "calibration" / "current"
    if not probe_root.exists():
        return {}
    task_ids = {task.task_id for task in index.tasks.values()}
    selected: Dict[tuple[str, str], Path] = {}
    priorities: Dict[tuple[str, str], tuple[bool, int, float]] = {}
    for stats_path in probe_root.glob("*/*/*/task_*/100x*_seed*/calibration_stats.json"):
        rel = stats_path.relative_to(probe_root)
        model_slug = str(rel.parts[0])
        task_id = str(rel.parts[3])
        if model_slug not in CURRENT_MODEL_SLUGS or task_id not in task_ids:
            continue
        rollout_match = re.match(r"100x(?P<rollouts>\d+)_seed", str(rel.parts[4]))
        if rollout_match is None:
            continue
        key = (task_id, model_slug)
        priority = (int(rollout_match.group("rollouts")) == 24, int(rollout_match.group("rollouts")), stats_path.stat().st_mtime)
        if key not in selected or priority >= priorities.get(key, (False, -1, 0.0)):
            selected[key] = stats_path
            priorities[key] = priority
    return selected


def _solve_stats_from_model_record(
    *,
    task_id: str,
    model_slug: str,
    combined_status: str,
    model_record: Mapping[str, Any],
) -> SolveStats | None:
    stats = model_record.get("stats", {})
    if not isinstance(stats, Mapping):
        return None
    overall = stats.get("overall", {})
    if not isinstance(overall, Mapping):
        overall = {}
    prompt_stats = stats.get("prompt_token_stats", {})
    if not isinstance(prompt_stats, Mapping):
        prompt_stats = {}
    response_stats = stats.get("response_token_stats", {})
    if not isinstance(response_stats, Mapping):
        response_stats = {}
    reasons = model_record.get("reasons", [])
    if isinstance(reasons, str):
        reason_text = reasons
    elif isinstance(reasons, Iterable):
        reason_text = ", ".join(str(item) for item in reasons)
    else:
        reason_text = ""
    return SolveStats(
        model=model_slug,
        model_id=str(model_record.get("model_id", MODEL_IDS.get(model_slug, model_slug))),
        status=str(model_record.get("status", "")),
        combined_status=str(combined_status or model_record.get("status", "")),
        reasons=reason_text,
        mean_solve_rate=_maybe_float(overall.get("mean_solve_rate")),
        hard_frac=_maybe_float(overall.get("hard_frac")),
        easy_frac=_maybe_float(overall.get("easy_frac")),
        band_frac=_maybe_float(overall.get("band_frac")),
        response_cap_rate=_maybe_float(response_stats.get("cap_rate")),
        prompt_count=_maybe_int(overall.get("prompt_count")),
        rollout_count=_maybe_int(overall.get("rollout_count")),
        solve_workbook=str(model_record.get("solve_workbook", "")),
        calibration_stats=str(model_record.get("calibration_stats", "")),
        output_dir=str(model_record.get("output_dir", "")),
    )


def _solve_stats_from_stats_file(*, stats_path: Path, model_slug: str, combined_status: str) -> SolveStats | None:
    try:
        stats = _load_json(stats_path)
    except Exception:
        return None
    config = stats.get("config", {}) if isinstance(stats, Mapping) else {}
    if isinstance(config, Mapping) and str(config.get("calibration_baseline", "")) != CURRENT_CALIBRATION_BASELINE:
        return None
    artifacts = stats.get("artifacts", {}) if isinstance(stats.get("artifacts", {}), Mapping) else {}
    status, reasons = _status_reasons_from_stats(stats, model_slug=model_slug)
    record = {
        "model_id": MODEL_IDS.get(model_slug, model_slug),
        "status": status,
        "reasons": reasons,
        "stats": stats,
        "solve_workbook": artifacts.get("solve_workbook", ""),
        "calibration_stats": artifacts.get("calibration_stats", str(stats_path)),
        "output_dir": config.get("probe_output_dir", str(stats_path.parent)) if isinstance(config, Mapping) else str(stats_path.parent),
    }
    return _solve_stats_from_model_record(
        task_id="",
        model_slug=model_slug,
        combined_status=combined_status or status,
        model_record=record,
    )


def _status_reasons_from_stats(stats: Mapping[str, Any], *, model_slug: str) -> tuple[str, list[str]]:
    overall = stats.get("overall", {}) if isinstance(stats.get("overall", {}), Mapping) else {}
    prompt_stats = stats.get("prompt_token_stats", {}) if isinstance(stats.get("prompt_token_stats", {}), Mapping) else {}
    response_stats = stats.get("response_token_stats", {}) if isinstance(stats.get("response_token_stats", {}), Mapping) else {}

    blocked: list[str] = []
    if int(prompt_stats.get("over_limit_count") or 0) > 0:
        blocked.append("prompt_over_limit")
    if float(response_stats.get("cap_rate") or 0.0) > MODEL_RESPONSE_CAP_THRESHOLDS.get(model_slug, 0.25):
        blocked.append("response_cap_rate")
    if not overall:
        blocked.append("missing_overall_stats")
    if blocked:
        return "blocked", blocked

    tuning: list[str] = []
    if float(overall.get("hard_frac") or 0.0) >= DIFFICULTY_TAIL_THRESHOLD:
        tuning.append("hard_frac")
    if float(overall.get("easy_frac") or 0.0) >= DIFFICULTY_TAIL_THRESHOLD:
        tuning.append("easy_frac")
    mean = float(overall.get("mean_solve_rate") or 0.0)
    if mean < 0.10 or mean > 0.75:
        tuning.append("mean_solve_rate")
    if tuning:
        return "needs_manual_tuning", tuning
    return "accepted", []


def _finalize_counts(index: ReviewIndex) -> None:
    for task_key, task in index.tasks.items():
        scene_key = ReviewIndex.scene_key(task.domain, task.scene_id)
        scene = index.scenes.get(scene_key)
        if scene is not None:
            scene.sample_count += task.sample_count
    for scene_key, scene in index.scenes.items():
        scene.tasks = sorted(dict.fromkeys(scene.tasks))
        scene.task_count = len(scene.tasks)
    for domain, domain_record in index.domains.items():
        domain_record.scenes = sorted(dict.fromkeys(domain_record.scenes))
        domain_record.task_count = sum(index.scenes[ReviewIndex.scene_key(domain, scene_id)].task_count for scene_id in domain_record.scenes)
        domain_record.sample_count = sum(index.scenes[ReviewIndex.scene_key(domain, scene_id)].sample_count for scene_id in domain_record.scenes)
        for scene_id in domain_record.scenes:
            preview_uid = index.scenes[ReviewIndex.scene_key(domain, scene_id)].preview_uid
            if preview_uid:
                domain_record.preview_uid = preview_uid
                break


def _remove_scene_from_index(index: ReviewIndex, *, domain: str, scene_id: str) -> None:
    """Remove one scene and its dependent task/sample records from an index."""

    scene_key = ReviewIndex.scene_key(str(domain), str(scene_id))
    scene = index.scenes.pop(scene_key, None)
    task_ids = list(scene.tasks) if scene is not None else [
        task.task_id for task in index.tasks.values() if task.domain == str(domain) and task.scene_id == str(scene_id)
    ]
    removed_sample_uids: set[str] = set()
    removed_media_ids: set[str] = set()
    for task_id in task_ids:
        task_key = ReviewIndex.task_key(str(domain), str(scene_id), str(task_id))
        index.tasks.pop(task_key, None)
        for sample_uid in index.samples_by_task.pop(task_key, []):
            removed_sample_uids.add(str(sample_uid))
    for sample_uid in list(removed_sample_uids):
        sample = index.samples.pop(sample_uid, None)
        if sample is not None and sample.media_id:
            removed_media_ids.add(str(sample.media_id))
    for query_key, sample_uids in list(index.samples_by_query.items()):
        filtered = [uid for uid in sample_uids if uid not in removed_sample_uids]
        if filtered:
            index.samples_by_query[query_key] = filtered
        else:
            index.samples_by_query.pop(query_key, None)
    for media_id in removed_media_ids:
        index.media.pop(media_id, None)
    domain_record = index.domains.get(str(domain))
    if domain_record is not None:
        domain_record.scenes = [name for name in domain_record.scenes if name != str(scene_id)]
        if not domain_record.scenes:
            index.domains.pop(str(domain), None)


def _reset_counts(index: ReviewIndex) -> None:
    """Clear derived counts before recomputing them."""

    for scene in index.scenes.values():
        scene.tasks = sorted(dict.fromkeys(scene.tasks))
        scene.task_count = 0
        scene.sample_count = 0
    for domain_record in index.domains.values():
        domain_record.scenes = sorted(dict.fromkeys(domain_record.scenes))
        domain_record.task_count = 0
        domain_record.sample_count = 0
        domain_record.preview_uid = ""


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON at {path}")
    return payload


def _load_json_safe(path: Path, errors: list[str]) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _load_json(path)
    except Exception as exc:
        errors.append(f"failed to load {path}: {exc}")
        return {}


def _distribution_summary(distribution: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(distribution, Mapping) or not distribution:
        return {}
    overall = distribution.get("overall", {})
    if not isinstance(overall, Mapping):
        overall = {}
    collection = distribution.get("collection", {})
    if not isinstance(collection, Mapping):
        collection = {}
    per_query = distribution.get("per_query_id", {})
    if not isinstance(per_query, Mapping):
        per_query = {}

    return {
        "pass": bool(distribution.get("pass")) if "pass" in distribution else None,
        "mode": str(distribution.get("mode", "")),
        "has_query_ids": bool(distribution.get("has_query_ids", False)),
        "failed_query_ids": list(distribution.get("failed_query_ids", []) or []),
        "incomplete_query_ids": list(distribution.get("incomplete_query_ids", []) or []),
        "warnings": list(distribution.get("warnings", []) or []),
        "sample_count": _maybe_int(overall.get("sample_count")),
        "unique_answers": _maybe_int(overall.get("unique_answers")),
        "max_answer_frequency": _maybe_float(overall.get("max_answer_frequency")),
        "top_answers": list(overall.get("top_answers", []) or [])[:5],
        "checks": _gated_distribution_checks(overall.get("checks", {})),
        "collection": {
            "target_count_per_query_id": _maybe_int(collection.get("target_count_per_query_id")),
            "total_generated": _maybe_int(collection.get("total_generated")),
            "collected_query_id_counts": dict(collection.get("collected_query_id_counts", {}) or {}),
            "generated_query_id_counts": dict(collection.get("generated_query_id_counts", {}) or {}),
        },
        "per_query_id": {
            str(query_id): {
                "pass": bool(report.get("pass")) if isinstance(report, Mapping) and "pass" in report else None,
                "sample_count": _maybe_int(report.get("sample_count")) if isinstance(report, Mapping) else None,
                "unique_answers": _maybe_int(report.get("unique_answers")) if isinstance(report, Mapping) else None,
                "max_answer_frequency": _maybe_float(report.get("max_answer_frequency")) if isinstance(report, Mapping) else None,
                "top_answers": list(report.get("top_answers", []) or [])[:5] if isinstance(report, Mapping) else [],
            }
            for query_id, report in sorted(per_query.items())
        },
    }


def _gated_distribution_checks(checks: Any) -> Dict[str, Any]:
    """Return only pass/fail distribution checks shown in the review UI."""

    if not isinstance(checks, Mapping):
        return {}
    gated: Dict[str, Any] = {}
    for name, check in sorted(checks.items()):
        if not isinstance(check, Mapping):
            continue
        if check.get("pass") is None:
            continue
        gated[str(name)] = dict(check)
    return gated


def _rel_or_empty(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return ""


def _safe_join(root: Path, rel_path: str) -> Path | None:
    if not rel_path:
        return None
    candidate = (root / rel_path).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def _stable_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _maybe_float(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except Exception:
        return None


def _maybe_int(value: Any) -> int | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return int(value)
    except Exception:
        return None
