"""Public word-search task for counting listed words present in the grid."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.sampling import integer_range_choice
from trace.tasks.registry import register_task

from ._lifecycle import make_word_search_binding, run_word_search_single_query_case
from .shared.annotations import segment_set_for_cell_pairs
from .shared.defaults import get_int_param, get_int_range
from .shared.sampling import (
    present_word_segments,
    resolve_scene_variant,
    sample_present_word_count_dataset,
)
from .shared.state import DOMAIN, SCENE_ID

TASK_ID = "task_puzzles__word_search__search_present_word_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "search_present_word_count_query"
PROMPT_QUERY_KEY = "search_present_word_count"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.search_present_word_count"


def _build_present_word_scene(params, generation_defaults, rng):
    """Construct one word-bank presence count dataset."""

    scene_variant, scene_probs = resolve_scene_variant(params, generation_defaults, rng)
    bank_size = get_int_param(params, generation_defaults, "word_bank_size", 5)
    count_min, count_max = get_int_range(
        params,
        generation_defaults,
        min_key="present_count_min",
        max_key="present_count_max",
        fallback_min=1,
        fallback_max=5,
    )
    count_max = min(int(count_max), int(bank_size))
    present_count, _probabilities = integer_range_choice(rng, count_min, count_max)
    return sample_present_word_count_dataset(
        params=params,
        generation_defaults=generation_defaults,
        rng=rng,
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probs),
        present_count=int(present_count),
        bank_size=int(bank_size),
    )


def _bind_present_word_output(dataset, visual):
    """Bind integer count and segment-set over each present word occurrence."""

    answer_value = int(dataset.answer_value)
    if len(dataset.present_words) != answer_value:
        raise ValueError("present words do not match answer")
    return make_word_search_binding(
        answer_type="integer",
        answer_value=answer_value,
        annotation_result=segment_set_for_cell_pairs(
            visual["rendered_scene"].cell_centers_px,
            present_word_segments(dataset),
        ),
        semantic_params={
            "answer_schema": "integer_count",
        },
        execution_fields={
            "annotation_policy": "segment_set_present_word_start_to_end",
            "supporting_annotation_source": "cell_centers_px",
        },
    )


@register_task
class PuzzlesWordSearchPresentWordCountTask:
    """Count word-bank entries that are actually present in the grid."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one present-word-count case."""

        return run_word_search_single_query_case(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            namespace=_NAMESPACE_BASE,
            prompt_task_key=PROMPT_TASK_KEY,
            prompt_query_key=PROMPT_QUERY_KEY,
            instance_seed=int(instance_seed),
            params=params,
            sample_builder=_build_present_word_scene,
            output_binder=_bind_present_word_output,
            attempt_limit=int(max_attempts),
        )
