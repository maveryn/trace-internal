"""Count loose dominoes above a reference pip sum."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import prepare_domino_recipe_count_objective, run_domino_lifecycle
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.rules import CANONICAL_DOMINOES, tile_sum
from .shared.sampling import CountedCandidateRecipe, random_orientation, sample_chain_with_end


TASK_ID = "task_games__dominoes__higher_sum_than_reference_count"
QUERY_ID = "higher_sum_than_reference_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _build_higher_sum_recipe(recipe_rng):
    """Choose a reference tile and predicate for larger candidate pip sums."""

    feasible_end_tiles = [tile for tile in CANONICAL_DOMINOES if 6 <= tile_sum(tile) <= 8]
    end_tile = feasible_end_tiles[int(recipe_rng.randrange(len(feasible_end_tiles)))]
    oriented_end = random_orientation(recipe_rng, tile=end_tile)
    oriented_chain = sample_chain_with_end(
        recipe_rng,
        end_tile=(int(oriented_end[0]), int(oriented_end[1])),
    )
    reference_sum = int(oriented_chain[-1][0] + oriented_chain[-1][1])
    return CountedCandidateRecipe(
        oriented_chain=oriented_chain,
        is_annotation_tile=lambda tile: tile_sum(tile) > int(reference_sum),
        reference_role="reference_sum",
        highlight_open_end=False,
        reference_sum=int(reference_sum),
    )


def _prepare_higher_sum_objective(
    instance_seed,
    task_params,
    _query_id,
    _query_probabilities,
    axes,
):
    """Resolve count axes and bind reference-sum comparison semantics."""

    return prepare_domino_recipe_count_objective(
        instance_seed=int(instance_seed),
        task_params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        axes=axes,
        prompt_query_key=QUERY_ID,
        attempt_namespace="games.dominoes.higher_sum",
        target_support_key="higher_sum_target_answer_support",
        target_fallback_support=DEFAULTS.higher_sum_target_answer_support,
        target_namespace="higher_sum.target_answer",
        minimum_candidate_count=lambda target: max(7, int(target)),
        candidate_namespace="higher_sum",
        build_recipe=_build_higher_sum_recipe,
        recipe_attempts=320,
        example_answer=3,
    )


@register_task
class GamesDominoesHigherSumThanReferenceCountTask:
    """Count loose dominoes with a larger pip sum than the reference tile."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        return run_domino_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            prepare_objective=_prepare_higher_sum_objective,
        )


__all__ = ["GamesDominoesHigherSumThanReferenceCountTask"]
