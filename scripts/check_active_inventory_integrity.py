#!/usr/bin/env python3
"""Check active TRACE inventory integrity across registry, docs, configs, and imports.

This is a read-only guard for the current public task surface. Generated review
outputs under ``review/`` are intentionally out of scope; this script checks
source-of-truth docs and active runtime surfaces.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterator, Mapping

sys.dont_write_bytecode = True

import yaml

import trace.tasks  # noqa: F401 - register task classes before registry checks.
from scripts.audit_active_domain_surfaces import (
    ACTIVE_DOMAINS,
    ALLOWED_DOMAIN_DOCS,
    ALLOWED_TASK_TOP_LEVEL_EXTRAS,
)
from scripts.generate_active_task_inventory import render_inventory_markdown
from trace.core.taxonomy import missing_taxonomy_task_ids, resolve_task_taxonomy
from trace.tasks.registry import TASK_REGISTRY, list_default_task_ids, list_task_ids


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("trace", "configs", "prompts", "assets", "docs", "skills", "scripts", "tests", "review")
CACHE_DIR_NAMES = {"__pycache__", ".ipynb_checkpoints"}
CACHE_FILE_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class IntegrityFailure:
    """One inventory-integrity failure."""

    check: str
    message: str

    def format(self) -> str:
        return f"{self.check}: {self.message}"


def _dir_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {child.name for child in path.iterdir() if child.is_dir()}


def _file_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {child.name for child in path.iterdir() if child.is_file()}


def _walk_bundle_ids(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) == "bundle_id" and isinstance(child, str):
                yield str(child)
            yield from _walk_bundle_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_bundle_ids(child)


def _config_bundle_failures() -> list[IntegrityFailure]:
    failures: list[IntegrityFailure] = []
    for path in sorted((REPO_ROOT / "configs" / "domains").glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        domain = path.parts[-2]
        task_group = path.stem
        for bundle_id in sorted(set(_walk_bundle_ids(data))):
            prompt_path = REPO_ROOT / "prompts" / domain / task_group / f"{bundle_id}.json"
            if not prompt_path.exists():
                failures.append(
                    IntegrityFailure(
                        "prompt_bundle_missing",
                        f"{path.relative_to(REPO_ROOT)} references {bundle_id!r}, "
                        f"but {prompt_path.relative_to(REPO_ROOT)} does not exist",
                    )
                )
    return failures


def _git_tracked_cache_artifacts() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", *SOURCE_ROOTS],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    artifacts: list[str] = []
    for raw in result.stdout.splitlines():
        path = Path(raw)
        if any(part in CACHE_DIR_NAMES for part in path.parts) or path.suffix in CACHE_FILE_SUFFIXES:
            artifacts.append(str(path))
    return sorted(artifacts)


def _local_cache_artifacts() -> list[str]:
    artifacts: list[str] = []
    for root_name in SOURCE_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            rel = path.relative_to(REPO_ROOT)
            if path.is_dir() and path.name in CACHE_DIR_NAMES:
                artifacts.append(str(rel))
            elif path.is_file() and path.suffix in CACHE_FILE_SUFFIXES:
                artifacts.append(str(rel))
    return sorted(artifacts)


def _registered_task_modules() -> set[str]:
    modules: set[str] = set()
    task_root = REPO_ROOT / "trace" / "tasks"
    for path in task_root.rglob("*.py"):
        if path.name == "__init__.py" or any(part in CACHE_DIR_NAMES for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "@register_task" not in text:
            continue
        module = "trace.tasks." + ".".join(path.with_suffix("").relative_to(task_root).parts)
        modules.add(module)
    return modules


def collect_inventory_integrity_failures(*, include_local_cache: bool = False) -> list[IntegrityFailure]:
    """Return active-inventory integrity failures."""

    failures: list[IntegrityFailure] = []

    default_task_ids = sorted(list_default_task_ids())
    registered_task_ids = sorted(list_task_ids())
    default_set = set(default_task_ids)
    registered_set = set(registered_task_ids)
    missing_taxonomy = missing_taxonomy_task_ids(default_task_ids)

    if missing_taxonomy:
        failures.append(IntegrityFailure("missing_taxonomy", ", ".join(missing_taxonomy)))

    non_default_registered = sorted(registered_set - default_set)
    if non_default_registered:
        failures.append(IntegrityFailure("non_default_registered_tasks", ", ".join(non_default_registered)))

    invalid_registered = sorted(task_id for task_id in registered_task_ids if task_id.startswith("task_") and "__" not in task_id)
    if invalid_registered:
        failures.append(IntegrityFailure("invalid_registered_task_id_shape", ", ".join(invalid_registered)))

    for task_id in default_task_ids:
        taxonomy = resolve_task_taxonomy(task_id)
        if taxonomy.domain not in ACTIVE_DOMAINS:
            failures.append(
                IntegrityFailure("inactive_domain_task", f"{task_id} resolves to inactive domain {taxonomy.domain!r}")
            )

    expected_inventory = render_inventory_markdown()
    inventory_path = REPO_ROOT / "docs" / "ACTIVE_TASK_INVENTORY.md"
    if not inventory_path.exists() or inventory_path.read_text(encoding="utf-8") != expected_inventory:
        failures.append(IntegrityFailure("active_inventory_stale", "docs/ACTIVE_TASK_INVENTORY.md is stale"))

    task_docs_root = REPO_ROOT / "docs" / "tasks"
    task_doc_files = {
        path.name for path in task_docs_root.glob("task_*.md") if path.name not in {"README.md", "TASK_DOC_TEMPLATE.md"}
    }
    expected_doc_files = {f"{task_id}.md" for task_id in registered_task_ids}
    missing_docs = sorted(expected_doc_files - task_doc_files)
    extra_docs = sorted(task_doc_files - expected_doc_files)
    if missing_docs:
        failures.append(IntegrityFailure("task_docs_missing", ", ".join(missing_docs[:20])))
    if extra_docs:
        failures.append(IntegrityFailure("task_docs_stale", ", ".join(extra_docs[:20])))

    for rel in ("configs/domains", "prompts"):
        names = _dir_names(REPO_ROOT / rel)
        unexpected = sorted(names - ACTIVE_DOMAINS)
        if unexpected:
            failures.append(IntegrityFailure("unexpected_domain_surface", f"{rel}: {unexpected}"))

    task_dirs = _dir_names(REPO_ROOT / "trace" / "tasks")
    unexpected_task_dirs = sorted(task_dirs - ACTIVE_DOMAINS - ALLOWED_TASK_TOP_LEVEL_EXTRAS)
    if unexpected_task_dirs:
        failures.append(IntegrityFailure("unexpected_task_domain_dirs", ", ".join(unexpected_task_dirs)))

    domain_docs = _file_names(REPO_ROOT / "docs" / "domains")
    unexpected_domain_docs = sorted(domain_docs - ALLOWED_DOMAIN_DOCS)
    if unexpected_domain_docs:
        failures.append(IntegrityFailure("unexpected_domain_docs", ", ".join(unexpected_domain_docs)))

    for task_id in default_task_ids:
        taxonomy = resolve_task_taxonomy(task_id)
        source_domain = taxonomy.source_domain
        source_task_group = taxonomy.source_task_group
        config_candidates = {
            REPO_ROOT / "configs" / "domains" / source_domain / "base.yaml",
            REPO_ROOT / "configs" / "domains" / source_domain / f"{source_task_group}.yaml",
            REPO_ROOT / "configs" / "domains" / taxonomy.domain / "base.yaml",
            REPO_ROOT / "configs" / "domains" / taxonomy.domain / f"{source_task_group}.yaml",
        }
        if not any(path.exists() for path in config_candidates):
            failures.append(IntegrityFailure("task_config_missing", task_id))

    failures.extend(_config_bundle_failures())

    missing_loaded_modules = sorted(module for module in _registered_task_modules() if module not in sys.modules)
    if missing_loaded_modules:
        failures.append(
            IntegrityFailure(
                "registered_task_module_not_imported",
                ", ".join(missing_loaded_modules[:20]),
            )
        )

    tracked_cache = _git_tracked_cache_artifacts()
    if tracked_cache:
        failures.append(IntegrityFailure("tracked_source_cache_artifacts", ", ".join(tracked_cache[:20])))

    if include_local_cache:
        local_cache = _local_cache_artifacts()
        if local_cache:
            failures.append(IntegrityFailure("local_source_cache_artifacts", ", ".join(local_cache[:20])))

    return failures


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check active TRACE inventory integrity")
    parser.add_argument(
        "--include-local-cache",
        action="store_true",
        help="Also fail on local ignored cache artifacts under active source, docs, scripts, tests, and review.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    failures = collect_inventory_integrity_failures(include_local_cache=bool(args.include_local_cache))
    if failures:
        for failure in failures:
            print(failure.format(), file=sys.stderr)
        return 1
    print("active inventory integrity OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
