"""Public Tangram task for counting marked and edge-touching pieces."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_tangram_output, retry_tangram_generation
from .shared.annotations import bbox_set_for_piece_ids
from .shared.sampling import make_contact_sample, sample_rng
from .shared.state import DOMAIN, SCENE_ID, RenderedTangramScene, TangramSample

TASK_ID = "task_puzzles__tangram__contact_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "contact_count_query"
PROMPT_QUERY_KEY = "contact_count"
OBJECT_DESCRIPTION = "a Tangram-style assembly with one or two marked pieces"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.contact_count"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesTangramContactCountTask:
    """Count marked Tangram pieces and directly edge-touching neighbors."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate one Tangram contact-count task with bbox-set annotation."""

        return retry_tangram_generation(
            build_case=_build_contact_count_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


def _build_contact_count_case(
    instance_seed: int,
    params: Mapping[str, Any],
) -> TaskOutput:
    """Select the fixed branch, construct marked pieces, and bind the answer."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SINGLE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.branch",
    )
    rng = sample_rng(int(instance_seed), _NAMESPACE_BASE)
    sample, sampling_metadata = make_contact_sample(
        rng=rng,
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
    )
    _validate_contact_sample(sample)
    return build_tangram_output(
        source_id=TASK_ID,
        namespace=_NAMESPACE_BASE,
        sample=sample,
        answer_gt=TypedValue(type="integer", value=int(sample.contact_count)),
        annotation_builder=_contact_annotation,
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        task_params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        object_description=OBJECT_DESCRIPTION,
        task_trace_fields=_contact_trace_fields(sample),
        task_scene_relations=_contact_scene_relations(sample),
        sampling_metadata=sampling_metadata,
        instance_seed=int(instance_seed),
    )


def _validate_contact_sample(sample: TangramSample) -> None:
    """Validate the counted target/contact piece ids are unique and complete."""

    counted_ids = [*sample.target_piece_ids, *sample.contact_piece_ids]
    if len(set(counted_ids)) != len(counted_ids):
        raise ValueError("Tangram contact-count witnesses must be unique")
    if int(sample.contact_count) != len(counted_ids):
        raise ValueError("Tangram contact-count answer does not match witnesses")


def _contact_annotation(
    rendered_scene: RenderedTangramScene,
    sample: TangramSample,
):
    """Project marked pieces followed by edge-touching pieces to bbox_set."""

    return bbox_set_for_piece_ids(
        rendered_scene.piece_bbox_map,
        [*sample.target_piece_ids, *sample.contact_piece_ids],
    )


def _contact_trace_fields(sample: TangramSample) -> dict[str, Any]:
    """Return task-owned trace fields for the counted pieces."""

    supporting_piece_ids = [
        *[str(item) for item in sample.target_piece_ids],
        *[str(item) for item in sample.contact_piece_ids],
    ]
    return {
        "contact_piece_ids": [str(item) for item in sample.contact_piece_ids],
        "contact_count": int(sample.contact_count),
        "contact_count_support": [int(item) for item in sample.contact_count_support],
        "supporting_piece_ids": supporting_piece_ids,
    }


def _contact_scene_relations(sample: TangramSample) -> dict[str, Any]:
    """Return task-owned symbolic relation metadata for contact counting."""

    return {
        "contact_piece_ids": [str(item) for item in sample.contact_piece_ids],
        "supporting_piece_ids": [
            *[str(item) for item in sample.target_piece_ids],
            *[str(item) for item in sample.contact_piece_ids],
        ],
    }


__all__ = [
    "PROMPT_QUERY_KEY",
    "PuzzlesTangramContactCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
