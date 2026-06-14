#!/usr/bin/env python3
"""Check repo-local skills stay thin workflow overlays."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

from trace.tasks.registry import list_default_task_ids


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
RETAINED_SKILL_DIRS = {
    "code-review",
    "prompt-design",
    "task-design",
    "task-implementation",
    "task-unit-audit",
    "verification-review",
}
REQUIRED_WORKFLOW_SECTIONS = (
    "## Read first",
    "## Handoff",
)
TASK_ID_RE = re.compile(r"\btask_[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+\b")
DOC_PATH_RE = re.compile(r"`(docs/[^`]+\.md)`")
BANNED_REFERENCE_PARTS = (
    ("docs", "core"),
    ("docs", "project"),
    ("plans",),
    ("review", "docs"),
    ("review", "code-review"),
    ("review", "taxonomy-audit"),
    ("review", "trace-extension"),
)
BANNED_REFERENCE_FRAGMENTS = tuple(
    "/".join(parts) + "/" for parts in BANNED_REFERENCE_PARTS
) + ("skills/" + "domain-",)


@dataclass(frozen=True)
class SkillConsistencyFailure:
    """One skill-consistency failure."""

    check: str
    message: str

    def format(self) -> str:
        return f"{self.check}: {self.message}"


def collect_skill_consistency_failures() -> list[SkillConsistencyFailure]:
    """Return skill-folder consistency failures."""

    failures: list[SkillConsistencyFailure] = []
    active_task_ids = set(list_default_task_ids())

    if not (SKILLS_ROOT / "README.md").is_file():
        failures.append(SkillConsistencyFailure("skills_readme_missing", "skills/README.md is missing"))

    skill_dirs = {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()}
    extra_skill_dirs = sorted(skill_dirs - RETAINED_SKILL_DIRS)
    if extra_skill_dirs:
        failures.append(SkillConsistencyFailure("skill_dirs_extra", ", ".join(extra_skill_dirs)))

    missing_skill_dirs = sorted(RETAINED_SKILL_DIRS - skill_dirs)
    if missing_skill_dirs:
        failures.append(SkillConsistencyFailure("skill_dirs_missing", ", ".join(missing_skill_dirs)))

    for path in sorted(SKILLS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        missing_task_ids = sorted(set(TASK_ID_RE.findall(text)) - active_task_ids)
        if missing_task_ids:
            failures.append(
                SkillConsistencyFailure(
                    "skill_inactive_task_id_reference",
                    f"{path.relative_to(REPO_ROOT)} references inactive task ids: {', '.join(missing_task_ids[:20])}",
                )
            )

        for fragment in BANNED_REFERENCE_FRAGMENTS:
            if fragment in text:
                failures.append(
                    SkillConsistencyFailure(
                        "skill_banned_reference",
                        f"{path.relative_to(REPO_ROOT)} references banned fragment {fragment}",
                    )
                )

        for doc_ref in sorted(set(DOC_PATH_RE.findall(text))):
            if "<" in doc_ref or "*" in doc_ref:
                continue
            if not (REPO_ROOT / doc_ref).is_file():
                failures.append(
                    SkillConsistencyFailure(
                        "skill_doc_reference_missing",
                        f"{path.relative_to(REPO_ROOT)} references missing {doc_ref}",
                    )
                )

    for skill_dir in sorted(RETAINED_SKILL_DIRS):
        skill_path = SKILLS_ROOT / skill_dir / "SKILL.md"
        if not skill_path.is_file():
            failures.append(
                SkillConsistencyFailure("workflow_skill_file_missing", str(skill_path.relative_to(REPO_ROOT)))
            )
            continue

        text = skill_path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            failures.append(
                SkillConsistencyFailure(
                    "workflow_skill_frontmatter_missing",
                    f"{skill_path.relative_to(REPO_ROOT)} is missing front matter",
                )
            )

        for section in REQUIRED_WORKFLOW_SECTIONS:
            if section not in text:
                failures.append(
                    SkillConsistencyFailure(
                        "workflow_skill_required_section_missing",
                        f"{skill_path.relative_to(REPO_ROOT)} is missing {section}",
                    )
                )

    return failures


def main() -> int:
    failures = collect_skill_consistency_failures()
    if failures:
        for failure in failures:
            print(failure.format())
        return 1
    print("skill consistency OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
