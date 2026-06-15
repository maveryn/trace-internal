"""Count reachable ore-top stacks along a height-constrained line."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import MinecraftObjectivePlan, minecraft_integer_attempt, run_minecraft_registered_task
from .shared.defaults import DEFAULT_BRANCH_ID
from .shared.sampling import resolve_reachable_resource_axes, sample_reachable_resource_scene


TASK_ID = "task_games__minecraft__reachable_ore_stack_count"
QUERY_ID = DEFAULT_BRANCH_ID
PROMPT_QUERY_KEY = "reachable_ore_stack_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _prepare_reachable_resource_objective(
    instance_seed,
    task_params,
    _selected_branch,
    _branch_probabilities,
    gen_defaults,
) -> MinecraftObjectivePlan:
    """Resolve line-reachability axes and bind stack-line sample construction."""

    axes = resolve_reachable_resource_axes(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace="games.minecraft.reachable_resource",
        params=task_params,
    )

    def construct_attempt(rng, resolved_axes):
        sample = sample_reachable_resource_scene(
            rng=rng,
            axes=resolved_axes,
            gen_defaults=gen_defaults,
            params=task_params,
        )
        return minecraft_integer_attempt(
            sample=sample,
            prompt_key=PROMPT_QUERY_KEY,
            object_description_key="object_description_reachable_stack_line",
            answer_hint_key=f"answer_hint_{PROMPT_QUERY_KEY}",
            annotation_hint_key=f"annotation_hint_{PROMPT_QUERY_KEY}",
            example_annotation=[[304, 252], [422, 222]],
            example_answer=2,
            counted_resource_kind=str(sample.counted_resource_kind),
            extra_query_params={
                "prompt_query_key": PROMPT_QUERY_KEY,
                "line_length": int(len(sample.stack_line_cells)),
                "line_length_probabilities": dict(resolved_axes.line_length_probabilities),
                "stack_line_cells": [list(cell) for cell in sample.stack_line_cells],
                "reachable_prefix_length": int(sample.reachable_prefix_length),
                "target_resource_kind": str(sample.target_resource_kind),
                "counted_resource_kind": str(sample.counted_resource_kind),
            },
        )

    return MinecraftObjectivePlan(
        axes=axes,
        attempt_namespace="games.minecraft.reachable_resource",
        construct_attempt=construct_attempt,
    )


@register_task
class GamesMinecraftReachableOreStackCountTask:
    """Count target-resource stack tops reachable along a height-constrained line."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    _default_branch = QUERY_ID
    _namespace = "games.minecraft.reachable_resource"
    _prepare_objective = staticmethod(_prepare_reachable_resource_objective)

    def generate(
        self,
        instance_seed,
        *,
        params=None,
        max_attempts=100,
    ):
        """Generate a reachable stack count task instance."""

        return run_minecraft_registered_task(
            self,
            int(instance_seed),
            params=params or {},
            max_attempts=int(max_attempts),
        )


__all__ = ["GamesMinecraftReachableOreStackCountTask"]
