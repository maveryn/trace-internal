"""Solid-volume construction formulas for volume-equivalence scenes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trace.core.seed import spawn_rng

from .sampling import support_probabilities
from .state import OptionSpec, ResolvedProblem, SolidSpec

OPTION_LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

CUBOID_TO_CYLINDER_LENGTH_CASES: tuple[tuple[int, int, int, int], ...] = (
    (6, 4, 5, 12),
    (8, 5, 3, 10),
    (9, 4, 5, 10),
    (10, 6, 4, 12),
    (7, 6, 4, 21),
    (12, 5, 3, 30),
)
CYLINDER_TO_CONE_HEIGHT_CASES: tuple[tuple[int, int, int], ...] = (
    (12, 5, 10),
    (8, 6, 12),
    (9, 8, 24),
    (10, 6, 18),
    (14, 5, 15),
    (16, 6, 18),
)
CONE_TO_CUBOID_HEIGHT_CASES: tuple[tuple[int, int, int, int], ...] = (
    (18, 6, 6, 3),
    (24, 9, 6, 4),
    (30, 12, 10, 3),
    (36, 15, 9, 4),
    (54, 9, 9, 3),
    (42, 14, 7, 4),
)
CONE_SOURCE_OPTION_CASES: tuple[tuple[int, int], ...] = ((18, 6), (24, 6), (30, 9), (36, 5))
CYLINDER_SOURCE_OPTION_CASES: tuple[tuple[int, int], ...] = ((12, 4), (9, 6), (15, 4), (18, 5))
CUBOID_SOURCE_OPTION_CASES: tuple[tuple[int, int, int], ...] = (
    (6, 4, 4),
    (8, 3, 5),
    (8, 4, 3),
    (10, 4, 3),
)


def solid_volume(spec: SolidSpec) -> int:
    if spec.shape == "cuboid":
        return int(spec.length) * int(spec.width) * int(spec.height)
    if spec.shape == "cylinder":
        return int(spec.base_area) * int(spec.height)
    if spec.shape == "cone":
        numerator = int(spec.base_area) * int(spec.height)
        if numerator % 3 != 0:
            raise ValueError("cone base_area * height must be divisible by 3")
        return numerator // 3
    raise ValueError(f"unsupported solid shape: {spec.shape}")


def resolve_cuboid_to_cylinder_length(case: Sequence[int]) -> ResolvedProblem:
    length, width, height, target_base_area = [int(value) for value in case]
    source = SolidSpec("cuboid", height=height, length=length, width=width)
    answer = solid_volume(source) // int(target_base_area)
    if int(target_base_area) * int(answer) != solid_volume(source):
        raise ValueError("cuboid-to-cylinder case must yield integer target length")
    target = SolidSpec("cylinder", base_area=int(target_base_area), height=int(answer))
    return ResolvedProblem(
        source=source,
        target=target,
        answer=int(answer),
        answer_schema="integer",
        formula_family="volume_equivalence_missing_dimension",
        formula="target_length = source_cuboid_volume / cylinder_base_area",
        target_unknown_role="cylinder_length",
    )


def resolve_cylinder_to_cone_height(case: Sequence[int]) -> ResolvedProblem:
    source_base_area, source_height, target_base_area = [int(value) for value in case]
    source = SolidSpec("cylinder", base_area=int(source_base_area), height=int(source_height))
    answer = (3 * solid_volume(source)) // int(target_base_area)
    if int(target_base_area) * int(answer) != 3 * solid_volume(source):
        raise ValueError("cylinder-to-cone case must yield integer target height")
    target = SolidSpec("cone", base_area=int(target_base_area), height=int(answer))
    return ResolvedProblem(
        source=source,
        target=target,
        answer=int(answer),
        answer_schema="integer",
        formula_family="volume_equivalence_missing_dimension",
        formula="target_height = 3 * source_cylinder_volume / cone_base_area",
        target_unknown_role="cone_height",
    )


def resolve_cone_to_cuboid_height(case: Sequence[int]) -> ResolvedProblem:
    source_base_area, source_height, target_length, target_width = [int(value) for value in case]
    source = SolidSpec("cone", base_area=int(source_base_area), height=int(source_height))
    target_base = int(target_length) * int(target_width)
    answer = solid_volume(source) // target_base
    if target_base * int(answer) != solid_volume(source):
        raise ValueError("cone-to-cuboid case must yield integer target height")
    target = SolidSpec("cuboid", height=int(answer), length=int(target_length), width=int(target_width))
    return ResolvedProblem(
        source=source,
        target=target,
        answer=int(answer),
        answer_schema="integer",
        formula_family="volume_equivalence_missing_dimension",
        formula="target_height = source_cone_volume / (cuboid_length * cuboid_width)",
        target_unknown_role="cuboid_height",
    )


def bind_case_metadata(
    problem: ResolvedProblem,
    *,
    case_probabilities: Mapping[str, float],
    answer_support: Sequence[int | str],
) -> ResolvedProblem:
    return ResolvedProblem(
        source=problem.source,
        target=problem.target,
        answer=problem.answer,
        answer_schema=problem.answer_schema,
        formula_family=problem.formula_family,
        formula=problem.formula,
        target_unknown_role=problem.target_unknown_role,
        option_specs=tuple(problem.option_specs),
        selected_option_label=str(problem.selected_option_label),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=support_probabilities(answer_support),
        option_count_probabilities=dict(problem.option_count_probabilities),
    )


def _rotated_option_specs(
    *,
    source: SolidSpec,
    correct: SolidSpec,
    distractors: Sequence[SolidSpec],
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
    shuffle_namespace: str,
    label_namespace: str,
) -> tuple[tuple[OptionSpec, ...], str]:
    source_volume = solid_volume(source)
    candidates = [correct, *list(distractors)]
    rng = spawn_rng(int(instance_seed), str(shuffle_namespace))
    rng.shuffle(candidates[1:])
    candidates = [candidates[0], *candidates[1 : max(1, int(option_count))]]
    rng = spawn_rng(int(instance_seed), str(label_namespace))
    offset = int(rng.randrange(len(candidates)))
    rotated = candidates[-offset:] + candidates[:-offset] if offset else candidates
    option_specs = tuple(
        OptionSpec(label=str(label), solid=solid, volume=solid_volume(solid))
        for label, solid in zip(OPTION_LABELS[: int(option_count)], rotated)
    )
    selected_label = next(
        option.label
        for option in option_specs
        if option.volume == source_volume and option.solid == correct
    )
    return option_specs, str(selected_label)


def _option_problem(
    *,
    source: SolidSpec,
    correct: SolidSpec,
    distractors: Sequence[SolidSpec],
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
    shuffle_namespace: str,
    label_namespace: str,
) -> ResolvedProblem:
    option_specs, selected_label = _rotated_option_specs(
        source=source,
        correct=correct,
        distractors=distractors,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        params=params,
        shuffle_namespace=str(shuffle_namespace),
        label_namespace=str(label_namespace),
    )
    selected = next(option.solid for option in option_specs if option.label == selected_label)
    labels = tuple(option.label for option in option_specs)
    return ResolvedProblem(
        source=source,
        target=selected,
        answer=str(selected_label),
        answer_schema="option_letter",
        formula_family="volume_equivalence_option_match",
        formula="select option whose solid volume equals the source solid volume",
        target_unknown_role="equal_volume_option",
        option_specs=tuple(option_specs),
        selected_option_label=str(selected_label),
        answer_support_probabilities=support_probabilities(labels),
    )


def resolve_cone_matching_cylinder_option(
    case: Sequence[int],
    *,
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
    shuffle_namespace: str,
    label_namespace: str,
) -> ResolvedProblem:
    source = SolidSpec("cone", base_area=int(case[0]), height=int(case[1]))
    source_volume = solid_volume(source)
    correct = SolidSpec("cylinder", base_area=6, height=source_volume // 6)
    distractors = (
        SolidSpec("cylinder", base_area=4, height=max(2, source_volume // 6)),
        SolidSpec("cylinder", base_area=9, height=max(2, source_volume // 6 + 1)),
        SolidSpec("cylinder", base_area=12, height=max(2, source_volume // 6 - 1)),
        SolidSpec("cylinder", base_area=15, height=max(2, source_volume // 6 + 2)),
        SolidSpec("cylinder", base_area=18, height=max(2, source_volume // 6 + 3)),
    )
    return _option_problem(
        source=source,
        correct=correct,
        distractors=distractors,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        params=params,
        shuffle_namespace=str(shuffle_namespace),
        label_namespace=str(label_namespace),
    )


def resolve_cylinder_matching_cone_option(
    case: Sequence[int],
    *,
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
    shuffle_namespace: str,
    label_namespace: str,
) -> ResolvedProblem:
    source = SolidSpec("cylinder", base_area=int(case[0]), height=int(case[1]))
    source_volume = solid_volume(source)
    correct = SolidSpec("cone", base_area=18, height=source_volume // 6)
    distractors = (
        SolidSpec("cone", base_area=12, height=max(3, source_volume // 6)),
        SolidSpec("cone", base_area=24, height=max(3, source_volume // 6 + 1)),
        SolidSpec("cone", base_area=15, height=max(3, source_volume // 6 + 2)),
        SolidSpec("cone", base_area=21, height=max(3, source_volume // 6 + 1)),
        SolidSpec("cone", base_area=30, height=max(3, source_volume // 6 + 2)),
    )
    return _option_problem(
        source=source,
        correct=correct,
        distractors=distractors,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        params=params,
        shuffle_namespace=str(shuffle_namespace),
        label_namespace=str(label_namespace),
    )


def resolve_cuboid_matching_cylinder_option(
    case: Sequence[int],
    *,
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
    shuffle_namespace: str,
    label_namespace: str,
) -> ResolvedProblem:
    source = SolidSpec("cuboid", height=int(case[2]), length=int(case[0]), width=int(case[1]))
    source_volume = solid_volume(source)
    correct = SolidSpec("cylinder", base_area=8, height=source_volume // 8)
    distractors = (
        SolidSpec("cylinder", base_area=6, height=max(2, source_volume // 8)),
        SolidSpec("cylinder", base_area=10, height=max(2, source_volume // 8 + 1)),
        SolidSpec("cylinder", base_area=12, height=max(2, source_volume // 8 - 1)),
        SolidSpec("cylinder", base_area=14, height=max(2, source_volume // 8 + 2)),
        SolidSpec("cylinder", base_area=16, height=max(2, source_volume // 8 + 3)),
    )
    return _option_problem(
        source=source,
        correct=correct,
        distractors=distractors,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        params=params,
        shuffle_namespace=str(shuffle_namespace),
        label_namespace=str(label_namespace),
    )


def bind_option_metadata(
    problem: ResolvedProblem,
    *,
    case_probabilities: Mapping[str, float],
    option_count_probabilities: Mapping[str, float],
) -> ResolvedProblem:
    return ResolvedProblem(
        source=problem.source,
        target=problem.target,
        answer=problem.answer,
        answer_schema=problem.answer_schema,
        formula_family=problem.formula_family,
        formula=problem.formula,
        target_unknown_role=problem.target_unknown_role,
        option_specs=tuple(problem.option_specs),
        selected_option_label=str(problem.selected_option_label),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=dict(problem.answer_support_probabilities),
        option_count_probabilities=dict(option_count_probabilities),
    )


__all__ = [
    "CONE_SOURCE_OPTION_CASES",
    "CONE_TO_CUBOID_HEIGHT_CASES",
    "CUBOID_SOURCE_OPTION_CASES",
    "CUBOID_TO_CYLINDER_LENGTH_CASES",
    "CYLINDER_SOURCE_OPTION_CASES",
    "CYLINDER_TO_CONE_HEIGHT_CASES",
    "OPTION_LABELS",
    "bind_case_metadata",
    "bind_option_metadata",
    "resolve_cone_matching_cylinder_option",
    "resolve_cone_to_cuboid_height",
    "resolve_cuboid_matching_cylinder_option",
    "resolve_cuboid_to_cylinder_length",
    "resolve_cylinder_matching_cone_option",
    "resolve_cylinder_to_cone_height",
    "solid_volume",
]
