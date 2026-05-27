#!/usr/bin/env python3
"""Audit public domain surface directories and docs.

This intentionally checks only discoverable domain surfaces, not planning notes
or task implementation internals.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_DOMAINS = {
    "charts",
    "games",
    "geometry",
    "graph",
    "icons",
    "illustrations",
    "pages",
    "physics",
    "puzzles",
    "three_d",
}

ALLOWED_TASK_TOP_LEVEL_EXTRAS = {"shared", "__pycache__"}
ALLOWED_DOMAIN_DOCS = {
    "README.md",
    "SCENE_TASK_QUERY_GUIDE.md",
    "CHART_DOMAIN_PLAN.md",
    "CHART_TASK_SETUP.md",
    "GAMES_TASK_SETUP.md",
    "GEOMETRY_TASK_SETUP.md",
    "GRAPH_TASK_SETUP.md",
    "ICON_TASK_SETUP.md",
    "ILLUSTRATIONS_TASK_SETUP.md",
    "PAGES_TASK_SETUP.md",
    "PHYSICS_TASK_SETUP.md",
    "PUZZLE_TASK_SETUP.md",
    "THREE_D_TASK_SETUP.md",
}


def _dir_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {child.name for child in path.iterdir() if child.is_dir()}


def _file_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {child.name for child in path.iterdir() if child.is_file()}


def main() -> int:
    failures: list[str] = []

    for rel in ("configs/domains", "prompts"):
        names = _dir_names(REPO_ROOT / rel)
        unexpected = sorted(names - ACTIVE_DOMAINS)
        if unexpected:
            failures.append(f"{rel}: unexpected domain directories: {unexpected}")

    task_names = _dir_names(REPO_ROOT / "trace/tasks")
    unexpected_tasks = sorted(task_names - ACTIVE_DOMAINS - ALLOWED_TASK_TOP_LEVEL_EXTRAS)
    if unexpected_tasks:
        failures.append(f"trace/tasks: unexpected top-level directories: {unexpected_tasks}")

    domain_docs = _file_names(REPO_ROOT / "docs/domains")
    unexpected_docs = sorted(domain_docs - ALLOWED_DOMAIN_DOCS)
    if unexpected_docs:
        failures.append(f"docs/domains: unexpected files: {unexpected_docs}")

    skill_dirs = _dir_names(REPO_ROOT / "skills")
    domain_skill_dirs = {name for name in skill_dirs if name.startswith("domain-")}
    allowed_domain_skill_dirs = {f"domain-{domain}" for domain in ACTIVE_DOMAINS} | {"domain-audit"}
    unexpected_skill_dirs = sorted(domain_skill_dirs - allowed_domain_skill_dirs)
    if unexpected_skill_dirs:
        failures.append(f"skills: unexpected domain skill directories: {unexpected_skill_dirs}")

    complexity_refs = _file_names(REPO_ROOT / "skills/task-complexity/references")
    allowed_complexity_refs = {f"{domain}.md" for domain in ACTIVE_DOMAINS} | {"policy.md"}
    unexpected_complexity_refs = sorted(complexity_refs - allowed_complexity_refs)
    if unexpected_complexity_refs:
        failures.append(f"skills/task-complexity/references: unexpected files: {unexpected_complexity_refs}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("active domain surfaces OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
