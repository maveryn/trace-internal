"""Select the option solid that has equal volume to the source solid."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from trace.tasks.geometry.shared.option_count import resolve_geometry_option_count

from ._lifecycle import VolumeEquivalenceTaskBinding, prepare_volume_equivalence_task_parts
from .shared.annotations import OPTION_ANNOTATION_KEYS
from .shared.construction import (
    CONE_SOURCE_OPTION_CASES,
    CUBOID_SOURCE_OPTION_CASES,
    CYLINDER_SOURCE_OPTION_CASES,
    bind_option_metadata,
    resolve_cone_matching_cylinder_option,
    resolve_cuboid_matching_cylinder_option,
    resolve_cylinder_matching_cone_option,
)
from .shared.defaults import DOMAIN, SCENE_ID, load_volume_equivalence_defaults
from .shared.rendering import render_option_scene
from .shared.sampling import select_conversion_case
from .shared.state import ResolvedProblem


TASK_ID = "task_geometry__volume_equivalence_conversion__equal_volume_option_label"
TASK_ID_EQUAL_VOLUME_OPTION = TASK_ID
QUERY_ID_CONE_MATCHES_CYLINDER_OPTION = "cone_matches_cylinder_option"
QUERY_ID_CYLINDER_MATCHES_CONE_OPTION = "cylinder_matches_cone_option"
QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION = "cuboid_matches_cylinder_option"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    QUERY_ID_CONE_MATCHES_CYLINDER_OPTION,
    QUERY_ID_CYLINDER_MATCHES_CONE_OPTION,
    QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION,
)
EQUAL_VOLUME_OPTION_QUERY_IDS = SUPPORTED_QUERY_IDS
PROMPT_TASK_KEY = "equal_volume_option_label_query"
TASK_BINDING = VolumeEquivalenceTaskBinding(
    prompt_task_key=PROMPT_TASK_KEY,
    annotation_keys=OPTION_ANNOTATION_KEYS,
    answer_hint_key="answer_hint_option",
    answer_type="option_letter",
    render_scene=render_option_scene,
)
_OptionResolver = Callable[..., ResolvedProblem]


@dataclass(frozen=True)
class _OptionBranchProgram:
    source_cases: tuple[tuple[int, ...], ...]
    resolver: _OptionResolver
    branch_name: str

    def resolve(
        self,
        *,
        case: Sequence[int],
        option_count: int,
        instance_seed: int,
        params: Mapping[str, Any],
        branch_key: str,
    ) -> ResolvedProblem:
        return self.resolver(
            case,
            option_count=int(option_count),
            instance_seed=int(instance_seed),
            params=params,
            shuffle_namespace=f"{TASK_ID}.{branch_key}.option_distractors",
            label_namespace=f"{TASK_ID}.{branch_key}.answer_label",
        )


_PROGRAMS: dict[str, _OptionBranchProgram] = {
    QUERY_ID_CONE_MATCHES_CYLINDER_OPTION: (
        _OptionBranchProgram(
            source_cases=CONE_SOURCE_OPTION_CASES,
            resolver=resolve_cone_matching_cylinder_option,
            branch_name="cone_matches_cylinder_option",
        )
    ),
    QUERY_ID_CYLINDER_MATCHES_CONE_OPTION: (
        _OptionBranchProgram(
            source_cases=CYLINDER_SOURCE_OPTION_CASES,
            resolver=resolve_cylinder_matching_cone_option,
            branch_name="cylinder_matches_cone_option",
        )
    ),
    QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION: (
        _OptionBranchProgram(
            source_cases=CUBOID_SOURCE_OPTION_CASES,
            resolver=resolve_cuboid_matching_cylinder_option,
            branch_name="cuboid_matches_cylinder_option",
        )
    ),
}


def _resolve_problem(
    *,
    selected_branch: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> ResolvedProblem:
    generation_defaults, _render_defaults, _prompt_defaults = load_volume_equivalence_defaults(TASK_ID)
    option_count, option_count_probabilities = resolve_geometry_option_count(
        params=params,
        gen_defaults=generation_defaults,
        field_name="option_count",
        supported_counts=(4, 6),
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
    )
    program = _PROGRAMS.get(str(selected_branch))
    if program is None:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    case, case_probabilities = select_conversion_case(
        branch_name=program.branch_name,
        cases=program.source_cases,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{selected_branch}.case",
    )
    problem = program.resolve(
        case=case,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        params=params,
        branch_key=str(selected_branch),
    )
    return bind_option_metadata(
        problem,
        case_probabilities=case_probabilities,
        option_count_probabilities=option_count_probabilities,
    )


@register_task
class GeometryVolumeEquivalenceConversionEqualVolumeOptionLabelTask:
    """Select the option solid that has equal volume to the source solid."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_branch, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        problem = _resolve_problem(
            selected_branch=str(selected_branch),
            instance_seed=int(instance_seed),
            params=task_params,
        )
        parts = prepare_volume_equivalence_task_parts(
            public_identifier=TASK_ID,
            branch_key=str(selected_branch),
            branch_probabilities=branch_probabilities,
            problem=problem,
            binding=TASK_BINDING,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(
            prompt=parts.prompt,
            answer_gt=TypedValue(type="option_letter", value=str(problem.answer)),
            annotation_gt=TypedValue(type="bbox_map", value=dict(parts.annotation_value)),
            image=parts.image,
            image_id="img0",
            trace_payload=parts.trace_payload,
            task_versions=parts.task_versions,
            scene_id=parts.scene_id,
            query_id=str(selected_branch),
            prompt_variants=dict(parts.prompt_variants),
        )


__all__ = [
    "EQUAL_VOLUME_OPTION_QUERY_IDS",
    "GeometryVolumeEquivalenceConversionEqualVolumeOptionLabelTask",
    "OPTION_ANNOTATION_KEYS",
    "QUERY_ID_CONE_MATCHES_CYLINDER_OPTION",
    "QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION",
    "QUERY_ID_CYLINDER_MATCHES_CONE_OPTION",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "TASK_ID_EQUAL_VOLUME_OPTION",
]
