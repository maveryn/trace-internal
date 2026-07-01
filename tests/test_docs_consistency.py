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
TASK_ID_RE = re.compile(r"\btask_[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+\b")
TASK_DOC_LOCAL_REF_RE = re.compile(
    r"`((?:prompts|trace/tasks|configs/domains)/[^`]+(?:\.json|\.py|\.yaml))`"
)
BENCHMARK_COVERAGE_SCRIPT_PATHS = (
    ROOT / "scripts" / "analyze_vero_benchmark_failures.py",
    ROOT / "scripts" / "review_vero_coverage.py",
    ROOT / "scripts" / "review_vero_round2_expansion.py",
)
ALLOWED_DOCS_TOP_LEVEL = {
    "ACTIVE_TASK_INVENTORY.md",
    "README.md",
    "RLVR_TRAINING_STRATEGY.md",
    "RLVR_TASK_SPLIT_PLAN.md",
    "SCENE_PACKAGE_MIGRATION",
    "TODO.md",
    "contracts",
    "domain-finalization-review",
    "domain-migration-report",
    "domains",
    "review",
    "resources",
    "tasks",
    "workflows",
}
BANNED_DOC_ROOTS = (
    ROOT / "docs" / "core",
    ROOT / "docs" / "project",
    ROOT / "plans",
    ROOT / "review" / "docs",
    ROOT / "review" / "code-review",
    ROOT / "review" / "taxonomy-audit",
    ROOT / "review" / "trace-extension",
)
BANNED_REFERENCE_FRAGMENTS = (
    "docs/core/",
    "docs/project/",
    "plans/",
    "review/docs/",
    "review/code-review/",
    "review/taxonomy-audit/",
    "review/trace-extension/",
)
DOC_STRUCTURE_SCANNED_ROOTS = (
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs",
    ROOT / "skills",
    ROOT / "scripts",
    ROOT / "tests",
)
DOC_STRUCTURE_REFERENCE_ALLOWLIST = {
    ROOT / "docs" / "workflows" / "DOC_STRUCTURE.md",
    Path(__file__).resolve(),
}


def _task_doc_rel_path(task_id: str) -> Path:
    """Return the canonical task-doc path below docs/tasks."""

    prefix, scene_id, _objective = task_id.split("__", 2)
    return Path(prefix.removeprefix("task_")) / scene_id / f"{task_id}.md"


def _iter_text_files(paths: tuple[Path, ...]) -> list[Path]:
    suffixes = {".md", ".py", ".yaml", ".yml", ".json", ".toml", ".txt"}
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix in suffixes:
                files.append(path)
            continue
        files.extend(
            child
            for child in path.rglob("*")
            if child.is_file()
            and child.suffix in suffixes
            and ".git" not in child.parts
            and "__pycache__" not in child.parts
        )
    return sorted(set(files))


def test_docs_index_references_existing_files() -> None:
    index_text = (DOCS_ROOT / "README.md").read_text(encoding="utf-8")
    referenced = set(re.findall(r"`([^`]+\.md)`", index_text))
    for rel_path in sorted(referenced):
        if "*" in rel_path or "<" in rel_path:
            continue
        path = ROOT / rel_path if rel_path.startswith("docs/") else DOCS_ROOT / rel_path
        assert path.is_file(), f"missing docs reference: {rel_path}"


def test_docs_top_level_structure_is_explicit() -> None:
    actual = {path.name for path in DOCS_ROOT.iterdir() if not path.name.startswith(".")}
    assert actual == ALLOWED_DOCS_TOP_LEVEL


def test_banned_legacy_doc_roots_do_not_exist() -> None:
    existing = [path.relative_to(ROOT).as_posix() for path in BANNED_DOC_ROOTS if path.exists()]
    assert not existing


def test_source_docs_do_not_reference_banned_legacy_roots() -> None:
    failures: list[str] = []
    for path in _iter_text_files(DOC_STRUCTURE_SCANNED_ROOTS):
        if path in DOC_STRUCTURE_REFERENCE_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in BANNED_REFERENCE_FRAGMENTS:
            if fragment in text:
                failures.append(f"{path.relative_to(ROOT)} references banned path {fragment}")
    assert not failures, "\n".join(failures)


def test_retired_decimal_answer_schema_is_absent() -> None:
    """The registry answer schema is `number`; precision is separate metadata."""

    retired_schema = "_".join(("decimal", "value", "1dp"))
    scanned_roots = (
        ROOT / "docs",
        ROOT / "prompts",
        ROOT / "review" / "task-reviews",
        ROOT / "scripts",
        ROOT / "tests",
        ROOT / "trace",
    )
    failures: list[str] = []
    for path in _iter_text_files(scanned_roots):
        text = path.read_text(encoding="utf-8")
        if retired_schema in text:
            failures.append(f"{path.relative_to(ROOT)} references retired answer schema")
    assert not failures, "\n".join(failures)


def test_review_tree_does_not_contain_source_docs() -> None:
    review_root = ROOT / "review"
    if not review_root.exists():
        return
    banned_names = {"docs", "code-review", "taxonomy-audit", "trace-extension"}
    existing = [
        path.relative_to(ROOT).as_posix()
        for path in review_root.iterdir()
        if path.is_dir() and path.name in banned_names
    ]
    assert not existing


def test_each_registered_task_has_task_doc() -> None:
    for task_id in sorted(TASK_REGISTRY.keys()):
        task_doc = TASK_DOCS_ROOT / _task_doc_rel_path(task_id)
        assert task_doc.is_file(), f"missing task doc for task_id='{task_id}'"


def test_task_doc_files_match_registry() -> None:
    expected_links = {_task_doc_rel_path(task_id) for task_id in TASK_REGISTRY.keys()}

    task_doc_files = {
        path.relative_to(TASK_DOCS_ROOT)
        for path in TASK_DOCS_ROOT.rglob("task_*.md")
        if path.name not in {"README.md", "TASK_DOC_TEMPLATE.md"}
    }
    assert task_doc_files == expected_links


def test_task_docs_reference_existing_local_files() -> None:
    failures: list[str] = []
    for path in TASK_DOCS_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in TASK_DOC_LOCAL_REF_RE.finditer(text):
            rel_path = match.group(1)
            if not (ROOT / rel_path).exists():
                failures.append(f"{path.relative_to(ROOT)} references missing local file {rel_path}")
    assert not failures, "\n".join(failures)


def test_task_docs_do_not_repeat_adjacent_scene_id_rows() -> None:
    failures: list[str] = []
    for path in TASK_DOCS_ROOT.rglob("*.md"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines[:-1]):
            next_line = lines[index + 1]
            if line.startswith("2. Scene id:") and next_line.startswith("3. Scene id:"):
                failures.append(f"{path.relative_to(ROOT)} repeats adjacent Scene id rows")
                break
    assert not failures, "\n".join(failures)


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


def test_benchmark_coverage_scripts_reference_active_tasks() -> None:
    active_task_ids = set(TASK_REGISTRY.keys())
    failures: list[str] = []
    for path in BENCHMARK_COVERAGE_SCRIPT_PATHS:
        text = path.read_text(encoding="utf-8")
        for task_id in sorted(set(TASK_ID_RE.findall(text)) - active_task_ids):
            failures.append(f"{path.relative_to(ROOT)} references inactive task id {task_id}")
    assert not failures, "\n".join(failures)


def test_code_review_guidelines_required_sections_are_present() -> None:
    path = DOCS_ROOT / "workflows" / "CODE_REVIEW_GUIDELINES.md"
    text = path.read_text(encoding="utf-8")
    for heading in (
        "## Read First",
        "## Core Checklist",
        "## Scene-Package Migration Red Flags",
        "## Handoff",
    ):
        assert heading in text

    for heading in ("Core Checklist", "Scene-Package Migration Red Flags", "Handoff"):
        match = re.search(rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)", text, flags=re.M | re.S)
        assert match is not None
        numbers = [int(value) for value in re.findall(r"^(\d+)\. ", match.group("body"), flags=re.M)]
        assert numbers == list(range(1, len(numbers) + 1))
