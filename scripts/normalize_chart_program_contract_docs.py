#!/usr/bin/env python3
"""Normalize chart task-doc Program Contract sections.

This maintainer script rewrites only the ``## Program Contract`` block in
``docs/tasks/charts/**/*.md``. It preserves the existing concrete program
expression and expands it into the structured labels used by post-migration
taxonomy review.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable


REQUIRED_LABELS = (
    "Program:",
    "Candidate set:",
    "Operands:",
    "Operation:",
    "Output binding:",
    "Annotation witnesses:",
    "Query ids:",
)

SCENE_CANDIDATE_SETS: dict[str, str] = {
    "annotated_series": "the visible series marks and callout annotations",
    "area": "the visible area-series bands, category labels, and interval endpoints",
    "bar_3d": "the visible 3D bars grouped by category and series",
    "boxplot": "the visible boxplot glyphs and their group labels",
    "candlestick": "the visible candlestick glyphs and period/category labels",
    "combo_mark": "the visible primary marks, secondary-line marks, and shared category labels",
    "composition_panels": "the visible panel segments and panel/category labels",
    "contour_density": "the visible contour-density regions, guide labels, and marked areas",
    "curve_panels": "the visible curve panels, curve traces, points, and panel labels",
    "dashboard": "the visible dashboard panels, linked marks, and panel labels",
    "density_curve": "the visible density curves, shaded regions, and axis labels",
    "dumbbell": "the visible paired endpoint markers, connectors, and category labels",
    "error_interval": "the visible interval marks, reference lines, and category labels",
    "errorbar_series": "the visible error bars, series markers, and category labels",
    "heatmap": "the visible heatmap cells with row and column labels",
    "hexbin_density": "the visible hexagonal bins and density/value labels",
    "histogram": "the visible histogram bins and axis/value labels",
    "matrix": "the visible matrix cells with row and column labels",
    "multiseries": "the visible series marks across shared x/category labels",
    "parallel_coords": "the visible polylines, axes, and axis-value positions",
    "part_whole": "the visible part-whole segments, slices, and category labels",
    "pictogram": "the visible pictogram rows, repeated icons, and category labels",
    "population_pyramid": "the visible left/right population bars and age-group labels",
    "radar": "the visible radar spokes, profile polygons, and profile labels",
    "radial_progress": "the visible radial progress rings, arcs, and labels",
    "radial_sankey": "the visible radial flow nodes, links, and labels",
    "region_map": "the visible map regions, region labels, and legend/value encodings",
    "sankey": "the visible flow nodes, links, and labels",
    "scatter_cluster": "the visible scatter points, clusters, and cluster labels",
    "scatter_points": "the visible scatter points and axis/value labels",
    "scatter_readout": "the visible scatter points, readout markers, and axis labels",
    "scientific_axis_frame": "the visible scientific-axis ticks, marked points, and scale labels",
    "single_series": "the visible marks in the ordered single-series chart",
    "size_encoding": "the visible items whose size encodes value and their category labels",
    "style_legend": "the visible plotted series/marks and legend entries",
    "sunburst": "the visible hierarchy wedges, rings, and node labels",
    "surface_3d": "the visible 3D surface samples, grid lines, and axis labels",
    "table": "the visible table cells with row and column labels",
    "treemap": "the visible treemap rectangles and hierarchy labels",
    "uncertainty_band": "the visible uncertainty bands, central series marks, and x labels",
    "violin": "the visible violin glyphs, summary markers, and group labels",
    "waterfall": "the visible waterfall bars, contribution steps, and total bars",
}


def _extract_section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*(.*?)(?:^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return ""
    return match.group(1).strip()


def _extract_program_expression(program_body: str) -> str:
    code_match = re.search(r"`([^`]*scene=[^`]*)`", program_body, flags=re.DOTALL)
    if code_match is not None:
        return " ".join(code_match.group(1).split())

    program_match = re.search(r"^Program:\s*`?(.+?)`?\s*$", program_body, flags=re.MULTILINE)
    if program_match is not None:
        return " ".join(program_match.group(1).split())

    for line in program_body.splitlines():
        stripped = line.strip().strip("`")
        if stripped:
            return " ".join(stripped.split())
    return ""


def _extract_field_from_program(program: str, field: str) -> str:
    match = re.search(rf"(?:^|;)\s*{re.escape(field)}=([^;]+)", program)
    if match is None:
        return ""
    return match.group(1).strip()


def _program_operation_name(program: str) -> str:
    first_clause = program.split(";", 1)[0].strip()
    if "(" in first_clause:
        return first_clause.split("(", 1)[0].strip()
    return first_clause or "chart_program"


def _schema_from_annotation_contract(section: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*`([^`]+)`", section)
    if match is not None:
        return match.group(1).strip()
    match = re.search(rf"{re.escape(label)}:\s*([A-Za-z0-9_]+)", section)
    if match is not None:
        return match.group(1).strip().rstrip(".")
    return "unspecified"


def _annotation_witness_notes(section: str) -> str:
    bullets = re.findall(r"^\d+\.\s+(.+)$", section, flags=re.MULTILINE)
    notes: list[str] = []
    for bullet in bullets:
        if bullet.startswith("Answer schema:") or bullet.startswith("Annotation schema:"):
            continue
        notes.append(bullet.strip())
    if not notes:
        return "The Annotation Contract below defines the prompt-facing witnesses."
    return " ".join(notes[:3])


def _query_ids_from_table(text: str) -> list[str]:
    section = _extract_section(text, "Query Details")
    query_ids: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if first.lower() in {"query id", "---"} or set(first) <= {"-", ":"}:
            continue
        if first.startswith("`") and first.endswith("`"):
            query_ids.append(first.strip("`"))
    return _dedupe(query_ids)


def _query_ids_from_contract(text: str) -> list[str]:
    ids: list[str] = []
    for pattern in (
        r"(?:Supported\s+)?`query_id`\s+values:\s*([^\n]+)",
        r"(?:Supported\s+)?query ids?:\s*([^\n]+)",
        r"Public query id:\s*([^\n]+)",
        r"Query ids:\s*([^\n]+)",
    ):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            line = match.group(1)
            ids.extend(re.findall(r"`([^`]+)`", line))
            if not ids and "single" in line:
                ids.append("single")
    return _dedupe(ids)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _query_id_text(text: str) -> str:
    query_ids = _query_ids_from_table(text) or _query_ids_from_contract(text) or ["single"]
    return ", ".join(f"`{query_id}`" for query_id in query_ids)


def _build_structured_program_contract(path: Path, text: str, program_body: str) -> str:
    scene_id = path.parent.name
    program = _extract_program_expression(program_body)
    if not program:
        raise ValueError(f"{path}: cannot find concrete program expression")

    annotation_section = _extract_section(text, "Annotation Contract")
    answer_schema = _schema_from_annotation_contract(annotation_section, "Answer schema")
    annotation_schema = _schema_from_annotation_contract(annotation_section, "Annotation schema")
    annotation_expr = _extract_field_from_program(program, "annotation") or "see_annotation_contract"
    output_expr = _extract_field_from_program(program, "output") or answer_schema
    scope = _extract_field_from_program(program, "scope") or path.stem.removeprefix("task_charts__").split("__")[-1]
    operation_name = _program_operation_name(program)
    candidates = SCENE_CANDIDATE_SETS.get(scene_id, f"the visible chart elements in the `{scene_id}` scene")
    query_ids = _query_id_text(text)
    query_phrase = (
        "the active query id's comparator, direction, target role, or extremum focus"
        if "," in query_ids
        else "the task's prompt-bound target operands"
    )

    return "\n".join(
        [
            f"Program: `{program}`",
            "",
            f"Candidate set: {candidates} inside the `{scope}` objective scope.",
            (
                "Operands: prompt-bound labels, categories, series names, thresholds, intervals, references, "
                f"and encoded chart values, plus {query_phrase} when present."
            ),
            (
                f"Operation: evaluate `{operation_name}` over the candidate set using the filters, comparisons, "
                "aggregations, rankings, projections, or counterfactual edits named in the program expression; "
                "generation enforces a unique final answer."
            ),
            f"Output binding: `answer` is the `{answer_schema}` value bound by `{output_expr}`.",
            (
                f"Annotation witnesses: `{annotation_schema}` witnesses bound by `{annotation_expr}`. "
                f"{_annotation_witness_notes(annotation_section)}"
            ),
            f"Query ids: {query_ids}.",
        ]
    )


def _program_contract_match(text: str) -> re.Match[str] | None:
    return re.search(r"^## Program Contract[ \t]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)


def _normalize_text(path: Path, text: str) -> tuple[str, bool]:
    match = _program_contract_match(text)
    if match is None:
        raise ValueError(f"{path}: missing ## Program Contract")
    body = match.group(1).strip()
    structured = _build_structured_program_contract(path, text, body)
    replacement = "\n" + structured.rstrip() + "\n\n"
    normalized = text[: match.start(1)] + replacement + text[match.end(1) :].lstrip("\n")
    return normalized, normalized != text


def _missing_required_labels(text: str) -> list[str]:
    match = _program_contract_match(text)
    if match is None:
        return list(REQUIRED_LABELS)
    body = match.group(1)
    return [label for label in REQUIRED_LABELS if label not in body]


def _iter_docs(root: Path) -> list[Path]:
    return sorted(root.glob("*/*.md"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("docs/tasks/charts"))
    parser.add_argument("--write", action="store_true", help="Rewrite docs in place")
    parser.add_argument("--check", action="store_true", help="Fail if docs are not normalized")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    docs = _iter_docs(args.root)
    changed: list[Path] = []
    errors: list[str] = []

    for path in docs:
        try:
            text = path.read_text(encoding="utf-8")
            normalized, did_change = _normalize_text(path, text)
            if did_change:
                changed.append(path)
                if args.write:
                    path.write_text(normalized, encoding="utf-8")
            missing = _missing_required_labels(normalized if args.write else text)
            if missing:
                errors.append(f"{path}: missing {', '.join(missing)}")
        except Exception as exc:  # noqa: BLE001 - maintenance script should report all doc failures.
            errors.append(str(exc))

    print(f"chart task docs scanned: {len(docs)}")
    print(f"docs requiring normalization: {len(changed)}")
    if args.write:
        print(f"docs rewritten: {len(changed)}")
    if errors:
        print("program contract structural failures:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if args.check and changed:
        print("chart Program Contract docs are not normalized; rerun with --write", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
