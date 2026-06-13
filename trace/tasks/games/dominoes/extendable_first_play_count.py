"""Count first plays that leave a follow-up domino move."""

from __future__ import annotations

from typing import List, Tuple

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import DominoObjectivePlan, domino_bbox_set_attempt, resolve_domino_count_axes, run_domino_lifecycle
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.prompts import domino_integer_json_examples, domino_output_slots
from .shared.rules import PIP_VALUES, can_connect, canonical_tile, new_open_end
from .shared.sampling import build_sampled_scene, build_scene_instances, candidate_pool_for_chain, sample_chain_with_end
from .shared.state import DominoSceneAxes


TASK_ID = "task_games__dominoes__extendable_first_play_count"
QUERY_ID = "extendable_first_play_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _sample_extendable_first_play_scene(rng, *, candidate_count: int, target_answer: int):
    """Construct first-play candidates that each have at least one follow-up play."""

    target_count = int(target_answer)
    for _ in range(420):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        bridge_values = [int(value) for value in PIP_VALUES if int(value) != int(open_end_value)]
        if int(target_count) > int(len(bridge_values)):
            continue
        target_bridges = list(rng.sample(bridge_values, int(target_count)))
        remaining_bridges = [value for value in bridge_values if int(value) not in set(target_bridges)]
        max_dead_count = max(0, min(len(remaining_bridges) - 1, int(candidate_count) - (2 * int(target_count))))
        dead_count = 0 if max_dead_count <= 0 else int(rng.randrange(max_dead_count + 1))
        dead_bridges = list(rng.sample(remaining_bridges, int(dead_count))) if int(dead_count) > 0 else []
        connector_options = [
            value for value in PIP_VALUES
            if int(value) not in {int(open_end_value), *[int(v) for v in target_bridges], *[int(v) for v in dead_bridges]}
        ]
        if not connector_options:
            continue
        connector_value = int(connector_options[int(rng.randrange(len(connector_options)))])
        try:
            oriented_chain = sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value), *target_bridges, *dead_bridges),
            )
        except ValueError:
            continue
        candidate_pool = set(candidate_pool_for_chain(oriented_chain))
        annotation_tiles = [canonical_tile(int(open_end_value), int(bridge)) for bridge in target_bridges]
        support_tiles = [canonical_tile(int(bridge), int(bridge)) for bridge in target_bridges]
        dead_first_tiles = [canonical_tile(int(open_end_value), int(bridge)) for bridge in dead_bridges]
        required_tiles = list(annotation_tiles) + list(support_tiles) + list(dead_first_tiles)
        if any(tile not in candidate_pool for tile in required_tiles):
            continue
        required_set = set(required_tiles)
        dead_value_set = {int(value) for value in dead_bridges}
        filler_pool = [
            tile for tile in candidate_pool
            if tile not in required_set
            and not can_connect(tile, int(open_end_value))
            and not ({int(tile[0]), int(tile[1])} & dead_value_set)
        ]
        filler_count = int(candidate_count) - int(len(required_tiles))
        if int(filler_count) < 0 or int(len(filler_pool)) < int(filler_count):
            continue
        selected_candidates = required_tiles + list(rng.sample(filler_pool, int(filler_count)))

        exact_extendable: List[Tuple[int, int]] = []
        selected_set = [canonical_tile(int(tile[0]), int(tile[1])) for tile in selected_candidates]
        for tile in selected_set:
            if not can_connect(tile, int(open_end_value)):
                continue
            next_open = new_open_end(tile, int(open_end_value))
            has_followup = any(other != tile and can_connect(other, int(next_open)) for other in selected_set)
            if bool(has_followup):
                exact_extendable.append(tile)
        if {canonical_tile(*tile) for tile in exact_extendable} != {canonical_tile(*tile) for tile in annotation_tiles}:
            continue

        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role="reference_end",
            highlight_open_end=True,
        )
        candidate_flags = {
            str(tile.tile_id): {"is_extendable_first_play": bool(str(tile.tile_id) in set(annotation_tile_ids))}
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
            candidate_extra_flags=candidate_flags,
        )
    raise ValueError("unable to sample extendable first-play domino scene")


def _prepare_extendable_first_play_objective(
    instance_seed,
    task_params,
    _query_id,
    _query_probabilities,
    axes: DominoSceneAxes,
):
    """Resolve axes and bind first-play-with-follow-up semantics."""

    count_axes = resolve_domino_count_axes(
        instance_seed=int(instance_seed),
        task_params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        axes=axes,
        target_support_key="extendable_first_play_target_answer_support",
        target_fallback_support=DEFAULTS.extendable_first_play_target_answer_support,
        target_namespace="extendable_first_play.target_answer",
        minimum_candidate_count=lambda target: max(7, int(target) * 2),
        candidate_namespace="extendable_first_play",
    )
    json_example, json_example_answer_only = domino_integer_json_examples(answer_value=2)
    prompt_dynamic_slots = domino_output_slots(
        prompt_query_key=QUERY_ID,
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
    )

    def construct_attempt(rng, _axes: DominoSceneAxes):
        sample = _sample_extendable_first_play_scene(
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
        attempt_namespace="games.dominoes.extendable_first_play",
        prompt_query_key=QUERY_ID,
        query_params=dict(count_axes.query_params),
        prompt_dynamic_slots=prompt_dynamic_slots,
        construct_attempt=construct_attempt,
    )


@register_task
class GamesDominoesExtendableFirstPlayCountTask:
    """Count loose dominoes that can be played first and still allow a second play."""

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
            prepare_objective=_prepare_extendable_first_play_objective,
        )


__all__ = ["GamesDominoesExtendableFirstPlayCountTask"]
