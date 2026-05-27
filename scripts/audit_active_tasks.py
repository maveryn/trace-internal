#!/usr/bin/env python3
"""Audit the current default-enabled TRACE task surface.

The audit is intentionally read-only with respect to task/config code. It writes
only the requested audit reports under ``plans/``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import traceback
from typing import Any, Iterable, Mapping

import trace.tasks  # noqa: F401 - registers task classes.
from trace.core.seed import hash64
from trace.core.taxonomy import (
    ACTIVE_DOMAINS,
    inject_taxonomy_metadata,
    missing_taxonomy_task_ids,
    resolve_task_query_id,
    resolve_task_taxonomy,
)
from trace.tasks import create_task
from trace.tasks.registry import TASK_REGISTRY, list_default_task_ids, list_task_ids


DOMAIN_DOCS: dict[str, str] = {
    "charts": "CHART_TASK_SETUP.md",
    "games": "GAMES_TASK_SETUP.md",
    "geometry": "GEOMETRY_TASK_SETUP.md",
    "graph": "GRAPH_TASK_SETUP.md",
    "icons": "ICON_TASK_SETUP.md",
    "illustrations": "ILLUSTRATIONS_TASK_SETUP.md",
    "pages": "PAGES_TASK_SETUP.md",
    "physics": "PHYSICS_TASK_SETUP.md",
    "puzzles": "PUZZLE_TASK_SETUP.md",
    "three_d": "THREE_D_TASK_SETUP.md",
}

REQUIRED_TRACE_KEYS: tuple[str, ...] = (
    "scene_ir",
    "query_spec",
    "render_spec",
    "render_map",
    "execution_trace",
    "witness_symbolic",
    "projected_evidence",
)
CURRENT_CALIBRATION_BASELINE = "v0"
CURRENT_CALIBRATION_MODEL_SLUG = "qwen25vl7b"


@dataclass(frozen=True)
class ProgressRecord:
    """One parsed row from ``plans/PROGRESS_SUMMARY.md``."""

    section: str
    status: str
    config: str
    hard: str
    easy: str
    band: str
    artifacts: str
    notes: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit active default TRACE tasks")
    parser.add_argument("--output-md", default="plans/active_task_audit.md")
    parser.add_argument("--output-json", default="plans/active_task_audit.json")
    parser.add_argument(
        "--review-status-out",
        default="",
        help="Optional path to refresh from current active-task audit results.",
    )
    parser.add_argument("--max-attempts", type=int, default=120)
    parser.add_argument("--smoke-seeds", type=int, default=8)
    parser.add_argument(
        "--tasks",
        default="",
        help="Comma-separated active task ids to smoke; static inventory still covers all active tasks.",
    )
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    return parser.parse_args()


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_progress_summary(path: Path) -> dict[str, ProgressRecord]:
    text = _read_text(path)
    records: dict[str, ProgressRecord] = {}
    section = ""
    for raw_line in text.splitlines():
        header = re.match(r"^##\s+(.+?)\s*$", raw_line)
        if header:
            section = header.group(1).strip()
            continue
        if not raw_line.startswith("| `task_"):
            continue
        parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
        if len(parts) < 8:
            continue
        task_id = parts[0].strip("`")
        records[task_id] = ProgressRecord(
            section=section,
            status=parts[1],
            config=parts[2],
            hard=parts[3],
            easy=parts[4],
            band=parts[5],
            artifacts=parts[6],
            notes=parts[7],
        )
    return records


def _parse_review_status(path: Path, active_task_ids: set[str]) -> dict[str, Any]:
    text = _read_text(path)
    rows: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.startswith("| task_"):
            continue
        parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
        if parts and parts[0] == "task_id":
            continue
        if parts:
            rows.append(parts[0])
    row_set = set(rows)
    return {
        "path": str(path),
        "exists": path.exists(),
        "row_count": len(rows),
        "rows_not_default_count": len(sorted(row_set - active_task_ids)),
        "rows_not_default": sorted(row_set - active_task_ids),
        "missing_default_rows_count": len(sorted(active_task_ids - row_set)),
        "missing_default_rows": sorted(active_task_ids - row_set),
    }


def _load_file_texts(paths: Iterable[Path]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in sorted(paths):
        if path.is_file():
            texts[str(path)] = _read_text(path)
    return texts


def _paths_under(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file() and path.suffix in suffixes]


def _index_xlsx(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.xlsx") if path.is_file())


def _contains_any(texts: Mapping[str, str], needle: str) -> list[str]:
    return sorted(path for path, text in texts.items() if needle in text)


def _domain_skill_exists(domain: str) -> bool:
    direct = Path("skills") / f"domain-{domain}" / "SKILL.md"
    return direct.exists()


def _domain_doc_path(domain: str) -> Path:
    name = DOMAIN_DOCS.get(domain, f"{domain.upper()}_TASK_SETUP.md")
    return Path("docs") / "domains" / name


def _extract_prompt_template_paths(output: Any) -> list[str]:
    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        return []
    query_spec = trace_payload.get("query_spec", {})
    if not isinstance(query_spec, Mapping):
        return []
    prompt_variant = query_spec.get("prompt_variant", {})
    if not isinstance(prompt_variant, Mapping):
        return []
    raw_paths = prompt_variant.get("template_paths", [])
    if not isinstance(raw_paths, list):
        return []
    return [str(item) for item in raw_paths if str(item).strip()]


def _prompt_path_exists(template_path: str) -> bool:
    raw = Path(template_path)
    candidates = [raw, Path("prompts") / raw]
    return any(path.exists() for path in candidates)


def _generate_smoke(task_id: str, *, max_attempts: int, smoke_seeds: int) -> dict[str, Any]:
    task = create_task(task_id)
    last_error = ""
    for seed_index in range(smoke_seeds):
        instance_seed = int(hash64(0, f"{task_id}:active_task_audit", seed_index))
        try:
            output = task.generate(
                instance_seed,
                params={},
                max_attempts=max_attempts,
            )
            taxonomy = resolve_task_taxonomy(
                task_id,
                source_domain=str(getattr(task, "domain", "")),
                source_task_group=str(getattr(task, "task_group", "")),
            )
            query_variant = str(getattr(output, "query_variant", "") or "default")
            trace_payload = getattr(output, "trace_payload", {})
            if not isinstance(trace_payload, Mapping):
                trace_payload = {}
            query_id = str(
                getattr(output, "query_id", "")
                or resolve_task_query_id(query_variant=query_variant, trace_payload=trace_payload)
            )
            injected = inject_taxonomy_metadata(
                dict(trace_payload),
                task_id=task_id,
                taxonomy=taxonomy,
                query_id=query_id,
                registered_domain=str(getattr(task, "domain", "")),
                registered_task_group=str(getattr(task, "task_group", "")),
            )
            taxonomy_payload = injected.get("taxonomy", {})
            taxonomy_public = taxonomy_payload.get("public", {}) if isinstance(taxonomy_payload, Mapping) else {}
            taxonomy_registered = (
                taxonomy_payload.get("registered", {}) if isinstance(taxonomy_payload, Mapping) else {}
            )
            taxonomy_source = taxonomy_payload.get("source", {}) if isinstance(taxonomy_payload, Mapping) else {}
            template_paths = _extract_prompt_template_paths(output)
            missing_template_paths = [path for path in template_paths if not _prompt_path_exists(path)]
            trace_missing_keys = [key for key in REQUIRED_TRACE_KEYS if key not in trace_payload]
            output_scene_id = str(getattr(output, "scene_id", "") or "")
            scene_id_matches = output_scene_id in {"", taxonomy.scene_id}
            query_spec = trace_payload.get("query_spec", {})
            execution_trace = trace_payload.get("execution_trace", {})
            return {
                "ok": True,
                "seed_index": seed_index,
                "instance_seed": instance_seed,
                "query_variant": query_variant,
                "query_id": query_id,
                "output_scene_id": output_scene_id,
                "resolved_scene_id": taxonomy.scene_id,
                "scene_id_matches_taxonomy": scene_id_matches,
                "answer_type": str(getattr(getattr(output, "answer_gt", None), "type", "")),
                "evidence_type": str(getattr(getattr(output, "evidence_gt", None), "type", "")),
                "trace_missing_keys": trace_missing_keys,
                "taxonomy_metadata_after_injection": {
                    "domain": str(taxonomy_payload.get("domain", "")),
                    "scene_id": str(taxonomy_payload.get("scene_id", "")),
                    "task_id": str(taxonomy_payload.get("task_id", "")),
                    "query_id": str(taxonomy_payload.get("query_id", "")),
                    "public": dict(taxonomy_public) if isinstance(taxonomy_public, Mapping) else {},
                    "registered": dict(taxonomy_registered) if isinstance(taxonomy_registered, Mapping) else {},
                    "source": dict(taxonomy_source) if isinstance(taxonomy_source, Mapping) else {},
                },
                "prompt_template_paths": template_paths,
                "missing_prompt_template_paths": missing_template_paths,
                "query_spec_has_query_id": isinstance(query_spec, Mapping) and bool(query_spec.get("query_id")),
                "execution_trace_has_query_id": isinstance(execution_trace, Mapping)
                and bool(execution_trace.get("query_id")),
            }
        except Exception as exc:  # pragma: no cover - audit diagnostics only.
            last_error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    return {
        "ok": False,
        "error": last_error or f"failed across {smoke_seeds} seeds",
        "query_variant": "",
        "query_id": "",
        "output_scene_id": "",
        "resolved_scene_id": "",
        "scene_id_matches_taxonomy": False,
        "answer_type": "",
        "evidence_type": "",
        "trace_missing_keys": list(REQUIRED_TRACE_KEYS),
        "taxonomy_metadata_after_injection": {},
        "prompt_template_paths": [],
        "missing_prompt_template_paths": [],
        "query_spec_has_query_id": False,
        "execution_trace_has_query_id": False,
    }


def _resolve_task_selection(raw_tasks: str, active_task_ids: list[str]) -> set[str] | None:
    raw = str(raw_tasks or "").strip()
    if not raw:
        return None
    active_set = set(active_task_ids)
    selected = {item.strip() for item in raw.split(",") if item.strip()}
    unknown = sorted(selected - active_set)
    if unknown:
        raise ValueError(f"--tasks contains non-active or unknown task ids: {', '.join(unknown)}")
    return selected


def _artifact_matches(index: list[Path], task_id: str, *, solve_only: bool = False) -> list[str]:
    matches: list[str] = []
    for path in index:
        name = path.name
        path_text = str(path)
        if task_id not in name and task_id not in path_text:
            continue
        if solve_only and "solve_rate_distribution" not in name:
            continue
        if not solve_only and "solve_rate_distribution" in name:
            continue
        if solve_only:
            required_label = f"_{CURRENT_CALIBRATION_MODEL_SLUG}_{CURRENT_CALIBRATION_BASELINE}_"
            if required_label not in name:
                continue
        else:
            manifest_path = path.parent / "manifest.json"
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(manifest.get("calibration_baseline", "")).strip() != CURRENT_CALIBRATION_BASELINE:
                continue
        matches.append(path_text)
    return sorted(matches)


def _status_from_checks(*, blocking: list[str], gaps: list[str]) -> str:
    if blocking:
        return "blocked"
    if gaps:
        return "audit_gap"
    return "audited"


def _build_audit(args: argparse.Namespace) -> dict[str, Any]:
    active_task_ids = sorted(list_default_task_ids())
    active_set = set(active_task_ids)
    selected_for_smoke = _resolve_task_selection(args.tasks, active_task_ids)
    all_task_ids = sorted(list_task_ids())
    invalid_default_ids = sorted(task_id for task_id in active_task_ids if task_id.startswith("task_") and "__" not in task_id)
    missing_taxonomy = sorted(missing_taxonomy_task_ids(active_task_ids))

    docs_readme = _read_text(Path("docs/tasks/README.md"))
    docs_task_files = set(path.name for path in Path("docs/tasks").glob("task_*.md"))
    tests_texts = _load_file_texts(Path("tests").glob("test_*.py"))
    global_contract_path = Path("tests/test_active_default_task_contracts.py")
    global_contract_text = _read_text(global_contract_path)
    has_global_contract_test = (
        global_contract_path.exists()
        and "list_default_task_ids" in global_contract_text
        and "query_variant" in global_contract_text
        and "query_id" in global_contract_text
    )
    config_texts = _load_file_texts(_paths_under(Path("configs/domains"), (".yaml", ".yml")))
    prompt_texts = _load_file_texts(_paths_under(Path("prompts"), (".json", ".txt", ".md")))
    plans_review_index = _index_xlsx(Path("plans/task-reviews"))
    progress = _parse_progress_summary(Path("plans/PROGRESS_SUMMARY.md"))
    review_status = _parse_review_status(Path("plans/task-reviews/REVIEW_STATUS.md"), active_set)

    tasks: list[dict[str, Any]] = []

    for task_id in active_task_ids:
        task_cls = TASK_REGISTRY[task_id]
        task_obj = task_cls()
        source_domain = str(getattr(task_obj, "domain", ""))
        source_task_group = str(getattr(task_obj, "task_group", ""))
        taxonomy = resolve_task_taxonomy(
            task_id,
            source_domain=source_domain,
            source_task_group=source_task_group,
        )
        domain_doc = _domain_doc_path(taxonomy.domain)
        task_doc_name = f"{task_id}.md"
        task_doc_path = Path("docs/tasks") / task_doc_name
        relevant_config_paths = [
            Path("configs/domains") / source_domain / "base.yaml",
            Path("configs/domains") / source_domain / f"{source_task_group}.yaml",
            Path("configs/domains") / taxonomy.domain / "base.yaml",
            Path("configs/domains") / taxonomy.domain / f"{source_task_group}.yaml",
        ]
        config_paths = sorted({str(path) for path in relevant_config_paths if path.exists()})
        config_mentions = _contains_any(config_texts, task_id)
        test_mentions = _contains_any(tests_texts, task_id)
        prompt_mentions = _contains_any(prompt_texts, task_id)
        progress_record = progress.get(task_id)
        plans_review_workbooks = _artifact_matches(plans_review_index, task_id)
        plans_solve_workbooks = _artifact_matches(plans_review_index, task_id, solve_only=True)

        should_smoke = not bool(args.skip_smoke)
        if selected_for_smoke is not None and task_id not in selected_for_smoke:
            should_smoke = False
        smoke = (
            _generate_smoke(task_id, max_attempts=args.max_attempts, smoke_seeds=args.smoke_seeds)
            if should_smoke
            else {"ok": None, "skipped": True}
        )

        blocking: list[str] = []
        gaps: list[str] = []

        if task_id in missing_taxonomy:
            blocking.append("missing_taxonomy")
        if task_id in invalid_default_ids:
            blocking.append("invalid_task_id_shape")
        if taxonomy.domain not in ACTIVE_DOMAINS:
            blocking.append("domain_not_active")
        if smoke.get("ok") is False:
            blocking.append("generation_smoke_failed")
        if smoke.get("ok") is True:
            if smoke.get("trace_missing_keys"):
                blocking.append("trace_required_keys_missing")
            if not smoke.get("answer_type"):
                blocking.append("answer_type_missing")
            if not smoke.get("evidence_type"):
                blocking.append("evidence_type_missing")
            if not smoke.get("scene_id_matches_taxonomy"):
                blocking.append("output_scene_id_mismatch")
            if not smoke.get("query_id"):
                gaps.append("query_id_missing")
            if smoke.get("query_variant") != "default":
                gaps.append("non_default_query_variant")
            if smoke.get("missing_prompt_template_paths"):
                gaps.append("prompt_template_path_missing")

        if task_doc_name not in docs_task_files:
            gaps.append("task_doc_missing")
        if task_doc_name not in docs_readme and task_id not in docs_readme:
            gaps.append("task_doc_not_indexed")
        if not domain_doc.exists():
            gaps.append("domain_doc_missing")
        if not _domain_skill_exists(taxonomy.domain):
            gaps.append("domain_skill_missing")
        if not config_paths:
            gaps.append("config_group_missing")
        if (not has_global_contract_test) and not test_mentions:
            gaps.append("test_mention_missing")
        if not progress_record:
            gaps.append("progress_summary_row_missing")
        if not plans_review_workbooks:
            gaps.append("plans_task_review_workbook_missing")
        if not plans_solve_workbooks and not (
            progress_record
            and "solve" in progress_record.artifacts.lower()
            and "pending" not in progress_record.artifacts.lower()
        ):
            gaps.append("solve_rate_artifact_missing")
        tasks.append(
            {
                "task_id": task_id,
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "source_domain": taxonomy.source_domain,
                "source_task_group": taxonomy.source_task_group,
                "registered": task_id in all_task_ids,
                "default_enabled": task_id in active_set,
                "taxonomy_present": task_id not in missing_taxonomy,
                "domain_active": taxonomy.domain in ACTIVE_DOMAINS,
                "docs": {
                    "task_doc_exists": task_doc_name in docs_task_files,
                    "task_doc_path": str(task_doc_path),
                    "task_doc_indexed": task_doc_name in docs_readme or task_id in docs_readme,
                    "domain_doc_exists": domain_doc.exists(),
                    "domain_doc_path": str(domain_doc),
                    "domain_skill_exists": _domain_skill_exists(taxonomy.domain),
                },
                "configs": {
                    "config_paths": config_paths,
                    "task_id_mentions": config_mentions,
                    "has_group_or_base_config": bool(config_paths),
                },
                "prompts": {
                    "task_id_mentions": prompt_mentions,
                    "template_paths_from_smoke": list(smoke.get("prompt_template_paths", [])),
                    "missing_template_paths_from_smoke": list(smoke.get("missing_prompt_template_paths", [])),
                },
                "tests": {"task_id_mentions": test_mentions},
                "global_contract_test": {
                    "exists": has_global_contract_test,
                    "path": str(global_contract_path),
                },
                "smoke": smoke,
                "review_artifacts": {
                    "plans_review_workbooks": plans_review_workbooks,
                    "plans_solve_workbooks": plans_solve_workbooks,
                },
                "progress_summary": None
                if progress_record is None
                else {
                    "section": progress_record.section,
                    "status": progress_record.status,
                    "hard": progress_record.hard,
                    "easy": progress_record.easy,
                    "band": progress_record.band,
                    "artifacts": progress_record.artifacts,
                    "notes": progress_record.notes,
                },
                "blocking_issues": sorted(set(blocking)),
                "audit_gaps": sorted(set(gaps)),
                "audit_status": _status_from_checks(blocking=blocking, gaps=gaps),
            }
        )

    by_domain: dict[str, Any] = {}
    for domain in ACTIVE_DOMAINS:
        domain_tasks = [task for task in tasks if task["domain"] == domain]
        scene_counter = Counter(str(task["scene_id"]) for task in domain_tasks)
        status_counter = Counter(str(task["audit_status"]) for task in domain_tasks)
        gap_counter: Counter[str] = Counter()
        blocking_counter: Counter[str] = Counter()
        for task in domain_tasks:
            gap_counter.update(task["audit_gaps"])
            blocking_counter.update(task["blocking_issues"])
        by_domain[domain] = {
            "task_count": len(domain_tasks),
            "scene_count": len(scene_counter),
            "scenes": dict(sorted(scene_counter.items())),
            "status_counts": dict(sorted(status_counter.items())),
            "gap_counts": dict(sorted(gap_counter.items())),
            "blocking_counts": dict(sorted(blocking_counter.items())),
        }

    status_counter = Counter(str(task["audit_status"]) for task in tasks)
    gap_counter = Counter(gap for task in tasks for gap in task["audit_gaps"])
    blocking_counter = Counter(issue for task in tasks for issue in task["blocking_issues"])

    return {
        "schema_version": "active_task_audit_v0",
        "scope": {
            "surface": "default_enabled_tasks",
            "active_domains": list(ACTIVE_DOMAINS),
            "smoke_skipped": bool(args.skip_smoke),
            "max_attempts": int(args.max_attempts),
            "smoke_seeds": int(args.smoke_seeds),
        },
        "summary": {
            "default_task_count": len(active_task_ids),
            "registered_task_count": len(all_task_ids),
            "domain_count": len(ACTIVE_DOMAINS),
            "missing_taxonomy_count": len(missing_taxonomy),
            "missing_taxonomy": missing_taxonomy,
            "invalid_default_ids_count": len(invalid_default_ids),
            "invalid_default_ids": invalid_default_ids,
            "status_counts": dict(sorted(status_counter.items())),
            "gap_counts": dict(sorted(gap_counter.items())),
            "blocking_counts": dict(sorted(blocking_counter.items())),
        },
        "stale_inventory": {"review_status": review_status},
        "domains": by_domain,
        "tasks": tasks,
    }


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return lines


def _render_markdown(audit: Mapping[str, Any]) -> str:
    summary = audit["summary"]
    stale = audit["stale_inventory"]["review_status"]
    lines: list[str] = [
        "# Active Task Audit",
        "",
        "Generated by `scripts/audit_active_tasks.py` for the current default-enabled TRACE task surface.",
        "",
        "## Summary",
        "",
        f"- Default tasks audited: `{summary['default_task_count']}`",
        f"- Registered tasks seen: `{summary['registered_task_count']}`",
        f"- Public domains: `{audit['summary']['domain_count']}`",
        f"- Missing taxonomy mappings: `{summary['missing_taxonomy_count']}`",
        f"- Invalid default task id shapes: `{summary['invalid_default_ids_count']}`",
        f"- Audit statuses: `{json.dumps(summary['status_counts'], sort_keys=True)}`",
        "",
        "A task is `blocked` only when active taxonomy or generation-contract checks fail. Missing task-review or solve-rate artifacts are `audit_gap` findings.",
        "",
        (
            "`plans/task-reviews/` is the required manual-review artifact root for this audit. "
            f"Review manifests must carry `calibration_baseline={CURRENT_CALIBRATION_BASELINE}` and solve-rate "
            f"workbooks must use `{CURRENT_CALIBRATION_MODEL_SLUG}_{CURRENT_CALIBRATION_BASELINE}` to count as current. "
            "A root-level `task-reviews/` tree is not counted as an active-review requirement."
        ),
        "",
        "## Domain Overview",
        "",
    ]
    domain_rows: list[list[Any]] = []
    for domain, data in audit["domains"].items():
        domain_rows.append(
            [
                domain,
                data["task_count"],
                data["scene_count"],
                json.dumps(data["status_counts"], sort_keys=True),
                data["gap_counts"].get("plans_task_review_workbook_missing", 0),
                data["gap_counts"].get("solve_rate_artifact_missing", 0),
                json.dumps(data["blocking_counts"], sort_keys=True),
            ]
        )
    lines.extend(
        _markdown_table(
            [
                "Domain",
                "Tasks",
                "Scenes",
                "Statuses",
                "Missing review",
                "Missing solve",
                "Blocking",
            ],
            domain_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Stale Inventory Notes",
            "",
            f"- `plans/task-reviews/REVIEW_STATUS.md` exists: `{stale['exists']}`",
            f"- REVIEW_STATUS rows: `{stale['row_count']}`",
            f"- REVIEW_STATUS rows not in current defaults: `{stale['rows_not_default_count']}`",
            f"- Current defaults missing from REVIEW_STATUS: `{stale['missing_default_rows_count']}`",
        ]
    )
    if int(stale.get("rows_not_default_count", 0)) or int(stale.get("missing_default_rows_count", 0)):
        lines.append("- This file is non-authoritative for the current active inventory until refreshed.")
    else:
        lines.append("- REVIEW_STATUS matches the current default task ids.")
    lines.extend(["", "## Top Gap Counts", ""])
    gap_rows = [[gap, count] for gap, count in sorted(summary["gap_counts"].items(), key=lambda item: (-item[1], item[0]))]
    if gap_rows:
        lines.extend(_markdown_table(["Gap", "Tasks"], gap_rows))
    else:
        lines.append("No audit gaps found.")
    lines.extend(["", "## Blocking Issue Counts", ""])
    blocking_rows = [
        [issue, count] for issue, count in sorted(summary["blocking_counts"].items(), key=lambda item: (-item[1], item[0]))
    ]
    if blocking_rows:
        lines.extend(_markdown_table(["Issue", "Tasks"], blocking_rows))
    else:
        lines.append("No blocking active-taxonomy or generation-contract issues found.")

    lines.extend(["", "## Per-Domain Task Results", ""])
    tasks = list(audit["tasks"])
    for domain in audit["scope"]["active_domains"]:
        domain_tasks = [task for task in tasks if task["domain"] == domain]
        lines.extend([f"### {domain}", ""])
        rows: list[list[Any]] = []
        for task in domain_tasks:
            progress = task.get("progress_summary") or {}
            smoke = task.get("smoke") or {}
            rows.append(
                [
                    f"`{task['task_id']}`",
                    task["scene_id"],
                    task["audit_status"],
                    progress.get("status", "-"),
                    smoke.get("query_variant", "-"),
                    smoke.get("query_id", "-"),
                    smoke.get("answer_type", "-"),
                    smoke.get("evidence_type", "-"),
                    ", ".join(task["blocking_issues"]) or "-",
                    ", ".join(task["audit_gaps"]) or "-",
                ]
            )
        lines.extend(
            _markdown_table(
                [
                    "Task",
                    "Scene",
                    "Audit",
                    "Progress",
                    "Variant",
                    "Query",
                    "Answer",
                    "Evidence",
                    "Blocking",
                    "Gaps",
                ],
                rows,
            )
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_review_status(audit: Mapping[str, Any]) -> str:
    """Render the review-status table from active audit results."""

    lines: list[str] = [
        "# Task Review Status",
        "",
        "Generated from `plans/active_task_audit.json` by `scripts/audit_active_tasks.py`.",
        "This table intentionally contains only current default-enabled task ids.",
        "",
        "| task_id | latest_run_id | status | notes |",
        "|---|---|---|---|",
    ]
    for task in sorted(audit["tasks"], key=lambda item: str(item["task_id"])):
        task_id = str(task["task_id"])
        status = str(task["audit_status"])
        gaps = list(task.get("audit_gaps", []))
        blocking = list(task.get("blocking_issues", []))
        progress = task.get("progress_summary") or {}
        review_artifacts = task.get("review_artifacts") or {}
        review_count = len(review_artifacts.get("plans_review_workbooks", []))
        solve_count = len(review_artifacts.get("plans_solve_workbooks", []))
        note_parts: list[str] = [
            f"domain={task['domain']}",
            f"scene={task['scene_id']}",
            f"progress={progress.get('status', '-')}",
            f"review_workbooks={review_count}",
            f"solve_workbooks={solve_count}",
        ]
        if blocking:
            note_parts.append("blocking=" + ",".join(str(item) for item in blocking))
        if gaps:
            note_parts.append("gaps=" + ",".join(str(item) for item in gaps))
        else:
            note_parts.append("gaps=none")
        notes = "; ".join(note_parts).replace("|", "\\|")
        lines.append(f"| {task_id} | {task_id} | {status} | {notes} |")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = _parse_args()
    audit = _build_audit(args)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(_render_markdown(audit), encoding="utf-8")
    if str(args.review_status_out or "").strip():
        review_status_path = Path(args.review_status_out)
        review_status_path.parent.mkdir(parents=True, exist_ok=True)
        review_status_path.write_text(_render_review_status(audit), encoding="utf-8")
    blocked = int(audit["summary"]["status_counts"].get("blocked", 0))
    print(f"wrote {output_json}")
    print(f"wrote {output_md}")
    print(json.dumps(audit["summary"], indent=2, sort_keys=True))
    if args.fail_on_blocked and blocked:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
