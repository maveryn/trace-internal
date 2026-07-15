#!/usr/bin/env python3
"""Validate code-authoritative task reasoning operations and their doc mirrors."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from trace.core.reasoning_operations import (
    REASONING_OPERATION_KEYS,
    REASONING_OPERATION_SCHEMA_VERSION,
    format_reasoning_operations_section,
    parse_reasoning_operations,
    program_contract_sha256,
)
from trace.tasks.registry import task_reasoning_operations


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "ACTIVE_TASK_INVENTORY.md"
TASK_DOC_ROOT = ROOT / "docs" / "tasks"
TASK_SOURCE_ROOT = ROOT / "trace" / "tasks"
_REASONING_SECTION_RE = re.compile(
    r"^## Reasoning Operations\s*$\n+.*?(?=^## |\Z)",
    flags=re.MULTILINE | re.DOTALL,
)
_PROGRAM_SECTION_RE = re.compile(
    r"^## Program Contract\s*$\n+.*?(?=^## |\Z)",
    flags=re.MULTILINE | re.DOTALL,
)


def _active_task_ids() -> list[str]:
    text = INVENTORY_PATH.read_text(encoding="utf-8")
    task_ids = re.findall(r"^- `(task_[a-z0-9_]+__[^`]+)`$", text, re.MULTILINE)
    if len(task_ids) != len(set(task_ids)):
        raise RuntimeError("active task inventory contains duplicate task ids")
    return task_ids


def _task_parts(task_id: str) -> tuple[str, str, str]:
    task_prefix, scene_id, objective = task_id.split("__", maxsplit=2)
    return task_prefix.removeprefix("task_"), scene_id, objective


def _task_doc_path(task_id: str) -> Path:
    domain, scene_id, _ = _task_parts(task_id)
    return TASK_DOC_ROOT / domain / scene_id / f"{task_id}.md"


def _task_source_path(task_id: str) -> Path:
    domain, scene_id, objective = _task_parts(task_id)
    return TASK_SOURCE_ROOT / domain / scene_id / f"{objective}.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sync_doc_section(text: str, operations: tuple[str, ...]) -> str:
    replacement = format_reasoning_operations_section(operations).rstrip()
    section_match = _REASONING_SECTION_RE.search(text)
    if section_match is not None:
        before = text[: section_match.start()].rstrip()
        after = text[section_match.end() :].lstrip()
        updated = before + "\n\n" + replacement
        if after:
            updated += "\n\n" + after
        return updated.rstrip() + "\n"
    program_match = _PROGRAM_SECTION_RE.search(text)
    if program_match is None:
        raise ValueError("missing '## Program Contract' section")
    insertion = program_match.end()
    before = text[:insertion].rstrip()
    after = text[insertion:].lstrip()
    updated = before + "\n\n" + replacement
    if after:
        updated += "\n\n" + after
    return updated.rstrip() + "\n"


def _load_rows(*, domain_filter: str | None, sync_docs: bool) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for task_id in _active_task_ids():
        domain, scene_id, objective = _task_parts(task_id)
        if domain_filter is not None and domain != domain_filter:
            continue
        doc_path = _task_doc_path(task_id)
        source_path = _task_source_path(task_id)
        if not doc_path.is_file():
            raise RuntimeError(f"missing task doc: {doc_path.relative_to(ROOT)}")
        if not source_path.is_file():
            raise RuntimeError(f"missing task source: {source_path.relative_to(ROOT)}")

        code_operations = task_reasoning_operations(task_id)
        doc_text = doc_path.read_text(encoding="utf-8")
        if sync_docs:
            updated = _sync_doc_section(doc_text, code_operations)
            if updated != doc_text:
                doc_path.write_text(updated, encoding="utf-8")
                doc_text = updated
        try:
            documented_operations = parse_reasoning_operations(doc_text)
            contract_hash = program_contract_sha256(doc_text)
        except ValueError as exc:
            raise RuntimeError(f"{doc_path.relative_to(ROOT)}: {exc}") from exc

        rows.append(
            {
                "task_id": task_id,
                "domain": domain,
                "scene_id": scene_id,
                "objective": objective,
                "operations": list(code_operations),
                "documented_operations": list(documented_operations),
                "doc_matches_code": documented_operations == code_operations,
                "source_sha256": _sha256(source_path),
                "program_contract_sha256": contract_hash,
                "source_path": str(source_path.relative_to(ROOT)),
                "doc_path": str(doc_path.relative_to(ROOT)),
            }
        )
    return rows


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    counts: Counter[str] = Counter()
    domain_counts: dict[str, Counter[str]] = defaultdict(Counter)
    multi_label_count = 0
    for row in rows:
        operations = tuple(str(value) for value in row["operations"])
        multi_label_count += int(len(operations) > 1)
        counts.update(operations)
        domain_counts[str(row["domain"])].update(operations)
    return {
        "task_count": len(rows),
        "multi_label_task_count": multi_label_count,
        "doc_drift_count": sum(not bool(row["doc_matches_code"]) for row in rows),
        "operation_counts": {key: counts[key] for key in REASONING_OPERATION_KEYS},
        "domain_operation_counts": {
            domain: {key: values[key] for key in REASONING_OPERATION_KEYS}
            for domain, values in sorted(domain_counts.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain")
    parser.add_argument("--sync-docs", action="store_true")
    parser.add_argument(
        "--allow-doc-drift",
        action="store_true",
        help="report code/doc differences without failing; intended for an active code-first audit",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    active_domains = sorted({_task_parts(task_id)[0] for task_id in _active_task_ids()})
    if args.domain is not None and args.domain not in active_domains:
        parser.error(f"unknown domain {args.domain!r}; expected one of {active_domains!r}")

    rows = _load_rows(domain_filter=args.domain, sync_docs=bool(args.sync_docs))
    summary = _summary(rows)
    if args.domain is None and int(summary["task_count"]) != 1000:
        raise RuntimeError(f"expected 1,000 active tasks, found {summary['task_count']}")
    missing_families = [
        key for key, count in summary["operation_counts"].items() if int(count) == 0
    ]
    if args.domain is None and missing_families:
        raise RuntimeError(f"unrepresented reasoning-operation families: {missing_families}")
    if int(summary["doc_drift_count"]) and not args.allow_doc_drift:
        drifted = [str(row["task_id"]) for row in rows if not bool(row["doc_matches_code"])]
        raise RuntimeError(
            "task docs drift from code-authoritative reasoning operations: "
            + ", ".join(drifted[:20])
            + (" ..." if len(drifted) > 20 else "")
        )

    payload = {
        "schema_version": REASONING_OPERATION_SCHEMA_VERSION,
        "assignment_source": "public_task_class.reasoning_operations",
        "inventory": str(INVENTORY_PATH.relative_to(ROOT)),
        "domain_filter": args.domain,
        "canonical_order": list(REASONING_OPERATION_KEYS),
        "summary": summary,
        "tasks": rows,
    }
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
