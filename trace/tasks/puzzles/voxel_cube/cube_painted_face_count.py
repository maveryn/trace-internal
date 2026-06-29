"""Public voxel-cube task for painted exterior-face counts."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import VoxelBinding, VoxelCubeSceneTask
from .shared.annotations import scalar_bbox_annotation
from .shared.rendering import render_single_stack_scene
from .shared.sampling import sample_painted_face_dataset
from .shared.state import DOMAIN, SCENE_ID, CountDataset

TASK_ID = "task_puzzles__voxel_cube__cube_painted_face_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "cube_painted_face_count_query"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.cube_painted_face_count"
_PROMPT_QUERY_BY_PAINTED_QUERY = {
    "exterior_face_total": "painted_exterior_face_count",
    "exact_k_faces_cube_count": "exact_k_painted_faces_cube_count",
}


def _sample_case(params, generation_defaults, rng):
    """Construct one painted exterior-face count dataset."""

    return sample_painted_face_dataset(
        params=params,
        generation_defaults=generation_defaults,
        rng=rng,
    )


def _prompt_query_key(dataset: CountDataset) -> str:
    """Return the prompt query key for the sampled painted-face operation."""

    painted_query = str(dataset.semantic_params.get("painted_query", ""))
    if painted_query not in _PROMPT_QUERY_BY_PAINTED_QUERY:
        raise ValueError(f"unsupported voxel painted_query: {painted_query}")
    return str(_PROMPT_QUERY_BY_PAINTED_QUERY[painted_query])


def _bind_output(dataset: CountDataset, visual, selected_query, branch_probabilities):
    """Bind the painted-face count answer and structure bbox witness."""

    _ = (str(selected_query), dict(branch_probabilities))
    annotation_gt, projected_annotation, witness_symbolic = scalar_bbox_annotation(
        visual["rendered_scene"].stack_bbox_px,
        role="painted_voxel_structure",
    )
    return VoxelBinding(
        answer_gt=TypedValue(type="integer", value=int(dataset.answer_value)),
        annotation_gt=annotation_gt,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        semantic_params=dict(dataset.semantic_params),
        execution_fields={
            "annotation_policy": "scalar_bbox_painted_voxel_structure",
        },
    )


@register_task
class PuzzlesVoxelCubeCubePaintedFaceCountTask(VoxelCubeSceneTask):
    """Count exterior painted faces or cubes by exposed painted faces."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_task_key = PROMPT_TASK_KEY
    namespace = _NAMESPACE_BASE
    sample_builder = staticmethod(_sample_case)
    render_builder = staticmethod(render_single_stack_scene)
    prompt_query_key_resolver = staticmethod(_prompt_query_key)
    output_binder = staticmethod(_bind_output)

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one voxel painted-face count case."""

        output = super().generate(
            instance_seed,
            params=params,
            max_attempts=max_attempts,
        )
        return output


__all__ = [
    "PuzzlesVoxelCubeCubePaintedFaceCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
