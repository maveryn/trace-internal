#!/usr/bin/env python3
"""Normalize physics task-doc Program Contract sections.

This maintainer script rewrites only the ``## Program Contract`` block in
``docs/tasks/physics/**/*.md``. It preserves the existing concrete program
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
    "analog_meter": "the visible meter needle, tick scale, numeric labels, and unit label",
    "bridge_circuit": "the visible bridge circuit components, branch labels, and balance/readout markings",
    "bulb_circuit": "the visible bulb symbols, wire topology, switch states, and component labels",
    "buoyancy_density": "the visible floating object, liquid region, level markers, and density labels",
    "circuit_equivalent": "the visible components between terminals A and B, their values, and the series-parallel topology",
    "circuit_state_change": "the visible switch action cue, bulb symbols, branch topology, and component labels",
    "collision": "the visible puck states, motion arrows or trails, impact marker, labels, and candidate option cells",
    "electromagnetic_induction": "the visible loop panels, magnetic-field markers, motion/change cues, and panel labels",
    "electrostatic_field": "the visible point charges, query point marker, test-charge cue, and direction option arrows",
    "fluid_flow": "the visible pipe sections, area labels, speed labels, and marked missing readout",
    "free_body_forces": "the visible force diagram, applied force arrows, magnitude labels, and candidate result arrows",
    "gear_train": "the visible gears, tooth-count labels, input/output markers, and candidate gear-train panels",
    "graduated_cylinder": "the visible cylinder readouts, liquid levels, tick marks, numeric labels, and unit labels",
    "hydraulic": "the visible piston sides, force labels, area labels, chambers, and missing-value marker",
    "lens_optics": "the visible lens, object arrow, focal marks, principal rays, and image-property option cues",
    "lever": "the visible lever beam, fulcrum, distance marks, weight blocks, and missing-weight marker",
    "magnetic_force": "the visible charged particle, velocity vector, magnetic-field orientation marker, and direction options",
    "manometer": "the visible manometer columns, height difference marker, density label, and pressure side labels",
    "motion_graph": "the visible graph curve, marked interval, axis scales, labels, and option cells when present",
    "orbital_motion": "the visible orbit, focus candidates, planet-position candidates, and orbital labels",
    "piston_cylinder": "the visible initial and final piston-cylinder states, pressure readout, dimensions, and motion cue",
    "pulley": "the visible pulley system, rope/support segments, load markers, and cut or connected segment cues",
    "pv_diagram": "the visible pressure-volume axes, process path, endpoint labels, and shaded/process direction cues",
    "ray_optics": "the visible mirror/ray geometry, ray path segments, target markers, and bounce/hit labels",
    "refraction_layers": "the visible media layers, interface normals, ray segments, and medium labels",
    "shadow_cause": "the visible object, shadow geometry, light-source candidates, and option labels",
    "signal_transform": "the visible input waveform panel, spectrum option panels, frequency markers, and labels",
    "spring": "the visible spring setups, weight blocks, extension markers, and measurement labels",
    "stack_stability": "the visible candidate stack panels, brick stacks, center-of-mass markers, projection lines, and support brackets",
    "switch_circuit": "the visible switch states, bulb symbols, wire topology, and bulb labels",
    "thermal_mixing": "the visible containers, initial temperature labels, masses or mixture labels, and final-state cue",
    "thermometer": "the visible thermometer tube, liquid level, numeric tick scale, and source unit label",
    "vernier_caliper": "the visible caliper jaws, main scale, vernier scale, zero tick, and aligned tick mark",
    "wave_interference": "the visible wave sources, wavefront spacing, candidate points, and guided source-to-point paths",
    "waveform_panel": "the visible waveform option panels, amplitudes, periods, wavelengths, and panel labels",
    "wire_magnetism": "the visible current-carrying wire, current direction cue, point marker, and magnetic-field direction options",
}


def _extract_section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*(.*?)(?:^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return ""
    return match.group(1).strip()


def _program_contract_match(text: str) -> re.Match[str] | None:
    return re.search(r"^## Program Contract[ \t]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)


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
    return first_clause or "physics_program"


def _schema_from_contract(section: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*`([^`]+)`", section)
    if match is not None:
        return match.group(1).strip()
    match = re.search(rf"{re.escape(label)}:\s*([A-Za-z0-9_]+)", section)
    if match is not None:
        return match.group(1).strip().rstrip(".")
    return "unspecified"


def _contract_notes(section: str, *, skip_prefixes: Iterable[str]) -> list[str]:
    notes: list[str] = []
    prefixes = tuple(skip_prefixes)
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        bullet = stripped[2:].strip()
        if bullet.startswith(prefixes):
            continue
        if bullet.startswith("Annotation and answer must be projected"):
            continue
        notes.append(bullet)
    return notes


def _answer_note(section: str) -> str:
    notes = _contract_notes(
        section,
        skip_prefixes=("Answer schema:", "Generator `answer_gt.type`:", "Generator `answer_gt.type`:"),
    )
    return notes[0] if notes else "the value described by the Answer Contract"


def _annotation_notes(section: str) -> str:
    notes = _contract_notes(
        section,
        skip_prefixes=("Annotation schema:", "Generator `annotation_gt.type`:", "Generator `annotation_gt.type`:"),
    )
    if not notes:
        return "The Annotation Contract below defines the prompt-facing witnesses."
    return " ".join(notes[:2])


def _query_ids_from_table(text: str) -> list[str]:
    section = _extract_section(text, "Query Branches")
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
    patterns = (
        r"(?:Supported\s+)?`query_id`\s+values?:\s*([^\n]+)",
        r"(?:Supported\s+)?query ids?:\s*([^\n]+)",
        r"(?:Supported\s+)?`query_id`s:\s*([^\n]+)",
        r"Query ids:\s*([^\n]+)",
    )
    for pattern in patterns:
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


def _argument_bullets(text: str) -> list[str]:
    metadata = _extract_section(text, "Program Metadata")
    if not metadata:
        return []
    match = re.search(r"^- Arguments:\s*\n(.*?)(?:\n- |\Z)", metadata, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        return []

    arguments: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        raw = stripped[2:].strip()
        parsed = re.match(r"`([^`]+)`:\s*([^;]+);\s*allowed\s+([^;]+);\s*source\s+(.+)", raw)
        if parsed is not None:
            name, role, allowed, source = parsed.groups()
            arguments.append(
                f"`{name}` ({role.strip()}, allowed {allowed.strip()}, source {source.strip().rstrip('.')})"
            )
        else:
            arguments.append(raw.rstrip("."))
    return arguments


def _operands_text(text: str, query_ids: str) -> str:
    arguments = _argument_bullets(text)
    if arguments:
        operand_text = "; ".join(arguments)
        if "," in query_ids:
            return f"{operand_text}; active `query_id` branch when present."
        return f"{operand_text}."
    if "," in query_ids:
        return "prompt-bound diagram quantities plus the active `query_id` branch."
    return "prompt-bound diagram quantities named by the task contract."


def _build_structured_program_contract(path: Path, text: str, program_body: str) -> str:
    scene_id = path.parent.name
    program = _extract_program_expression(program_body)
    if not program:
        raise ValueError(f"{path}: cannot find concrete program expression")

    answer_section = _extract_section(text, "Answer Contract")
    annotation_section = _extract_section(text, "Annotation Contract")
    answer_schema = _schema_from_contract(answer_section, "Answer schema")
    annotation_schema = _schema_from_contract(annotation_section, "Annotation schema")
    explicit_output = _extract_field_from_program(program, "output")
    scope = _extract_field_from_program(program, "scope") or path.stem.removeprefix("task_physics__").split("__")[-1]
    operation_name = _program_operation_name(program)
    candidates = SCENE_CANDIDATE_SETS.get(scene_id, f"the visible physics diagram elements in the `{scene_id}` scene")
    query_ids = _query_id_text(text)

    return "\n".join(
        [
            f"Program: `{program}`",
            "",
            f"Candidate set: {candidates} inside the `{scope}` objective scope.",
            f"Operands: {_operands_text(text, query_ids)}",
            (
                f"Operation: evaluate `{operation_name}` over the candidate set using the visible quantities, "
                "relations, branch semantics, and formulas encoded in the program expression; generation enforces "
                "a unique final answer."
            ),
            (
                f"Output binding: `answer` uses the `{answer_schema}` schema"
                + (f" and is bound by `{explicit_output}`" if explicit_output else "")
                + f"; {_answer_note(answer_section)}"
            ),
            f"Annotation witnesses: `{annotation_schema}` witnesses from the finalized render. {_annotation_notes(annotation_section)}",
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
    parser.add_argument("--root", type=Path, default=Path("docs/tasks/physics"))
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

    print(f"physics task docs scanned: {len(docs)}")
    print(f"docs requiring normalization: {len(changed)}")
    if args.write:
        print(f"docs rewritten: {len(changed)}")
    if args.check and changed:
        errors.append("physics Program Contract docs are not normalized; rerun with --write")
    if errors:
        print("program contract structural failures:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
