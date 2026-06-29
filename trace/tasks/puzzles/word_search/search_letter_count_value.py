"""Public word-search task for counting one target letter."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.sampling import integer_range_choice
from trace.tasks.registry import register_task

from ._lifecycle import make_word_search_binding, run_word_search_single_query_case
from .shared.annotations import bbox_set_for_cells
from .shared.defaults import get_int_range
from .shared.sampling import resolve_scene_variant, sample_letter_count_dataset
from .shared.state import DOMAIN, SCENE_ID

TASK_ID = "task_puzzles__word_search__search_letter_count_value"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "search_letter_count_value_query"
PROMPT_QUERY_KEY = "search_letter_count_value"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.search_letter_count_value"


def _build_letter_count_scene(params, generation_defaults, rng):
    """Construct one exact target-letter count dataset."""

    scene_variant, scene_probs = resolve_scene_variant(params, generation_defaults, rng)
    count_min, count_max = get_int_range(
        params,
        generation_defaults,
        min_key="target_count_min",
        max_key="target_count_max",
        fallback_min=1,
        fallback_max=8,
    )
    target_count, _probabilities = integer_range_choice(rng, count_min, count_max)
    return sample_letter_count_dataset(
        params=params,
        generation_defaults=generation_defaults,
        rng=rng,
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probs),
        target_count=int(target_count),
    )


def _bind_letter_count_output(dataset, visual):
    """Bind integer count and bbox-set over all matching letter cells."""

    answer_value = int(dataset.answer_value)
    if len(dataset.target_cells) != answer_value:
        raise ValueError("word-search letter-count cells do not match answer")
    return make_word_search_binding(
        answer_type="integer",
        answer_value=answer_value,
        annotation_result=bbox_set_for_cells(
            visual["rendered_scene"].item_bbox_map,
            dataset.target_cells,
        ),
        semantic_params={
            "answer_schema": "integer_count",
            "target_letter": str(dataset.target_letter),
        },
        execution_fields={
            "annotation_policy": "bbox_set_cells_matching_target_letter",
        },
    )


@register_task
class PuzzlesWordSearchLetterCountValueTask:
    """Count all cells containing the named target letter."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one target-letter count case."""

        return run_word_search_single_query_case(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            namespace=_NAMESPACE_BASE,
            prompt_task_key=PROMPT_TASK_KEY,
            prompt_query_key=PROMPT_QUERY_KEY,
            instance_seed=int(instance_seed),
            params=params,
            sample_builder=_build_letter_count_scene,
            output_binder=_bind_letter_count_output,
            attempt_limit=int(max_attempts),
        )


__all__ = ["PuzzlesWordSearchLetterCountValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
