#!/usr/bin/env python3
"""Audit seed/index modulo patterns that may be semantic sampling bugs."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_ROOTS = (
    Path("trace/tasks"),
    Path("trace/core"),
)

SCAN_SUFFIXES = (".py",)
WINDOW_SIZE = 6

MODULO_PATTERNS = (
    re.compile(r"\binstance_seed\s*%"),
    re.compile(r"%\s*len\s*\("),
    re.compile(r"\bcursor\s*%\s*len\s*\("),
)
RESOLVE_SELECTION_PATTERN = re.compile(r"\bresolve_selection_index\s*\(")

SEMANTIC_TERMS = (
    "answer",
    "branch",
    "case",
    "choice",
    "class",
    "construction",
    "correct",
    "count",
    "family",
    "query",
    "relation",
    "sample",
    "sampling",
    "scene_variant",
    "selected",
    "selection",
    "support",
    "target",
    "variant",
    "weight",
)

ALLOWED_TERMS = (
    "annotation_color",
    "bbox",
    "belt_sequence",
    "color =",
    "color",
    "cyclic",
    "distractor_index",
    "edge",
    "idx",
    "index +",
    "label",
    "line_colors",
    "option_list",
    "palette",
    "point",
    "polygon",
    "review_overlay",
    "template",
    "vertex",
    "vertices",
)

ALLOWED_PATH_PARTS = (
    "review_overlays.py",
    "prompt_json_example.py",
    "render_variation.py",
    "/rendering.py",
)

ALLOWED_SOURCE_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "trace/tasks/charts/part_whole/shared/sampling.py",
        r"%\s*len\(categories\)",
        "circular part-whole category traversal, not random sampling",
    ),
    (
        "trace/tasks/charts/surface_3d/",
        r"color_rgb\s*=\s*PALETTE\[.*%\s*len\(PALETTE\)",
        "deterministic surface-series palette assignment, not random sampling",
    ),
    (
        "trace/tasks/charts/treemap/repeated_leaf_aggregate_value.py",
        r"total\s*%\s*len\(matching\)\s*!=\s*0",
        "integer divisibility validation, not random sampling",
    ),
    (
        "trace/tasks/games/ludo_board/capture_roll_option_label.py",
        r"target_index\s*=\s*\(mover_index\s*\+\s*distance\)\s*%\s*len\(MAIN_PATH\)",
        "Ludo token movement wraps around the circular main path",
    ),
    (
        "trace/tasks/games/mancala_pit_board/sowing_landing_option_label.py",
        r"source_index\s*=\s*\(int\(target_index\)\s*-\s*int\(source_seed_count\)\)\s*%\s*len\(LABELS\)",
        "Mancala reverse sowing uses circular pit topology",
    ),
)

REVIEW_STRATIFICATION_PATH_PARTS = (
    "task_review_sampling.py",
)

CATEGORY_PRIORITY = {
    "needs_refactor": 0,
    "needs_manual_review": 1,
    "review_stratification_or_round_robin": 2,
    "allowed_deterministic_enumeration": 3,
}


@dataclass(frozen=True)
class Finding:
    """One modulo/cycling pattern found in source."""

    path: Path
    line: int
    category: str
    kind: str
    snippet: str
    reason: str


@dataclass(frozen=True)
class SelectionSite:
    """One grouped modulo/cycling selection site."""

    path: Path
    start_line: int
    end_line: int
    category: str
    kind: str
    snippets: tuple[str, ...]
    reason: str
    raw_findings: int


def _readable_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _context(lines: Sequence[str], index: int) -> str:
    start = max(0, int(index) - WINDOW_SIZE)
    end = min(len(lines), int(index) + WINDOW_SIZE + 1)
    return "\n".join(line.strip() for line in lines[start:end])


def _line_category(path: Path, line_text: str, context: str) -> tuple[str, str]:
    """Classify one candidate as must-fix, allowed, or manual-review."""

    path_text = _readable_path(path)
    if any(part in path_text for part in REVIEW_STRATIFICATION_PATH_PARTS):
        return (
            "review_stratification_or_round_robin",
            "review harness deterministic coverage, not task random sampling",
        )
    if any(part in path_text for part in ALLOWED_PATH_PARTS):
        return (
            "allowed_deterministic_enumeration",
            "path is known rendering/review/example enumeration code",
        )
    for path_part, pattern, reason in ALLOWED_SOURCE_RULES:
        if str(path_part) in path_text and re.search(str(pattern), line_text):
            return (
                "allowed_deterministic_enumeration",
                str(reason),
            )
    source_haystack = f"{line_text}\n{context}".lower()
    if any(term in source_haystack for term in ALLOWED_TERMS) and not any(
        term in source_haystack
        for term in ("answer", "correct", "query", "target", "support")
    ):
        return (
            "allowed_deterministic_enumeration",
            "context looks like cyclic visual/layout enumeration",
        )
    if any(term in source_haystack for term in SEMANTIC_TERMS):
        return (
            "needs_refactor",
            "semantic sampling should use explicit support/range weights, not modulo cycling",
        )
    return (
        "needs_manual_review",
        "modulo/index cycling found but semantic role is unclear",
    )


def scan_source_text(path: Path, text: str) -> list[Finding]:
    """Scan source text for modulo/index sampling patterns."""

    findings: list[Finding] = []
    lines = text.splitlines()
    seen: set[tuple[int, str]] = set()
    for index, line_text in enumerate(lines):
        stripped = line_text.strip()
        if not stripped or stripped.startswith("#"):
            continue
        kinds: list[str] = []
        if any(pattern.search(stripped) for pattern in MODULO_PATTERNS):
            kinds.append("modulo_index")
        if RESOLVE_SELECTION_PATTERN.search(stripped):
            window = _context(lines, index)
            if re.search(r"%\s*len\s*\(", window):
                kinds.append("resolve_selection_index_modulo")
        for kind in kinds:
            key = (int(index) + 1, str(kind))
            if key in seen:
                continue
            seen.add(key)
            context = _context(lines, index)
            category, reason = _line_category(path, stripped, context)
            findings.append(
                Finding(
                    path=path,
                    line=int(index) + 1,
                    category=category,
                    kind=str(kind),
                    snippet=stripped,
                    reason=reason,
                )
            )
    return findings


def iter_python_files(roots: Iterable[Path]) -> list[Path]:
    """Return sorted Python files below the requested roots."""

    files: list[Path] = []
    for root in roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.suffix in SCAN_SUFFIXES:
            files.append(root_path)
            continue
        if not root_path.exists():
            continue
        files.extend(path for path in root_path.rglob("*.py") if path.is_file())
    return sorted(set(files), key=lambda path: _readable_path(path))


def scan_paths(paths: Iterable[Path]) -> list[Finding]:
    """Scan all files and return findings."""

    findings: list[Finding] = []
    for path in iter_python_files(paths):
        findings.extend(scan_source_text(path, path.read_text(encoding="utf-8")))
    return sorted(
        findings,
        key=lambda item: (item.category, _readable_path(item.path), item.line),
    )


def _site_kind(findings: Sequence[Finding]) -> str:
    kinds = {finding.kind for finding in findings}
    snippets = "\n".join(finding.snippet for finding in findings)
    if "resolve_selection_index_modulo" in kinds:
        return "resolve_selection_index_support_modulo"
    if "hash64" in snippets:
        return "hash_support_modulo"
    if "instance_seed" in snippets:
        return "seed_support_modulo"
    if "cursor" in snippets or "_sample_cursor" in snippets:
        return "cursor_support_modulo"
    return "modulo_index"


def _site_category(findings: Sequence[Finding]) -> str:
    return min(
        (finding.category for finding in findings),
        key=lambda category: CATEGORY_PRIORITY.get(str(category), 99),
    )


def _site_reason(category: str) -> str:
    if category == "needs_refactor":
        return "replace with explicit support/range sampling and uniform or weighted RNG draw"
    if category == "review_stratification_or_round_robin":
        return "allowed only because this is explicit review/dataset coverage, not task randomness"
    if category == "allowed_deterministic_enumeration":
        return "allowed deterministic visual/layout/example enumeration"
    return "manual source review needed before deciding whether this is random sampling"


def group_findings(findings: Sequence[Finding]) -> list[SelectionSite]:
    """Group raw line findings into source-level selection sites."""

    by_path: dict[Path, list[Finding]] = {}
    for finding in findings:
        by_path.setdefault(finding.path, []).append(finding)

    sites: list[SelectionSite] = []
    for path, path_findings in by_path.items():
        ordered = sorted(path_findings, key=lambda finding: (finding.line, finding.kind))
        index = 0
        while index < len(ordered):
            current = ordered[index]
            group = [current]
            next_index = index + 1
            while next_index < len(ordered) and ordered[next_index].line == current.line:
                group.append(ordered[next_index])
                next_index += 1

            if any(finding.kind == "resolve_selection_index_modulo" for finding in group):
                scan_index = next_index
                while scan_index < len(ordered):
                    candidate = ordered[scan_index]
                    if candidate.line - current.line > WINDOW_SIZE:
                        break
                    if candidate.kind == "modulo_index" and candidate not in group:
                        group.append(candidate)
                        scan_index += 1
                        break
                    scan_index += 1
                next_index = scan_index if len(group) > 1 else next_index

            index = next_index

            category = _site_category(group)
            snippets = tuple(dict.fromkeys(finding.snippet for finding in group))
            sites.append(
                SelectionSite(
                    path=path,
                    start_line=min(finding.line for finding in group),
                    end_line=max(finding.line for finding in group),
                    category=category,
                    kind=_site_kind(group),
                    snippets=snippets,
                    reason=_site_reason(category),
                    raw_findings=len(group),
                )
            )

    return sorted(
        sites,
        key=lambda item: (CATEGORY_PRIORITY.get(item.category, 99), _readable_path(item.path), item.start_line),
    )


def _line_range(site: SelectionSite) -> str:
    if site.start_line == site.end_line:
        return str(int(site.start_line))
    return f"{int(site.start_line)}-{int(site.end_line)}"


def _markdown_section(title: str, sites: Sequence[SelectionSite]) -> list[str]:
    lines = [f"## {title}", ""]
    if not sites:
        lines.extend(["None found.", ""])
        return lines
    lines.extend(
        [
            "| File | Lines | Kind | Raw Lines | Reason | Snippets |",
            "| --- | ---: | --- | ---: | --- | --- |",
        ]
    )
    for site in sites:
        snippet = "<br>".join(site.snippets).replace("|", "\\|")
        lines.append(
            f"| `{_readable_path(site.path)}` | {_line_range(site)} | "
            f"{site.kind} | {site.raw_findings} | {site.reason} | `{snippet}` |"
        )
    lines.append("")
    return lines


def render_markdown(findings: Sequence[Finding]) -> str:
    """Render one first-pass audit report."""

    sites = group_findings(findings)
    by_category = {
        "needs_refactor": [
            site for site in sites if site.category == "needs_refactor"
        ],
        "needs_manual_review": [
            site for site in sites if site.category == "needs_manual_review"
        ],
        "review_stratification_or_round_robin": [
            site
            for site in sites
            if site.category == "review_stratification_or_round_robin"
        ],
        "allowed_deterministic_enumeration": [
            site for site in sites if site.category == "allowed_deterministic_enumeration"
        ],
    }
    lines = [
        "# Semantic Sampling Modulo Audit: First Pass",
        "",
        "This report flags source patterns where modulo/index cycling may be "
        "standing in for semantic random sampling. Task random sampling should "
        "draw from an explicit support or bounded range with uniform or weighted "
        "probabilities. It is a static first pass; each refactor site still "
        "needs source-level confirmation before editing.",
        "",
        "## Summary",
        "",
        f"- Raw line findings: {len(findings)}",
        f"- Grouped selection sites: {len(sites)}",
        f"- Needs refactor: {len(by_category['needs_refactor'])}",
        f"- Needs manual review: {len(by_category['needs_manual_review'])}",
        "- Review harness stratification / round-robin: "
        f"{len(by_category['review_stratification_or_round_robin'])}",
        "- Allowed deterministic visual/layout enumeration: "
        f"{len(by_category['allowed_deterministic_enumeration'])}",
        "",
    ]
    lines.extend(
        _markdown_section(
            "Needs Refactor",
            by_category["needs_refactor"],
        )
    )
    lines.extend(
        _markdown_section(
            "Needs Manual Review",
            by_category["needs_manual_review"],
        )
    )
    lines.extend(
        _markdown_section(
            "Review Harness Stratification / Round-Robin",
            by_category["review_stratification_or_round_robin"],
        )
    )
    lines.extend(
        _markdown_section(
            "Allowed Deterministic Visual/Layout Enumeration",
            by_category["allowed_deterministic_enumeration"],
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        default=None,
        help="Root file or directory to scan. May be repeated.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional markdown output path. Prints to stdout when omitted.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = [Path(value) for value in args.roots] if args.roots else list(DEFAULT_ROOTS)
    report = render_markdown(scan_paths(roots))
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
