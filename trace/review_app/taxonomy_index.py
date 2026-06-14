"""Index generated taxonomy review artifacts for browser review."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

from trace.core.taxonomy_semantics import classify_objective

from .models import ReviewIndex


DEFAULT_TAXONOMY_ROUND = "contract_v0_reanalysis"


@dataclass(frozen=True)
class TaxonomyQueryRecord:
    """One current query row mapped to its proposed task boundary."""

    round_id: str
    domain: str
    scene_id: str
    current_task_id: str
    current_objective: str
    query_id: str
    proposed_objective: str
    proposed_task_id: str
    rationale: str
    answer_types: str
    annotation_types: str
    semantic_root: str
    semantic_family: str
    semantic_leaf: str
    semantic_path: str
    current_task_slug: str = ""
    proposed_task_slug: str = ""
    scene_contract: str = ""
    view_contract: str = ""
    answer_schema: str = ""
    answer_type_observed: str = ""
    annotation_schema: str = ""
    annotation_type_observed: str = ""
    annotation_schema_notes: str = ""
    program_signature_id: str = ""
    program_schema: str = ""
    base_program_contract: str = ""
    parameter_axes: str = ""
    program_arguments: dict[str, Any] = field(default_factory=dict)
    decision_source: str = ""
    split_from: str = ""
    merge_with: str = ""
    generation_failures: str = ""
    sample_uid: str = ""
    sample_uids: tuple[str, ...] = ()


@dataclass
class TaxonomyTaskRecord:
    """One current public task and the proposed task units underneath it."""

    round_id: str
    domain: str
    scene_id: str
    current_task_id: str
    current_objective: str = ""
    current_query_count: int = 0
    decision: str = ""
    proposed_task_count: int = 0
    proposed_task_ids: list[str] = field(default_factory=list)
    program_signature_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    generation_failures: str = ""
    indexed: bool = False
    queries: list[TaxonomyQueryRecord] = field(default_factory=list)

    @property
    def task_key(self) -> str:
        return ReviewIndex.task_key(self.domain, self.scene_id, self.current_task_id)

    @property
    def sample_uids(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for query in self.queries:
            for uid in query.sample_uids or ((query.sample_uid,) if query.sample_uid else ()):
                if uid and uid not in seen:
                    seen.add(uid)
                    ordered.append(uid)
        return ordered

    @property
    def semantic_paths(self) -> list[str]:
        return sorted({query.semantic_path for query in self.queries if query.semantic_path})


@dataclass
class TaxonomyProposedUnitRecord:
    """One proposed task unit under the contract-v0 program taxonomy."""

    domain: str
    scene_id: str
    proposed_task_id: str
    proposed_objective: str
    semantic_root: str
    semantic_family: str
    semantic_leaf: str
    semantic_path: str
    program_signature_id: str = ""
    program_schema: str = ""
    base_program_contract: str = ""
    program_argument_axes: dict[str, Any] = field(default_factory=dict)
    query_count: int = 0
    source_task_ids: list[str] = field(default_factory=list)
    query_ids: list[str] = field(default_factory=list)
    answer_types: list[str] = field(default_factory=list)
    annotation_types: list[str] = field(default_factory=list)
    sample_uids: list[str] = field(default_factory=list)


@dataclass
class TaxonomyAuditIndex:
    """Browser-facing index for one taxonomy audit round."""

    root: Path
    round_id: str
    round_dir: Path
    summary: dict[str, Any] = field(default_factory=dict)
    domain_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[str, TaxonomyTaskRecord] = field(default_factory=dict)
    tasks_by_domain: dict[str, list[str]] = field(default_factory=dict)
    proposed_units: dict[str, TaxonomyProposedUnitRecord] = field(default_factory=dict)
    proposed_units_by_domain: dict[str, list[str]] = field(default_factory=dict)
    domain_docs: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return self.round_dir.exists()

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def query_count(self) -> int:
        return sum(len(task.queries) for task in self.tasks.values())

    @property
    def split_task_count(self) -> int:
        return sum(1 for task in self.tasks.values() if task.decision == "split")

    def domain_tasks(self, domain: str = "") -> list[TaxonomyTaskRecord]:
        if domain:
            return [self.tasks[key] for key in self.tasks_by_domain.get(domain, [])]
        return [self.tasks[key] for key in sorted(self.tasks)]

    def domain_units(self, domain: str = "") -> list[TaxonomyProposedUnitRecord]:
        if domain:
            return [self.proposed_units[key] for key in self.proposed_units_by_domain.get(domain, [])]
        return [self.proposed_units[key] for key in sorted(self.proposed_units)]


def build_taxonomy_audit_index(
    *,
    repo_root: Path | str,
    review_index: ReviewIndex,
    round_id: str = DEFAULT_TAXONOMY_ROUND,
) -> TaxonomyAuditIndex:
    """Build an index from generated taxonomy review artifacts and attach samples."""

    resolved_round = _normalize_round_id(round_id)
    repo_root = Path(repo_root).resolve()
    root = repo_root / "review" / "task-reviews" / "taxonomy"
    round_dir = root / resolved_round
    audit = TaxonomyAuditIndex(root=root, round_id=resolved_round, round_dir=round_dir)

    if not round_dir.exists():
        audit.errors.append(f"taxonomy audit round does not exist: {round_dir}")
        return audit

    summary = _load_json_safe(round_dir / "summary.json", audit.errors)
    if isinstance(summary, Mapping):
        audit.summary = _normalize_summary(summary)
        domains = summary.get("domains", {})
        if isinstance(domains, Mapping):
            audit.domain_summaries = {
                str(domain): _normalize_domain_summary(value)
                for domain, value in domains.items()
            }

    task_rows = _read_first_csv(
        round_dir,
        audit.errors,
        "proposed_task_summary.csv",
    )
    query_rows = _read_first_csv(
        round_dir,
        audit.errors,
        "task_query_analysis.csv",
    )

    for row in task_rows:
        task = _task_from_row(row, round_id=resolved_round, review_index=review_index)
        audit.tasks[task.task_key] = task
        audit.tasks_by_domain.setdefault(task.domain, []).append(task.task_key)

    for row in query_rows:
        query = _query_from_row(row, round_id=resolved_round, review_index=review_index)
        task_key = ReviewIndex.task_key(query.domain, query.scene_id, query.current_task_id)
        task = audit.tasks.get(task_key)
        if task is None:
            task = TaxonomyTaskRecord(
                round_id=resolved_round,
                domain=query.domain,
                scene_id=query.scene_id,
                current_task_id=query.current_task_id,
                current_objective=query.current_objective,
                indexed=task_key in review_index.tasks,
            )
            audit.tasks[task_key] = task
            audit.tasks_by_domain.setdefault(query.domain, []).append(task_key)
        task.queries.append(query)
        if not task.current_objective:
            task.current_objective = query.current_objective

    for task in audit.tasks.values():
        task.queries.sort(key=lambda query: (query.proposed_task_id, query.query_id))
        if not task.current_query_count:
            task.current_query_count = len(task.queries)
        if not task.proposed_task_count:
            task.proposed_task_count = len({query.proposed_task_id for query in task.queries})
        if not task.proposed_task_ids:
            task.proposed_task_ids = sorted({query.proposed_task_id for query in task.queries})
        if not task.decision:
            task.decision = "split" if task.proposed_task_count > 1 else "keep"

    _build_proposed_units(audit)

    for domain, keys in list(audit.tasks_by_domain.items()):
        audit.tasks_by_domain[domain] = sorted(keys)
    for domain, keys in list(audit.proposed_units_by_domain.items()):
        audit.proposed_units_by_domain[domain] = sorted(
            keys,
            key=lambda key: (
                audit.proposed_units[key].semantic_root,
                audit.proposed_units[key].semantic_family,
                audit.proposed_units[key].scene_id,
                audit.proposed_units[key].proposed_task_id,
            ),
        )

    domain_doc_dir = round_dir / "domain_taxonomies"
    if domain_doc_dir.exists():
        for path in sorted(domain_doc_dir.glob("*.md")):
            audit.domain_docs[path.stem] = path.read_text(encoding="utf-8")

    return audit


def _normalize_round_id(round_id: str) -> str:
    text = str(round_id or DEFAULT_TAXONOMY_ROUND).strip().lower()
    aliases = {
        "current": DEFAULT_TAXONOMY_ROUND,
        "v0": DEFAULT_TAXONOMY_ROUND,
        "contract-v0": DEFAULT_TAXONOMY_ROUND,
        "contract_v0": DEFAULT_TAXONOMY_ROUND,
        "contract-v0-reanalysis": DEFAULT_TAXONOMY_ROUND,
    }
    return aliases.get(text, text)


def _normalize_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(summary)
    if "live_task_count" in normalized:
        normalized.setdefault("current_tasks", normalized.get("live_task_count"))
    if "proposed_task_count" in normalized:
        normalized.setdefault("proposed_tasks", normalized.get("proposed_task_count"))
    if "split_task_count" in normalized:
        normalized.setdefault("split_tasks", normalized.get("split_task_count"))
    if "query_row_count" in normalized:
        normalized.setdefault("query_rows", normalized.get("query_row_count"))
    if "base_program_contract_count" in normalized:
        normalized.setdefault("base_program_contracts", normalized.get("base_program_contract_count"))
    if "program_argument_row_count" in normalized:
        normalized.setdefault("program_argument_rows", normalized.get("program_argument_row_count"))
    return normalized


def _normalize_domain_summary(value: Any) -> dict[str, Any]:
    normalized = dict(value) if isinstance(value, Mapping) else {}
    if "current_tasks" in normalized:
        normalized.setdefault("current", normalized.get("current_tasks"))
    if "proposed_tasks" in normalized:
        normalized.setdefault("proposed", normalized.get("proposed_tasks"))
    if "split_tasks" in normalized:
        normalized.setdefault("split", normalized.get("split_tasks"))
    return normalized


def _task_from_row(row: Mapping[str, str], *, round_id: str, review_index: ReviewIndex) -> TaxonomyTaskRecord:
    domain = str(row.get("domain", ""))
    scene_id = str(row.get("scene_id", ""))
    current_task_id = str(row.get("current_task_id", ""))
    proposed_task_ids = _split_pipe(row.get("proposed_task_ids", ""))
    query_ids = _split_pipe(row.get("query_ids", ""))
    program_signature_ids = _split_pipe(row.get("program_signature_ids", ""))
    task_key = ReviewIndex.task_key(domain, scene_id, current_task_id)
    return TaxonomyTaskRecord(
        round_id=round_id,
        domain=domain,
        scene_id=scene_id,
        current_task_id=current_task_id,
        current_objective=_task_slug(current_task_id),
        current_query_count=_int_or_zero(row.get("current_query_count")) or len(query_ids),
        decision=str(row.get("decision", "")),
        proposed_task_count=_int_or_zero(row.get("proposed_task_count")),
        proposed_task_ids=proposed_task_ids,
        program_signature_ids=program_signature_ids,
        rationale=str(row.get("rationale", "")),
        generation_failures=str(row.get("generation_failures", "")),
        indexed=task_key in review_index.tasks,
    )


def _query_from_row(row: Mapping[str, str], *, round_id: str, review_index: ReviewIndex) -> TaxonomyQueryRecord:
    domain = str(row.get("domain", ""))
    scene_id = str(row.get("scene_id", ""))
    current_task_id = str(row.get("current_task_id", ""))
    query_id = str(row.get("current_query_id", "")) or str(row.get("query_id", "")) or "default"
    current_task_slug = str(row.get("current_task_slug", "")) or _task_slug(current_task_id)
    proposed_task_id = str(row.get("proposed_task_id", ""))
    proposed_task_slug = str(row.get("proposed_task_slug", "")) or _task_slug(proposed_task_id)
    answer_schema = str(row.get("answer_schema", "")) or str(row.get("answer_types", ""))
    annotation_schema = str(row.get("annotation_schema", "")) or str(row.get("annotation_types", ""))
    program_signature_id = str(row.get("program_signature_id", ""))
    program_schema = str(row.get("program_schema", ""))
    base_program = str(row.get("base_program_contract", "")) or _base_program_contract(program_schema)
    program_arguments = _parse_json_object(row.get("program_arguments_json", ""))
    sample_uids = tuple(
        _example_sample_uids(
            review_index=review_index,
            domain=domain,
            scene_id=scene_id,
            task_id=current_task_id,
            query_id=query_id,
            limit=5,
        )
    )
    semantic_root, semantic_family, semantic_leaf, semantic_path = _semantic_parts(
        program_signature_id=program_signature_id,
        program_schema=program_schema,
        proposed_objective=proposed_task_slug or str(row.get("proposed_objective", "")),
        answer_schema=answer_schema,
        annotation_schema=annotation_schema,
        domain=domain,
        scene_id=scene_id,
    )
    return TaxonomyQueryRecord(
        round_id=round_id,
        domain=domain,
        scene_id=scene_id,
        current_task_id=current_task_id,
        current_objective=str(row.get("current_objective", "")) or current_task_slug,
        query_id=query_id,
        proposed_objective=str(row.get("proposed_objective", "")) or proposed_task_slug,
        proposed_task_id=proposed_task_id,
        rationale=str(row.get("rationale", "")),
        answer_types=answer_schema,
        annotation_types=annotation_schema,
        semantic_root=semantic_root,
        semantic_family=semantic_family,
        semantic_leaf=semantic_leaf,
        semantic_path=semantic_path,
        current_task_slug=current_task_slug,
        proposed_task_slug=proposed_task_slug,
        scene_contract=str(row.get("scene_contract", "")),
        view_contract=str(row.get("view_contract", "")),
        answer_schema=answer_schema,
        answer_type_observed=str(row.get("answer_type_observed", "")),
        annotation_schema=annotation_schema,
        annotation_type_observed=str(row.get("annotation_type_observed", "")),
        annotation_schema_notes=str(row.get("annotation_schema_notes", "")),
        program_signature_id=program_signature_id,
        program_schema=program_schema,
        base_program_contract=base_program,
        parameter_axes=str(row.get("parameter_axes", "")),
        program_arguments=program_arguments,
        decision_source=str(row.get("decision_source", "")),
        split_from=str(row.get("split_from", "")),
        merge_with=str(row.get("merge_with", "")),
        generation_failures=str(row.get("generation_failures", "")),
        sample_uid=sample_uids[0] if sample_uids else "",
        sample_uids=sample_uids,
    )


def _build_proposed_units(audit: TaxonomyAuditIndex) -> None:
    for task in audit.tasks.values():
        for query in task.queries:
            unit = audit.proposed_units.get(query.proposed_task_id)
            if unit is None:
                unit = TaxonomyProposedUnitRecord(
                    domain=query.domain,
                    scene_id=query.scene_id,
                    proposed_task_id=query.proposed_task_id,
                    proposed_objective=query.proposed_objective,
                    semantic_root=query.semantic_root,
                    semantic_family=query.semantic_family,
                    semantic_leaf=query.semantic_leaf,
                    semantic_path=query.semantic_path,
                    program_signature_id=query.program_signature_id,
                    program_schema=query.program_schema,
                    base_program_contract=query.base_program_contract,
                    program_argument_axes=query.program_arguments,
                )
                audit.proposed_units[query.proposed_task_id] = unit
                audit.proposed_units_by_domain.setdefault(query.domain, []).append(query.proposed_task_id)
            else:
                unit.program_argument_axes = _merge_program_argument_payloads(
                    unit.program_argument_axes,
                    query.program_arguments,
                )
            unit.query_count += 1
            _append_unique(unit.source_task_ids, query.current_task_id)
            _append_unique(unit.query_ids, query.query_id)
            for answer_type in _split_pipe(query.answer_types):
                _append_unique(unit.answer_types, answer_type)
            for annotation_type in _split_pipe(query.annotation_types):
                _append_unique(unit.annotation_types, annotation_type)
            for sample_uid in query.sample_uids:
                _append_unique(unit.sample_uids, sample_uid)


def _example_sample_uids(
    *,
    review_index: ReviewIndex,
    domain: str,
    scene_id: str,
    task_id: str,
    query_id: str,
    limit: int,
) -> list[str]:
    query_key = ReviewIndex.query_key(domain, scene_id, task_id, query_id)
    query_samples = review_index.samples_by_query.get(query_key, [])
    if query_samples:
        return list(query_samples[: max(1, int(limit))])
    task_key = ReviewIndex.task_key(domain, scene_id, task_id)
    task_samples = review_index.samples_by_task.get(task_key, [])
    return list(task_samples[: max(1, int(limit))])


def _read_csv(path: Path, errors: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        errors.append(f"missing taxonomy CSV: {path}")
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_first_csv(round_dir: Path, errors: list[str], *filenames: str) -> list[dict[str, str]]:
    for filename in filenames:
        path = round_dir / filename
        if path.exists():
            return _read_csv(path, errors)
    errors.append(
        "missing taxonomy CSV: "
        + " or ".join(str(round_dir / filename) for filename in filenames)
    )
    return []


def _semantic_parts(
    *,
    program_signature_id: str,
    program_schema: str,
    proposed_objective: str,
    answer_schema: str,
    annotation_schema: str,
    domain: str,
    scene_id: str,
) -> tuple[str, str, str, str]:
    if program_signature_id:
        root = program_signature_id.split(".", 1)[0]
        family = program_signature_id
        leaf = proposed_objective or "proposed_task"
        return root, family, leaf, f"{root} / {family} / {leaf}"
    semantic = classify_objective(
        proposed_objective,
        answer_types=answer_schema,
        annotation_types=annotation_schema,
        domain=domain,
        scene_id=scene_id,
    )
    if program_schema:
        return semantic.root, semantic.family, semantic.leaf, f"{semantic.path} / {program_schema}"
    return semantic.root, semantic.family, semantic.leaf, semantic.path


def _task_slug(task_id: str) -> str:
    text = str(task_id or "")
    if "__" not in text:
        return text
    return text.rsplit("__", 1)[-1]


def _base_program_contract(program_schema: str) -> str:
    return str(program_schema or "").split("; query_branch=", 1)[0].strip()


def _parse_json_object(value: Any) -> dict[str, Any]:
    try:
        payload = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {
            "schema_version": "program_arguments_v0",
            "status": "needs_review",
            "parameter_axes": ["invalid_json"],
            "arguments": {},
            "constraints": ["invalid_json"],
        }
    return dict(payload) if isinstance(payload, Mapping) else {}


def _merge_program_argument_payloads(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    if not left:
        return dict(right) if isinstance(right, Mapping) else {}
    if not right:
        return dict(left)
    status_counts: dict[str, int] = {}
    for payload in (left, right):
        counts = payload.get("status_counts")
        if isinstance(counts, Mapping):
            for status, count in counts.items():
                try:
                    status_counts[str(status)] = status_counts.get(str(status), 0) + int(count)
                except (TypeError, ValueError):
                    status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        else:
            status = str(payload.get("status", "needs_review"))
            status_counts[status] = status_counts.get(status, 0) + 1

    arguments: dict[str, dict[str, Any]] = {}
    for payload in (left, right):
        payload_args = payload.get("arguments", {})
        if not isinstance(payload_args, Mapping):
            continue
        for name, entry in payload_args.items():
            if not isinstance(entry, Mapping):
                continue
            existing = arguments.setdefault(
                str(name),
                {
                    "value_type": str(entry.get("value_type", "semantic_role")),
                    "allowed_values": [],
                    "source": "",
                    "notes": "",
                },
            )
            existing["allowed_values"] = sorted(
                set(existing.get("allowed_values", []))
                | {str(value) for value in entry.get("allowed_values", []) if str(value)}
            )
            existing["source"] = _join_unique([existing.get("source", ""), str(entry.get("source", ""))], sep="|")
            existing["notes"] = _join_unique([existing.get("notes", ""), str(entry.get("notes", ""))], sep=" ")

    parameter_axes = sorted(
        {
            str(axis)
            for payload in (left, right)
            for axis in payload.get("parameter_axes", [])
            if str(axis)
        }
    )
    if status_counts.get("needs_review"):
        status = "needs_review"
    elif status_counts.get("inferred"):
        status = "inferred"
    else:
        status = "curated"
    return {
        "schema_version": str(left.get("schema_version") or right.get("schema_version") or "program_arguments_v0"),
        "status": status,
        "status_counts": dict(sorted(status_counts.items())),
        "parameter_axes": parameter_axes,
        "arguments": {name: arguments[name] for name in sorted(arguments)},
        "constraints": [],
    }


def _join_unique(values: list[str], sep: str = " | ") -> str:
    out: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in out:
            out.append(text)
    return sep.join(out)


def _load_json_safe(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"missing taxonomy JSON: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid taxonomy JSON {path}: {exc}")
        return {}


def _split_pipe(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def _append_unique(values: list[str], value: str) -> None:
    text = str(value or "")
    if text and text not in values:
        values.append(text)


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
