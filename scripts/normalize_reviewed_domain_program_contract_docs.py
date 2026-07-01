#!/usr/bin/env python3
"""Normalize reviewed-domain task-doc Program Contract sections.

This maintainer script rewrites only ``## Program Contract`` blocks in task
docs for reviewed post-migration domains. It preserves the existing concrete
program expression and expands compact sections into the structured labels used
by post-migration taxonomy review.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_DOMAINS = ("games", "graph", "icons", "illustrations", "three_d", "symbolic")

REQUIRED_LABELS = (
    "Program:",
    "Candidate set:",
    "Operands:",
    "Operation:",
    "Output binding:",
    "Annotation witnesses:",
    "Query ids:",
)

DOMAIN_CANDIDATE_SETS: dict[str, str] = {
    "games": "the visible game board, pieces, tokens, cards, tiles, marked state, legal-move cues, result panels, and labeled options",
    "graph": "the visible graph, tree, network, route, matrix, table, node, edge, label, weight, path, and option elements",
    "icons": "the visible icon instances, icon attributes, fields, grids, paths, panels, reference items, and labeled option cards",
    "illustrations": "the visible illustrated scene objects, people, regions, tiles, patches, labels, and option panels",
    "three_d": "the visible 3D objects, surfaces, room/street/warehouse structures, spatial anchors, markers, and labeled options",
    "symbolic": "the visible symbolic notation, tokens, rows, columns, cards, labels, components, and target markers",
}

DOMAIN_OPERATION_TEXT: dict[str, str] = {
    "games": (
        "using the visible game state, rules, legal moves, comparisons, counts, "
        "simulations, or option-selection constraints encoded in the program expression"
    ),
    "graph": (
        "using the visible graph structure, labels, weights, directions, reachability, "
        "paths, connectivity, or option-selection constraints encoded in the program expression"
    ),
    "icons": (
        "using the visible icon attributes, positions, relationships, transforms, counts, "
        "comparisons, or option-selection constraints encoded in the program expression"
    ),
    "illustrations": (
        "using the visible illustrated objects, regions, layout relationships, counts, "
        "patch/tile transforms, or option-selection constraints encoded in the program expression"
    ),
    "three_d": (
        "using the finalized 3D scene state, camera projection, object identities, spatial "
        "relations, counts, distances, or option-selection constraints encoded in the program expression"
    ),
    "symbolic": (
        "using the visible symbolic notation, rows, columns, labels, component states, "
        "computed values, or option-selection constraints encoded in the program expression"
    ),
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
        r"Program code:\s*`([^`]+)`",
        r"Program schema:\s*`([^`]+)`",
        r"`([^`]*scene\s*=[^`]*)`",
    ):
        match = re.search(pattern, program_body, flags=re.IGNORECASE | re.DOTALL)
        if match is not None:
            return " ".join(match.group(1).split()).rstrip(".")

    for line in program_body.splitlines():
        stripped = line.strip().strip("- ").strip("`").rstrip(".")
        if stripped and "scene=" in stripped:
            return " ".join(stripped.split())
    return ""


def _extract_field_from_program(program: str, field: str) -> str:
    match = re.search(rf"(?:^|[;,(\s]){re.escape(field)}\s*=\s*([^;,)\s]+)", program)
    if match is None:
        return ""
    return match.group(1).strip()


def _program_operation_name(program: str) -> str:
    first_clause = program.split(";", 1)[0].strip()
    if "(" in first_clause:
        return first_clause.split("(", 1)[0].strip()
    return first_clause or "program"


def _normalize_answer_schema(schema: str) -> str:
    schema = str(schema).strip().strip("`").rstrip(".")
    mapping = {
        "count": "integer",
        "value": "integer",
        "number": "integer",
        "integer_count": "integer",
        "integer_value": "integer",
        "integer_digit": "integer",
        "option": "option_letter",
        "label": "option_letter",
        "option_label": "option_letter",
        "string_label": "string",
        "label_string": "string",
    }
    return mapping.get(schema, schema)


def _normalize_annotation_schema(schema: str) -> str:
    schema = str(schema).strip().strip("`").rstrip(".")
    if "(" in schema:
        schema = schema.split("(", 1)[0].strip()
    mapping = {
        "scalar": "bbox",
        "unordered": "bbox_set",
        "boxes": "bbox_set",
        "box": "bbox",
    }
    return mapping.get(schema, schema)


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
    if any(term in lowered for term in ("count", "value", "digit", "size", "length", "sum", "total", "weight")):
        return "integer"
    if any(term in lowered for term in ("label", "option", "selected", "letter", "match")):
        return "option_letter"
    if any(term in lowered for term in ("status", "relation", "color", "type", "side", "winner")):
        return "string"
    return "string"


def _infer_annotation_schema(path: Path, note: str, program: str) -> str:
    domain = path.parts[path.parts.index("tasks") + 1]
    objective = path.stem.rsplit("__", 1)[-1]
    lowered = f"{path.stem} {note} {program}".lower()
    if "bbox_map" in lowered:
        return "bbox_map"
    if "bbox_sequence" in lowered:
        return "bbox_sequence"
    if "bbox_set_map" in lowered:
        return "bbox_set_map"
    if "bbox set" in lowered or "bbox_set" in lowered or "bounding boxes" in lowered:
        return "bbox_set"
    if "segment_set" in lowered:
        return "segment_set"
    if "segment" in lowered:
        return "segment"
    if "point_sequence" in lowered:
        return "point_sequence"
    if "point_set" in lowered:
        return "point_set"
    if "point_map" in lowered:
        return "point_map"
    if "point" in lowered:
        return "point"
    if domain == "icons" and "count" in objective:
        return "bbox_set"
    if "bbox" in lowered or "box" in lowered or path.stem.endswith("_label"):
        return "bbox"
    return "bbox"


def _query_ids_from_text(text: str) -> list[str]:
    ids: list[str] = []
    for pattern in (
        r"(?:Supported\s+)?`query_id`\s+values?:\s*([^\n]+)",
        r"(?:Supported\s+)?public\s+`query_id`:\s*([^\n]+)",
        r"(?:Supported\s+)?`query_id`:\s*([^\n]+)",
        r"(?:Supported\s+)?query ids?:\s*([^\n]+)",
        r"Query IDs?:\s*([^\n]+)",
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
            if not note.strip(" .;:-`"):
                continue
            return note.rstrip(".") + "."
    return ""


def _answer_note(text: str) -> str:
    return _first_matching_note(
        text,
        (
            r"^\s*(?:[-*]|\d+\.)?\s*`?answer_gt\.value`?\s+is\s+([^\n]+)",
            r"^\s*(?:[-*]|\d+\.)?\s*Answer\s+is\s+([^\n]+)",
            r"^\s*(?:[-*]|\d+\.)?\s*Prompt-facing answer is\s+([^\n]+)",
            r"^\s*(?:[-*]|\d+\.)?\s*The answer value is\s+([^\n]+)",
        ),
    )


def _annotation_note(text: str) -> str:
    return _first_matching_note(
        text,
        (
            r"^\s*(?:[-*]|\d+\.)?\s*Annotation witness policy:\s*([^\n]+)",
            r"^\s*(?:[-*]|\d+\.)?\s*Annotation target:\s*([^\n]+)",
            r"^\s*(?:[-*]|\d+\.)?\s*Prompt-facing annotation is\s+([^\n]+)",
        ),
    )


def _program_terms(program: str) -> list[str]:
    terms: list[str] = []
    first_clause = program.split(";", 1)[0]
    inside_match = re.search(r"\((.*)\)", first_clause)
    if inside_match is not None:
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9_]*", inside_match.group(1)))
    for key, value in re.findall(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*([^;,)]*)", program):
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
        "for",
        "in",
        "and",
        "or",
        "not",
        "integer",
        "count",
        "value",
        "string",
        "option_letter",
        "bbox",
        "bbox_set",
        "bbox_map",
        "bbox_sequence",
        "point",
        "point_set",
        "point_map",
        "point_sequence",
        "segment",
        "segment_set",
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


def _missing_required_labels_from_body(body: str) -> list[str]:
    return [label for label in REQUIRED_LABELS if label not in body]


def _candidate_set_text(domain: str, scope: str) -> str:
    candidates = DOMAIN_CANDIDATE_SETS.get(domain, "the visible rendered task elements")
    return f"{candidates} inside the `{scope}` objective scope."


def _insert_candidate_set_only(domain: str, body: str, scope: str) -> str:
    lines = body.strip().splitlines()
    candidate = f"Candidate set: {_candidate_set_text(domain, scope)}"
    for index, line in enumerate(lines):
        if line.strip().startswith("Program:"):
            insert_at = index + 1
            while insert_at < len(lines) and not lines[insert_at].strip():
                insert_at += 1
            return "\n".join(lines[: index + 1] + ["", candidate] + lines[index + 1 :]).rstrip() + "\n"
    return body


def _build_structured_program_contract(path: Path, text: str, program_body: str) -> str:
    domain = path.parts[path.parts.index("tasks") + 1]
    text_without_program = _text_without_program_contract(text)
    program = _extract_program_expression(program_body)
    if not program:
        raise ValueError(f"{path}: cannot find concrete program expression")

    scope = _extract_field_from_program(program, "scope") or path.stem.rsplit("__", 1)[-1]
    existing_missing = _missing_required_labels_from_body(program_body)
    source_text = text_without_program if not existing_missing else text_without_program + "\n" + program_body
    if existing_missing == ["Candidate set:"] and "Program:" in program_body:
        return _insert_candidate_set_only(domain, program_body, scope)

    output_field = _extract_field_from_program(program, "output")
    annotation_field = _extract_field_from_program(program, "annotation")
    answer_note = _answer_note(source_text) or "generation binds a unique final answer."
    annotation_note = _annotation_note(source_text) or "the prompt/annotation contract defines the minimal visual witnesses."
    answer_schema = _schema_from_text(
        source_text,
        ("Answer schema", "Answer type", "answer_gt.type"),
        output_field or "unspecified",
    )
    annotation_schema = _schema_from_text(
        source_text,
        ("Annotation schema", "Annotation type", "Default `annotation_gt.type`", "annotation_gt.type"),
        annotation_field or "unspecified",
    )

    answer_schema = _normalize_answer_schema(answer_schema)
    annotation_schema = _normalize_annotation_schema(annotation_schema)
    if answer_schema == "unspecified":
        answer_schema = _infer_answer_schema(path, program, answer_note)
    if annotation_schema == "unspecified":
        annotation_schema = _infer_annotation_schema(path, annotation_note, program)

    query_ids = _query_id_text(source_text)
    operation_name = _program_operation_name(program)
    operation_text = DOMAIN_OPERATION_TEXT.get(domain, "using the visible states and constraints encoded in the program expression")

    return "\n".join(
        [
            f"Program: `{program}`",
            "",
            f"Candidate set: {_candidate_set_text(domain, scope)}",
            f"Operands: {_operands_text(program, query_ids)}",
            (
                f"Operation: evaluate `{operation_name}` over the candidate set {operation_text}; "
                "generation enforces a unique final answer."
            ),
            f"Output binding: `answer` uses the `{answer_schema}` schema; {answer_note}",
            f"Annotation witnesses: `annotation` uses the `{annotation_schema}` schema; {annotation_note}",
            f"Query ids: {query_ids}.",
        ]
    )


def _normalize_text(path: Path, text: str, *, force: bool = False) -> tuple[str, bool]:
    match = _program_contract_match(text)
    if match is None:
        raise ValueError(f"{path}: missing ## Program Contract")
    body = match.group(1).strip()
    if not force and not _missing_required_labels_from_body(body):
        return text, False
    structured = _build_structured_program_contract(path, text, body)
    replacement = "\n" + structured.rstrip() + "\n\n"
    normalized = text[: match.start(1)] + replacement + text[match.end(1) :].lstrip("\n")
    return normalized, normalized != text


def _missing_required_labels(text: str) -> list[str]:
    match = _program_contract_match(text)
    if match is None:
        return list(REQUIRED_LABELS)
    return _missing_required_labels_from_body(match.group(1))


def _iter_docs(root: Path, domain: str) -> list[Path]:
    return sorted((root / domain).glob(f"*/*.md"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-root", type=Path, default=Path("docs/tasks"))
    parser.add_argument("--domains", nargs="+", default=list(DEFAULT_DOMAINS))
    parser.add_argument("--write", action="store_true", help="Rewrite docs in place")
    parser.add_argument("--check", action="store_true", help="Fail if docs are not normalized")
    parser.add_argument("--force", action="store_true", help="Rewrite existing structured Program Contract blocks too")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    changed: list[Path] = []
    scanned = 0
    errors: list[str] = []

    for domain in args.domains:
        docs = _iter_docs(args.docs_root, domain)
        scanned += len(docs)
        for path in docs:
            try:
                text = path.read_text(encoding="utf-8")
                normalized, did_change = _normalize_text(path, text, force=args.force)
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

    print(f"reviewed-domain task docs scanned: {scanned}")
    print(f"docs requiring normalization: {len(changed)}")
    if args.write:
        print(f"docs rewritten: {len(changed)}")
    if args.check and changed:
        errors.append("reviewed-domain Program Contract docs are not normalized; rerun with --write")
    if errors:
        print("program contract structural failures:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
