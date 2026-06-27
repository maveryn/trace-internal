#!/usr/bin/env python3
"""Audit modulo use in visual candidate-set and attribute assignment code."""

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

WINDOW_SIZE = 5
MODULO_PATTERN = re.compile(r"%\s*len\s*\(")
RESOLVE_SELECTION_PATTERN = re.compile(r"\bresolve_selection_index\s*\(")

VISUAL_TERMS = (
    "accent",
    "color",
    "fill",
    "font",
    "icon",
    "kind",
    "label",
    "marker",
    "option",
    "palette",
    "pattern",
    "rgb",
    "shape",
    "stroke",
    "style",
    "symbol",
    "texture",
    "theme",
    "title",
)

RANDOM_SELECTION_TERMS = (
    "_sample_cursor",
    "branch_index",
    "choice(",
    "hash64",
    "instance_seed",
    "randrange",
    "random(",
    "resolve_selection_index",
    "rng.",
    "sample(",
    "sampling_index",
    "shuffle(",
    "spawn_rng",
)

ASSIGNMENT_TERMS = (
    "bin_index",
    "category_index",
    "color_index",
    "enumerate(",
    "heat_level",
    "index",
    "label_index",
    "pit_index",
    "region_index",
    "series_index",
    "state",
)

SAFE_PATH_PARTS = (
    "review_overlays.py",
    "/rendering.py",
)

NON_VISUAL_SOURCE_RULES: tuple[tuple[str, str], ...] = (
    (
        "trace/tasks/charts/part_whole/shared/sampling.py",
        r"%\s*len\(categories\)",
    ),
    (
        "trace/tasks/charts/treemap/repeated_leaf_aggregate_value.py",
        r"total\s*%\s*len\(matching\)\s*!=\s*0",
    ),
    (
        "trace/tasks/games/ludo_board/capture_roll_option_label.py",
        r"target_index\s*=\s*\(mover_index\s*\+\s*distance\)\s*%\s*len\(MAIN_PATH\)",
    ),
    (
        "trace/tasks/games/mancala_pit_board/sowing_landing_option_label.py",
        r"source_index\s*=\s*\(int\(target_index\)\s*-\s*int\(source_seed_count\)\)\s*%\s*len\(LABELS\)",
    ),
    (
        "trace/tasks/games/mancala_pit_board/shared/rules.py",
        r"return\s+str\(LABELS\[int\(index\)\s*%\s*len\(LABELS\)\]\)",
    ),
)

SAFE_SOURCE_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "trace/tasks/charts/surface_3d/",
        r"color_rgb\s*=\s*PALETTE\[.*%\s*len\(PALETTE\)",
        "deterministic surface-series palette assignment",
    ),
)


@dataclass(frozen=True)
class VisualModuloSite:
    """One visual modulo/cycling site."""

    path: Path
    line: int
    category: str
    reason: str
    snippet: str
    context: str


def _readable_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _context(lines: Sequence[str], index: int) -> str:
    start = max(0, int(index) - WINDOW_SIZE)
    end = min(len(lines), int(index) + WINDOW_SIZE + 1)
    return "\n".join(line.strip() for line in lines[start:end] if line.strip())


def _has_any(text: str, terms: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _classify(path: Path, snippet: str, context: str) -> tuple[str, str] | None:
    haystack = f"{_readable_path(path)}\n{snippet}\n{context}".lower()
    path_text = _readable_path(path)
    for path_part, pattern in NON_VISUAL_SOURCE_RULES:
        if str(path_part) in path_text and re.search(str(pattern), snippet):
            return None
    if not _has_any(haystack, VISUAL_TERMS):
        return None

    # Use the actual candidate line for random-selector detection. Surrounding
    # context often contains legitimate RNG setup for a later non-modulo shuffle.
    random_selector = _has_any(snippet, RANDOM_SELECTION_TERMS)
    assignment_like = _has_any(haystack, ASSIGNMENT_TERMS)

    for path_part, pattern, reason in SAFE_SOURCE_RULES:
        if str(path_part) in path_text and re.search(str(pattern), snippet):
            return (
                "likely_safe_deterministic_assignment",
                str(reason),
            )
    if random_selector:
        return (
            "random_candidate_selection_needs_refactor",
            "visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo",
        )
    if "/sampling.py" in path_text or "/_lifecycle.py" in path_text:
        return (
            "sampling_assignment_needs_review",
            "sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first",
        )
    if any(part in path_text for part in SAFE_PATH_PARTS) and assignment_like:
        return (
            "likely_safe_deterministic_assignment",
            "render/review code cycles through an already-selected palette or repeated style list",
        )
    return (
        "needs_manual_review",
        "visual modulo found, but candidate-set vs assignment role is unclear",
    )


def scan_source_text(path: Path, text: str) -> list[VisualModuloSite]:
    """Scan one Python file for visual modulo/cycling sites."""

    sites: list[VisualModuloSite] = []
    lines = text.splitlines()
    for index, line_text in enumerate(lines):
        stripped = line_text.strip()
        if not stripped or stripped.startswith("#"):
            continue
        context = _context(lines, index)
        has_modulo = bool(MODULO_PATTERN.search(stripped))
        has_resolve_selection_modulo = bool(RESOLVE_SELECTION_PATTERN.search(stripped)) and bool(
            MODULO_PATTERN.search(context)
        )
        if not has_modulo and not has_resolve_selection_modulo:
            continue
        classified = _classify(path, stripped, context)
        if classified is None:
            continue
        category, reason = classified
        sites.append(
            VisualModuloSite(
                path=path,
                line=int(index) + 1,
                category=category,
                reason=reason,
                snippet=stripped,
                context=context,
            )
        )
    return sites


def iter_python_files(roots: Iterable[Path]) -> list[Path]:
    """Return sorted Python files below the requested roots."""

    files: list[Path] = []
    for root in roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.suffix == ".py":
            files.append(root_path)
            continue
        if not root_path.exists():
            continue
        files.extend(path for path in root_path.rglob("*.py") if path.is_file())
    return sorted(set(files), key=lambda path: _readable_path(path))


def scan_paths(paths: Iterable[Path]) -> list[VisualModuloSite]:
    """Scan all requested paths."""

    sites: list[VisualModuloSite] = []
    for path in iter_python_files(paths):
        sites.extend(scan_source_text(path, path.read_text(encoding="utf-8")))
    priority = {
        "random_candidate_selection_needs_refactor": 0,
        "sampling_assignment_needs_review": 1,
        "needs_manual_review": 2,
        "likely_safe_deterministic_assignment": 3,
    }
    return sorted(
        sites,
        key=lambda site: (priority.get(site.category, 99), _readable_path(site.path), site.line),
    )


def _markdown_section(title: str, sites: Sequence[VisualModuloSite]) -> list[str]:
    lines = [f"## {title}", ""]
    if not sites:
        lines.extend(["None found.", ""])
        return lines
    lines.extend(
        [
            "| File | Line | Reason | Snippet |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for site in sites:
        snippet = site.snippet.replace("|", "\\|")
        lines.append(
            f"| `{_readable_path(site.path)}` | {site.line} | "
            f"{site.reason} | `{snippet}` |"
        )
    lines.append("")
    return lines


def render_markdown(sites: Sequence[VisualModuloSite]) -> str:
    """Render a visual modulo audit report."""

    categories = {
        "random_candidate_selection_needs_refactor": [
            site for site in sites if site.category == "random_candidate_selection_needs_refactor"
        ],
        "sampling_assignment_needs_review": [
            site for site in sites if site.category == "sampling_assignment_needs_review"
        ],
        "needs_manual_review": [
            site for site in sites if site.category == "needs_manual_review"
        ],
        "likely_safe_deterministic_assignment": [
            site for site in sites if site.category == "likely_safe_deterministic_assignment"
        ],
    }
    lines = [
        "# Visual Candidate-Set Modulo Audit",
        "",
        "This report audits modulo use around visual attributes such as colors, "
        "styles, labels, shapes, themes, symbols, and option layouts. Random "
        "candidate-set selection should use RNG sampling from an explicit support "
        "or range. Modulo is acceptable only for deterministic assignment from an "
        "already-selected list or for intentional repeat cycling.",
        "",
        "## Summary",
        "",
        f"- Total visual modulo sites: {len(sites)}",
        "- Random candidate selection needs refactor: "
        f"{len(categories['random_candidate_selection_needs_refactor'])}",
        "- Sampling-time assignment needs review: "
        f"{len(categories['sampling_assignment_needs_review'])}",
        f"- Needs manual review: {len(categories['needs_manual_review'])}",
        "- Likely safe deterministic assignment: "
        f"{len(categories['likely_safe_deterministic_assignment'])}",
        "",
    ]
    lines.extend(
        _markdown_section(
            "Random Candidate Selection Needs Refactor",
            categories["random_candidate_selection_needs_refactor"],
        )
    )
    lines.extend(
        _markdown_section(
            "Sampling-Time Assignment Needs Review",
            categories["sampling_assignment_needs_review"],
        )
    )
    lines.extend(
        _markdown_section(
            "Needs Manual Review",
            categories["needs_manual_review"],
        )
    )
    lines.extend(
        _markdown_section(
            "Likely Safe Deterministic Assignment",
            categories["likely_safe_deterministic_assignment"],
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
