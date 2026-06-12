"""Query sampling and candidate enumeration for circle-theorem value tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Tuple

from ......core.seed import spawn_rng
from .....shared.support_sampling import resolve_integer_choice
from .theorem_common import (
    _ANSWER_SUPPORT_BY_VARIANT,
    _TANGENT_SECANT_TARGET_KINDS,
    _SECANT_SECANT_VARIABLE_TARGET_KINDS,
    _GEN_DEFAULTS,
    _ResolvedQuery,
)

BASE_QUERY_IDS: Tuple[str, ...] = (
    "diameter_perpendicular_chord_length",
    "secant_secant_variable_segment_length",
    "tangent_secant_length",
    "secant_secant_length",
    "intersecting_chords_arc_measure",
    "multi_step_angle_value",
    "inscribed_angle_from_central",
    "central_angle_from_inscribed",
    "inscribed_angle_from_arc",
    "tangent_chord_angle_from_arc",
    "tangent_chord_angle_from_inscribed",
    "external_two_secants_angle_from_arcs",
    "opposite_angle_supplement",
    "exterior_angle_from_opposite_interior",
)
BASE_SAMPLING_NAMESPACE = "geometry_circle_theorem_value_base"

def _candidate_diameter_chord_values(target_answer: int) -> List[Dict[str, int]]:
    candidates: List[Dict[str, int]] = []
    for radius in range(8, 41):
        for offset in range(2, radius - 1):
            half_chord_sq = (radius * radius) - (offset * offset)
            half_chord = int(math.isqrt(int(half_chord_sq)))
            if int(half_chord * half_chord) != int(half_chord_sq):
                continue
            answer_value = int(radius - offset)
            if int(answer_value) != int(target_answer):
                continue
            chord_length = int(2 * half_chord)
            diameter_length = int(2 * radius)
            if half_chord < 4 or chord_length > 64:
                continue
            candidates.append(
                {
                    "radius": int(radius),
                    "offset": int(offset),
                    "half_chord": int(half_chord),
                    "diameter": int(diameter_length),
                    "chord": int(chord_length),
                    "answer": int(answer_value),
                }
            )
    return candidates

def _hard_tangent_secant_triple(*, outside: int, internal: int, tangent: int) -> bool:
    if int(outside) < 16 or int(internal) < 10:
        return False
    if len({int(outside), int(internal), int(tangent)}) != 3:
        return False
    if int(tangent) == int(2 * outside) or int(tangent) % int(outside) == 0:
        return False
    if int(internal) in {int(outside), int(2 * outside), int(3 * outside)}:
        return False
    if int(outside) % 2 == 0 and int(internal) == int(outside // 2):
        return False
    return True

def _candidate_tangent_secant_values(
    target_answer: int, *, target_kind: str | None = None
) -> List[Dict[str, int | str]]:
    if target_kind is not None and str(target_kind) not in _TANGENT_SECANT_TARGET_KINDS:
        raise ValueError(f"unsupported tangent secant target kind: {target_kind}")
    candidates: List[Dict[str, int | str]] = []
    for outside in range(16, 81):
        for internal in range(10, 71):
            tangent_sq = int(outside * (outside + internal))
            tangent = int(math.isqrt(tangent_sq))
            if int(tangent * tangent) != int(tangent_sq):
                continue
            if int(tangent) > 100:
                continue
            if not _hard_tangent_secant_triple(
                outside=int(outside), internal=int(internal), tangent=int(tangent)
            ):
                continue
            base_spec = {
                "PA": int(outside),
                "AB": int(internal),
                "PT": int(tangent),
                "PB": int(outside + internal),
            }
            target_options = {
                "outside": ("PA", int(outside)),
                "inside": ("AB", int(internal)),
                "tangent": ("PT", int(tangent)),
            }
            for option_kind, (answer_segment, answer_value) in target_options.items():
                if target_kind is not None and str(option_kind) != str(target_kind):
                    continue
                if int(answer_value) != int(target_answer):
                    continue
                candidates.append(
                    {
                        **base_spec,
                        "target_kind": str(option_kind),
                        "canonical_answer_segment": str(answer_segment),
                        "answer": int(answer_value),
                    }
                )
    return candidates

def _feasible_tangent_secant_target_kinds(target_answer: int) -> Tuple[str, ...]:
    kinds = sorted(
        {
            str(candidate["target_kind"])
            for candidate in _candidate_tangent_secant_values(int(target_answer))
        }
    )
    return tuple(kind for kind in _TANGENT_SECANT_TARGET_KINDS if kind in set(kinds))

def _candidate_secant_secant_values(target_answer: int) -> List[Dict[str, int]]:
    candidates: List[Dict[str, int]] = []
    pa = int(target_answer)
    for ab in range(11, 35):
        power = int(pa * (pa + ab))
        center_x = float(pa + (0.5 * ab))
        for pc in range(3, 25):
            if int(power) % int(pc) != 0:
                continue
            pd = int(power // pc)
            cd = int(pd - pc)
            if not (3 <= int(cd) <= 30):
                continue
            if int(pc) == int(pa) and int(cd) == int(ab):
                continue
            cos_theta = float(pc + pd) / float(2.0 * center_x)
            if 0.25 <= float(cos_theta) <= 0.86:
                candidates.append(
                    {
                        "PA": int(pa),
                        "AB": int(ab),
                        "PB": int(pa + ab),
                        "PC": int(pc),
                        "CD": int(cd),
                        "PD": int(pd),
                        "power": int(power),
                    }
                )
    return candidates

def _candidate_secant_secant_variable_values(
    target_answer: int,
    *,
    target_kind: str | None = None,
) -> List[Dict[str, int | str]]:
    if (
        target_kind is not None
        and str(target_kind) not in _SECANT_SECANT_VARIABLE_TARGET_KINDS
    ):
        raise ValueError(f"unsupported secant secant target kind: {target_kind}")
    candidates: List[Dict[str, int | str]] = []
    for pa in range(4, 31):
        for ab in range(8, 61):
            power = int(pa * (pa + ab))
            center_x = float(pa + (0.5 * ab))
            for pc in range(4, 31):
                if int(power) % int(pc) != 0:
                    continue
                pd = int(power // pc)
                cd = int(pd - pc)
                if not (8 <= int(cd) <= 60):
                    continue
                if int(pc) == int(pa) and int(cd) == int(ab):
                    continue
                cos_theta = float(pc + pd) / float(2.0 * center_x)
                if not (0.20 <= float(cos_theta) <= 0.88):
                    continue
                values = (int(pa), int(ab), int(pc), int(cd))
                if len(set(values)) != 4:
                    continue
                if int(ab) in {int(pa), int(2 * pa), int(3 * pa)}:
                    continue
                if int(cd) in {int(pc), int(2 * pc), int(3 * pc)}:
                    continue
                base_spec = {
                    "PA": int(pa),
                    "AB": int(ab),
                    "PB": int(pa + ab),
                    "PC": int(pc),
                    "CD": int(cd),
                    "PD": int(pd),
                    "power": int(power),
                }
                target_options = {
                    "outside_first": ("PA", int(pa)),
                    "inside_first": ("AB", int(ab)),
                    "outside_second": ("PC", int(pc)),
                    "inside_second": ("CD", int(cd)),
                }
                for option_kind, (
                    answer_segment,
                    answer_value,
                ) in target_options.items():
                    if target_kind is not None and str(option_kind) != str(target_kind):
                        continue
                    if int(answer_value) != int(target_answer):
                        continue
                    candidates.append(
                        {
                            **base_spec,
                            "target_kind": str(option_kind),
                            "canonical_answer_segment": str(answer_segment),
                            "answer": int(answer_value),
                        }
                    )
    return candidates

def _feasible_secant_secant_variable_target_kinds(
    target_answer: int,
) -> Tuple[str, ...]:
    kinds = sorted(
        {
            str(candidate["target_kind"])
            for candidate in _candidate_secant_secant_variable_values(
                int(target_answer)
            )
        }
    )
    return tuple(
        kind for kind in _SECANT_SECANT_VARIABLE_TARGET_KINDS if kind in set(kinds)
    )

def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    rng = spawn_rng(int(instance_seed), f"{BASE_SAMPLING_NAMESPACE}.query")
    query_id = str(params.get("query_id", "")).strip()
    if query_id not in BASE_QUERY_IDS:
        raise ValueError(f"circle theorem shared sampling requires a supported query_id: {query_id!r}")
    query_id_probabilities = {
        str(candidate): (1.0 if str(candidate) == str(query_id) else 0.0)
        for candidate in BASE_QUERY_IDS
    }
    support_key = f"{query_id}_answer_support"
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=_ANSWER_SUPPORT_BY_VARIANT[str(query_id)],
        namespace=f"{BASE_SAMPLING_NAMESPACE}.{query_id}.target_answer",
        balanced_flag_key="balanced_answer_sampling",
        namespace_support_permutation=True,
    )
    tangent_secant_target_kind: str | None = None
    tangent_secant_target_kind_probabilities: Dict[str, float] = {}
    secant_secant_variable_target_kind: str | None = None
    secant_secant_variable_target_kind_probabilities: Dict[str, float] = {}
    if str(query_id) == "tangent_secant_length":
        feasible_target_kinds = _feasible_tangent_secant_target_kinds(
            int(target_answer)
        )
        if not feasible_target_kinds:
            raise ValueError(
                f"unsupported target answer for tangent secant theorem: {target_answer}"
            )
        explicit_target_kind = params.get("tangent_secant_target_kind")
        if explicit_target_kind is not None:
            if str(explicit_target_kind) not in feasible_target_kinds:
                raise ValueError(
                    f"unsupported tangent secant target kind {explicit_target_kind!r} for target answer {target_answer}"
                )
            tangent_secant_target_kind = str(explicit_target_kind)
        else:
            tangent_secant_target_kind = str(rng.choice(feasible_target_kinds))
        probability = 1.0 / float(len(feasible_target_kinds))
        tangent_secant_target_kind_probabilities = {
            str(kind): float(probability) for kind in feasible_target_kinds
        }
    if str(query_id) == "secant_secant_variable_segment_length":
        feasible_target_kinds = _feasible_secant_secant_variable_target_kinds(
            int(target_answer)
        )
        if not feasible_target_kinds:
            raise ValueError(
                f"unsupported target answer for variable secant secant theorem: {target_answer}"
            )
        explicit_target_kind = params.get("secant_secant_variable_target_kind")
        if explicit_target_kind is not None:
            if str(explicit_target_kind) not in feasible_target_kinds:
                raise ValueError(
                    f"unsupported variable secant secant target kind {explicit_target_kind!r} "
                    f"for target answer {target_answer}"
                )
            secant_secant_variable_target_kind = str(explicit_target_kind)
        else:
            secant_secant_variable_target_kind = str(rng.choice(feasible_target_kinds))
        probability = 1.0 / float(len(feasible_target_kinds))
        secant_secant_variable_target_kind_probabilities = {
            str(kind): float(probability) for kind in feasible_target_kinds
        }
    return _ResolvedQuery(
        query_id=str(query_id),
        target_answer=int(target_answer),
        query_id_probabilities=dict(query_id_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        tangent_secant_target_kind=tangent_secant_target_kind,
        tangent_secant_target_kind_probabilities=dict(
            tangent_secant_target_kind_probabilities
        ),
        secant_secant_variable_target_kind=secant_secant_variable_target_kind,
        secant_secant_variable_target_kind_probabilities=dict(
            secant_secant_variable_target_kind_probabilities
        ),
    )

__all__ = [
    '_candidate_diameter_chord_values',
    '_hard_tangent_secant_triple',
    '_candidate_tangent_secant_values',
    '_feasible_tangent_secant_target_kinds',
    '_candidate_secant_secant_values',
    '_candidate_secant_secant_variable_values',
    '_feasible_secant_secant_variable_target_kinds',
    '_resolve_query',
]
