"""Count dominoes playable after the forced first play."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import DominoObjectivePlan, domino_bbox_set_attempt, resolve_domino_count_axes, run_domino_lifecycle
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.prompts import domino_integer_json_examples, domino_output_slots
from .shared.rules import PIP_VALUES, can_connect, canonical_tile
from .shared.sampling import (
    build_sampled_scene,
    build_scene_instances,
    candidate_pool_for_chain,
    sample_chain_with_end,
    tile_id_for_canonical,
)
from .shared.state import DominoSceneAxes


TASK_ID = "task_games__dominoes__second_play_candidate_count"
QUERY_ID = "second_play_candidate_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _sample_second_play_candidate_scene(rng, *, candidate_count: int, target_answer: int):
    """Construct one unique first play followed by target-count second plays."""

    for _ in range(360):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        bridge_options = [value for value in PIP_VALUES if int(value) != int(open_end_value)]
        bridge_value = int(bridge_options[int(rng.randrange(len(bridge_options)))])
        connector_options = [
            value for value in PIP_VALUES
            if int(value) not in {int(open_end_value), int(bridge_value)}
        ]
        if not connector_options:
            continue
        connector_value = int(connector_options[int(rng.randrange(len(connector_options)))])
        first_tile = canonical_tile(int(open_end_value), int(bridge_value))
        try:
            oriented_chain = sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value), int(bridge_value)),
            )
        except ValueError:
            continue
        candidate_pool = set(candidate_pool_for_chain(oriented_chain))
        if first_tile not in candidate_pool:
            continue
        second_pool = [
            tile for tile in candidate_pool
            if tile != first_tile
            and can_connect(tile, int(bridge_value))
            and not can_connect(tile, int(open_end_value))
        ]
        filler_pool = [
            tile for tile in candidate_pool
            if tile != first_tile
            and not can_connect(tile, int(bridge_value))
            and not can_connect(tile, int(open_end_value))
        ]
        if int(len(second_pool)) < int(target_answer):
            continue
        if int(len(filler_pool)) < int(candidate_count - target_answer - 1):
            continue
        annotation_tiles = list(rng.sample(second_pool, int(target_answer)))
        selected_candidates = [first_tile] + annotation_tiles + list(rng.sample(filler_pool, int(candidate_count - target_answer - 1)))
        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role="reference_end",
            highlight_open_end=True,
        )
        first_step_tile_id = tile_id_for_canonical(candidate_instances, first_tile)
        candidate_flags = {
            str(tile.tile_id): {
                "is_unique_first_play": bool(str(tile.tile_id) == str(first_step_tile_id)),
                "is_second_play_candidate": bool(str(tile.tile_id) in set(annotation_tile_ids)),
            }
            for tile in candidate_instances
        }
        return build_sampled_scene(
            chain_instances=chain_instances,
            candidate_instances=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            first_step_tile_id=first_step_tile_id,
            bridge_value=int(bridge_value),
            candidate_extra_flags=candidate_flags,
        )
    raise ValueError("unable to sample second-play candidate domino scene")


def _prepare_second_play_objective(
    instance_seed,
    task_params,
    _query_id,
    _query_probabilities,
    axes: DominoSceneAxes,
):
    """Resolve axes and bind forced-first-play follow-up semantics."""

    count_axes = resolve_domino_count_axes(
        instance_seed=int(instance_seed),
        task_params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        axes=axes,
        target_support_key="second_play_candidate_target_answer_support",
        target_fallback_support=DEFAULTS.second_play_candidate_target_answer_support,
        target_namespace="second_play.target_answer",
        minimum_candidate_count=lambda target: max(7, int(target) + 1),
        candidate_namespace="second_play",
    )
    json_example, json_example_answer_only = domino_integer_json_examples(answer_value=2)
    prompt_dynamic_slots = domino_output_slots(
        prompt_query_key=QUERY_ID,
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
    )

    def construct_attempt(rng, _axes: DominoSceneAxes):
        sample = _sample_second_play_candidate_scene(
            rng,
            candidate_count=int(count_axes.candidate_axis.value),
            target_answer=int(count_axes.target_axis.value),
        )
        return domino_bbox_set_attempt(
            sample=sample,
            answer_gt=TypedValue(type="integer", value=int(sample.answer_value)),
            execution_extra={"target_answer": int(sample.answer_value)},
        )

    return DominoObjectivePlan(
        attempt_namespace="games.dominoes.second_play",
        prompt_query_key=QUERY_ID,
        query_params=dict(count_axes.query_params),
        prompt_dynamic_slots=prompt_dynamic_slots,
        construct_attempt=construct_attempt,
    )


@register_task
class GamesDominoesSecondPlayCandidateCountTask:
    """Count remaining loose dominoes that can connect after the unique first play."""

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
            prepare_objective=_prepare_second_play_objective,
        )


__all__ = ["GamesDominoesSecondPlayCandidateCountTask"]
