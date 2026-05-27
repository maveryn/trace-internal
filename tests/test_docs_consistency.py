"""Documentation consistency checks for active task contracts."""

from __future__ import annotations

import re
from pathlib import Path

import trace.tasks  # noqa: F401 - ensures task modules register on import
from scripts.check_active_inventory_integrity import collect_inventory_integrity_failures
from scripts.check_skill_consistency import collect_skill_consistency_failures
from scripts.generate_active_task_inventory import render_inventory_markdown
from trace.tasks import TASK_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
TASK_DOCS_ROOT = DOCS_ROOT / "tasks"


def _parse_markdown_links(markdown: str) -> set[str]:
    """Return markdown link targets from text."""
    return {match.group(1).strip() for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", markdown)}


def test_docs_readme_references_existing_files() -> None:
    readme_text = (DOCS_ROOT / "README.md").read_text(encoding="utf-8")
    referenced = set(re.findall(r"`([^`]+\.md)`", readme_text))
    for rel_path in sorted(referenced):
        if "*" in rel_path or "<" in rel_path:
            continue
        path = ROOT / rel_path if rel_path.startswith("docs/") else DOCS_ROOT / rel_path
        assert path.is_file(), f"missing docs reference: {rel_path}"


def test_each_registered_task_has_task_doc() -> None:
    for task_id in sorted(TASK_REGISTRY.keys()):
        task_doc = TASK_DOCS_ROOT / f"{task_id}.md"
        assert task_doc.is_file(), f"missing task doc for task_id='{task_id}'"


def test_task_docs_readme_links_match_registry() -> None:
    readme_text = (TASK_DOCS_ROOT / "README.md").read_text(encoding="utf-8")
    readme_links = {
        Path(target).name
        for target in _parse_markdown_links(readme_text)
        if str(target).lower().endswith(".md")
    }
    expected_links = {f"{task_id}.md" for task_id in TASK_REGISTRY.keys()}
    assert readme_links == expected_links

    task_doc_files = {
        path.name
        for path in TASK_DOCS_ROOT.glob("*.md")
        if path.name not in {"README.md", "TASK_DOC_TEMPLATE.md"}
    }
    assert task_doc_files == expected_links


def test_active_task_inventory_matches_registry_and_taxonomy() -> None:
    inventory_path = DOCS_ROOT / "ACTIVE_TASK_INVENTORY.md"
    assert inventory_path.is_file()
    assert not (DOCS_ROOT / "SCENE_TASK_COUNTS.md").exists()
    assert inventory_path.read_text(encoding="utf-8") == render_inventory_markdown()


def test_active_inventory_integrity_check_passes() -> None:
    failures = collect_inventory_integrity_failures(include_local_cache=False)
    assert not failures, "\n".join(failure.format() for failure in failures)


def test_repo_skills_match_active_domain_surface() -> None:
    failures = collect_skill_consistency_failures()
    assert not failures, "\n".join(failure.format() for failure in failures)
