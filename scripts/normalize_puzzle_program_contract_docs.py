#!/usr/bin/env python3
"""Normalize puzzle task-doc Program Contract sections.

This maintainer script rewrites only the ``## Program Contract`` block in
``docs/tasks/puzzles/**/*.md``. It preserves the existing concrete program
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
    "arithmetic_panel": "the visible arithmetic panels, numeric entries, operators, totals, and marked target cell/node/brick",
    "balance_scale": "the visible balance-scale panels, object symbols, object counts, side relations, and query markers",
    "cell_board": "the visible grid cells, cell colors/states, labels, walls, start/goal markers, and mirror or connectivity cues",
    "color_gradient": "the visible swatch sequence or swatch grid, missing/violating swatches, and labeled options or cells",
    "cube_net": "the visible cube-net faces, face colors/labels, marked face or edge, and labeled candidate options",
    "cyclic_order": "the visible cyclic-order tokens, reference loop, gap/swap markers, numbered positions, and labeled options",
    "matchstick": "the visible matchstick segments, digit/equation/lattice structure, segment labels, and labeled candidate options when present",
    "maze": "the visible maze cells, walls, start marker, exits, labels, and reachability/path structure",
    "nonogram": "the visible nonogram clues, row or grid cells, filled/empty states, and labeled candidate strips or grids",
    "pipe_flow": "the visible pipe tiles, pipe connectors, start/finish markers, misrotated or missing tile cue, and labeled options",
    "polyomino_assembly": "the visible polyomino cells, source/target/hole shapes, allowed transforms, and labeled candidate options",
    "raven_matrix": "the visible Raven matrix cells, visual features, missing-cell cue, rule-bearing rows/columns, and labeled candidate options",
    "rubiks_net": "the visible cube-net stickers, face labels, move sequence, target face/sticker cues, and labeled options",
    "sheet_transform": "the visible source sheet/fold/cut/overlay panels, marked cells or holes, and labeled result options",
    "star_battle": "the visible Star Battle grid, regions, clues, placed stars, scope markers, and labeled candidate cells",
    "sudoku": "the visible Sudoku grid, givens, filled values, marked cell, candidate values, and option labels when present",
    "tents": "the visible Tents grid, tree cells, tent cells, row/column clues, labels, and candidate or violating cell markers",
    "toggle_grid": "the visible start/target/result grids, toggle rule markers, switch cells, labels, and labeled grid options",
    "voxel_cube": "the visible voxel stack, unit cubes, projections, changed/reference stacks, and labeled candidate views",
    "word_search": "the visible letter grid, target or option words, candidate location/direction labels, and highlighted word path",
}


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _program_contract_match(text: str) -> re.Match[str] | None:
    return re.search(r"^## Program Contract[ \t]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)


def _text_without_program_contract(text: str) -> str:
    match = _program_contract_match(text)
    if match is None:
        return text
    return text[: match.start()] + text[match.end() :]


def _extract_program_expression(program_body: str) -> str:
    for pattern in (
        r"Program:\s*`([^`]+)`",
        r"Program schema:\s*`([^`]+)`",
        r"`([^`]*;\s*scene=[^`]*)`",
    ):
        match = re.search(pattern, program_body, flags=re.IGNORECASE | re.DOTALL)
        if match is not None:
            return " ".join(match.group(1).split())

    for line in program_body.splitlines():
        stripped = line.strip().strip("- ").strip("`")
        if stripped and "scene=" in stripped:
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
    return first_clause or "puzzle_program"


def _schema_from_text(text: str, names: Iterable[str], default: str) -> str:
    lowered_names = tuple(name.lower() for name in names)
    for line in text.splitlines():
        lower_line = line.lower()
        if not any(name in lower_line for name in lowered_names):
            continue
        assignment = re.search(r"(?:answer_gt\.type|annotation_gt\.type)\s*=?\s*([A-Za-z0-9_]+)", line)
        if assignment is not None:
            return assignment.group(1).strip().rstrip(".")
        backticked = re.findall(r"`([A-Za-z0-9_]+)`", line)
        if backticked:
            return backticked[-1].strip().rstrip(".")
        after_colon = re.search(r":\s*([A-Za-z0-9_]+)", line)
        if after_colon is not None:
            return after_colon.group(1).strip().rstrip(".")
    return default


def _infer_answer_schema(path: Path, program: str, note: str) -> str:
    objective = path.stem.rsplit("__", 1)[-1]
    operation = _program_operation_name(program)
    lowered = f"{objective} {operation} {note}".lower()
    if any(term in lowered for term in ("count", "value", "digit", "size", "length")):
        return "integer"
    if any(term in lowered for term in ("label", "option", "selected", "letter")):
        return "option_letter"
    return "unspecified"


def _infer_annotation_schema(path: Path, note: str) -> str:
    lowered = f"{path.stem} {note}".lower()
    if "bbox_map" in lowered:
        return "bbox_map"
    if "bbox_sequence" in lowered:
        return "bbox_sequence"
    if "bbox set" in lowered or "bbox_set" in lowered or "bounding boxes" in lowered:
        return "bbox_set"
    if "segment_set" in lowered:
        return "segment_set"
    if "segment" in lowered:
        return "segment"
    if "point_set" in lowered:
        return "point_set"
    if "point" in lowered:
        return "point"
    if "bbox" in lowered or "box" in lowered or objective_uses_option_bbox(path):
        return "bbox"
    return "unspecified"


def objective_uses_option_bbox(path: Path) -> bool:
    objective = path.stem.rsplit("__", 1)[-1]
    return objective.endswith("_label")


def _query_ids_from_text(text: str) -> list[str]:
    ids: list[str] = []
    for pattern in (
        r"(?:Supported\s+)?`query_id`\s+values?:\s*([^\n]+)",
        r"(?:Supported\s+)?public\s+`query_id`:\s*([^\n]+)",
        r"(?:Supported\s+)?`query_id`:\s*([^\n]+)",
        r"(?:Supported\s+)?query ids?:\s*([^\n]+)",
        r"Query ids:\s*([^\n]+)",
    ):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            line = match.group(1)
            ids.extend(re.findall(r"`([^`]+)`", line))
            if "single" in line and "single" not in ids:
                ids.append("single")
    return _dedupe(ids) or ["single"]


def _query_id_text(text: str) -> str:
    return ", ".join(f"`{query_id}`" for query_id in _query_ids_from_text(text))


def _first_matching_note(text: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match is not None:
            note = " ".join(match.group(1).strip().split())
            return note.rstrip(".") + "."
    return ""


def _answer_note(text: str) -> str:
    return _first_matching_note(
        text,
        (
            r"answer_gt\.value`\s+is\s+([^\n]+)",
            r"Answer\s+is\s+([^\n]+)",
            r"Prompt-facing answer is\s+([^\n]+)",
        ),
    )


def _annotation_note(text: str) -> str:
    return _first_matching_note(
        text,
        (
            r"Annotation witness policy:\s*([^\n]+)",
            r"Annotation target:\s*([^\n]+)",
            r"Prompt-facing annotation is\s+([^\n]+)",
            r"Annotation is\s+([^\n]+)",
        ),
    )


def _program_terms(program: str) -> list[str]:
    terms: list[str] = []
    first_clause = program.split(";", 1)[0]
    inside_match = re.search(r"\((.*)\)", first_clause)
    if inside_match is not None:
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9_]*", inside_match.group(1)))
    for key, value in re.findall(r"([A-Za-z][A-Za-z0-9_]*)=([^;,)]*)", program):
        terms.append(key)
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9_]*", value))
    skip = {
        "scene",
        "scope",
        "rule",
        "target",
        "option",
        "options",
        "output",
        "annotation",
        "single",
    }
    return [term for term in _dedupe(terms) if term not in skip][:12]


def _operands_text(program: str, query_ids: str) -> str:
    terms = _program_terms(program)
    if terms:
        base = ", ".join(f"`{term}`" for term in terms)
        suffix = " plus the active `query_id` branch" if "," in query_ids else ""
        return f"visible scene state and prompt-bound operands named by {base}{suffix}."
    if "," in query_ids:
        return "visible scene state, prompt-bound target operands, and the active `query_id` branch."
    return "visible scene state and prompt-bound target operands named by the task contract."


def _build_structured_program_contract(path: Path, text: str, program_body: str) -> str:
    scene_id = path.parent.name
    text_without_program = _text_without_program_contract(text)
    program = _extract_program_expression(program_body)
    if not program:
        raise ValueError(f"{path}: cannot find concrete program expression")

    answer_note = _answer_note(text_without_program) or "generation binds a unique final answer."
    annotation_note = _annotation_note(text_without_program) or "the prompt/annotation contract defines the minimal visual witnesses."
    answer_schema = _schema_from_text(
        text_without_program,
        ("Answer schema", "Answer type", "answer_gt.type"),
        "unspecified",
    )
    annotation_schema = _schema_from_text(
        text_without_program,
        ("Annotation schema", "Annotation type", "Default `annotation_gt.type`", "annotation_gt.type"),
        "unspecified",
    )
    explicit_output = _extract_field_from_program(program, "output")
    explicit_annotation = _extract_field_from_program(program, "annotation")
    scope = _extract_field_from_program(program, "scope") or path.stem.removeprefix("task_puzzles__").split("__")[-1]
    operation_name = _program_operation_name(program)
    candidates = SCENE_CANDIDATE_SETS.get(scene_id, f"the visible puzzle elements in the `{scene_id}` scene")
    query_ids = _query_id_text(text_without_program)
    if answer_schema == "unspecified":
        answer_schema = _infer_answer_schema(path, program, answer_note)
    if annotation_schema == "unspecified":
        annotation_schema = _infer_annotation_schema(path, annotation_note)

    output_binding = f"`answer` uses the `{answer_schema}` schema"
    if explicit_output:
        output_binding += f" and is bound by `{explicit_output}`"
    output_binding += f"; {answer_note}"

    annotation_binding = f"`annotation` uses the `{annotation_schema}` schema"
    if explicit_annotation:
        annotation_binding += f" and is bound by `{explicit_annotation}`"
    annotation_binding += f"; {annotation_note}"

    return "\n".join(
        [
            f"Program: `{program}`",
            "",
            f"Candidate set: {candidates} inside the `{scope}` objective scope.",
            f"Operands: {_operands_text(program, query_ids)}",
            (
                f"Operation: evaluate `{operation_name}` over the candidate set using the visible states, "
                "constraints, transforms, comparisons, counts, paths, or option-selection rules encoded in the "
                "program expression; generation enforces a unique final answer."
            ),
            f"Output binding: {output_binding}",
            f"Annotation witnesses: {annotation_binding}",
            f"Query ids: {query_ids}.",
        ]
    )


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
    parser.add_argument("--root", type=Path, default=Path("docs/tasks/puzzles"))
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
            check_text = normalized if args.write else text
            missing = _missing_required_labels(check_text)
            if missing:
                errors.append(f"{path}: missing {', '.join(missing)}")
        except Exception as exc:  # noqa: BLE001 - maintenance script should report all doc failures.
            errors.append(str(exc))

    print(f"puzzle task docs scanned: {len(docs)}")
    print(f"docs requiring normalization: {len(changed)}")
    if args.write:
        print(f"docs rewritten: {len(changed)}")
    if args.check and changed:
        errors.append("puzzle Program Contract docs are not normalized; rerun with --write")
    if errors:
        print("program contract structural failures:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
