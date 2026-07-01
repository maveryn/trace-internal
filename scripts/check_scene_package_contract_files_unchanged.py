#!/usr/bin/env python3
"""Fail if scene-package migration contract files changed in this worktree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROTECTED_CONTRACT_FILES = (
    "scripts/check_scene_package_contract_files_unchanged.py",
    "tests/test_scene_package_migration_contracts.py",
    "trace/core/scene_package_file_policies.py",
    "trace/core/scene_package_migration.py",
    "docs/SCENE_PACKAGE_MIGRATION",
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    commands = (
        ["git", "diff", "--name-only", "--", *PROTECTED_CONTRACT_FILES],
        ["git", "diff", "--cached", "--name-only", "--", *PROTECTED_CONTRACT_FILES],
        ["git", "ls-files", "--others", "--exclude-standard", "--", *PROTECTED_CONTRACT_FILES],
    )
    changed: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=repo_root, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            return int(result.returncode)
        changed.update(line.strip() for line in result.stdout.splitlines() if line.strip())
    if changed:
        sys.stderr.write(
            "Scene-package migration contract files changed in this worktree. "
            "Do not edit migration tests, policies, registries, or contract docs "
            "during scene migration without explicit user approval:\n"
        )
        for path in sorted(changed):
            sys.stderr.write(f"  {path}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
