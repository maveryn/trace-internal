#!/usr/bin/env python3
"""Check repo-local skill files against the active TRACE domain surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

import trace.tasks  # noqa: F401 - register task classes before registry checks.
from trace.core.taxonomy import ACTIVE_DOMAINS
from trace.tasks.registry import list_default_task_ids


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
STALE_SKILL_REFERENCES = ("docs/project/",)

DOMAIN_SETUP_DOCS = {
    "charts": "docs/domains/charts.md",
    "games": "docs/domains/games.md",
    "geometry": "docs/domains/geometry.md",
    "graph": "docs/domains/graph.md",
    "icons": "docs/domains/icons.md",
    "illustrations": "docs/domains/illustrations.md",
    "pages": "docs/domains/pages.md",
    "physics": "docs/domains/physics.md",
    "symbolic": "docs/domains/symbolic.md",
    "puzzles": "docs/domains/puzzles.md",
    "three_d": "docs/domains/three_d.md",
}

REQUIRED_DOMAIN_SECTIONS = (
    "## Read first",
    "## Active-contract reminders",
    "## Practical review checklist",
)
NON_DOMAIN_SKILL_DIRS = {"domain-audit"}
TASK_ID_RE = re.compile(r"\btask_[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+\b")


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

    for path in sorted(SKILLS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for stale_ref in STALE_SKILL_REFERENCES:
            if stale_ref in text:
                failures.append(
                    SkillConsistencyFailure(
                        "stale_skill_reference",
                        f"{path.relative_to(REPO_ROOT)} references {stale_ref}",
                    )
                )
        missing_task_ids = sorted(set(TASK_ID_RE.findall(text)) - active_task_ids)
        if missing_task_ids:
            failures.append(
                SkillConsistencyFailure(
                    "skill_inactive_task_id_reference",
                    f"{path.relative_to(REPO_ROOT)} references inactive task ids: {', '.join(missing_task_ids[:20])}",
                )
            )

    active_domains = set(ACTIVE_DOMAINS)
    expected_domain_dirs = {f"domain-{domain}" for domain in active_domains}
    actual_domain_dirs = {
        path.name
        for path in SKILLS_ROOT.glob("domain-*")
        if path.is_dir() and path.name not in NON_DOMAIN_SKILL_DIRS
    }

    missing_domain_dirs = sorted(expected_domain_dirs - actual_domain_dirs)
    if missing_domain_dirs:
        failures.append(SkillConsistencyFailure("domain_skills_missing", ", ".join(missing_domain_dirs)))

    extra_domain_dirs = sorted(actual_domain_dirs - expected_domain_dirs)
    if extra_domain_dirs:
        failures.append(SkillConsistencyFailure("domain_skills_extra", ", ".join(extra_domain_dirs)))

    for domain in sorted(active_domains):
        skill_path = SKILLS_ROOT / f"domain-{domain}" / "SKILL.md"
        if not skill_path.is_file():
            failures.append(
                SkillConsistencyFailure("domain_skill_file_missing", str(skill_path.relative_to(REPO_ROOT)))
            )
            continue

        text = skill_path.read_text(encoding="utf-8")
        if f"domain={domain}" not in text:
            failures.append(
                SkillConsistencyFailure(
                    "domain_skill_domain_marker_missing",
                    f"{skill_path.relative_to(REPO_ROOT)} does not mention domain={domain}",
                )
            )

        setup_doc = DOMAIN_SETUP_DOCS[domain]
        if setup_doc not in text:
            failures.append(
                SkillConsistencyFailure(
                    "domain_skill_setup_doc_missing",
                    f"{skill_path.relative_to(REPO_ROOT)} does not reference {setup_doc}",
                )
            )

        if "docs/ACTIVE_TASK_INVENTORY.md" not in text:
            failures.append(
                SkillConsistencyFailure(
                    "domain_skill_inventory_doc_missing",
                    f"{skill_path.relative_to(REPO_ROOT)} does not reference docs/ACTIVE_TASK_INVENTORY.md",
                )
            )

        for section in REQUIRED_DOMAIN_SECTIONS:
            if section not in text:
                failures.append(
                    SkillConsistencyFailure(
                        "domain_skill_required_section_missing",
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
