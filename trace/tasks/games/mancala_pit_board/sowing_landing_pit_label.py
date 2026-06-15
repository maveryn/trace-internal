"""Select the pit where the last Mancala seed lands after one sowing move."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import MancalaAttemptResult, MancalaObjectivePlan, MancalaSingleQueryTaskBase, build_mancala_attempt_result, run_mancala_registered_task
from .shared.annotations import pit_bbox_set_annotation
from .shared.prompts import make_mancala_prompt_slots
from .shared.rules import pit_index, pit_label, sow_counts
from .shared.sampling import random_initial_counts, resolve_mancala_label_axis
from .shared.state import DEFAULTS, LABELS, SCENE_ID, MancalaSample, MancalaSceneAxes


TASK_ID = "task_games__mancala_pit_board__sowing_landing_pit_label"
PROMPT_SLOTS = make_mancala_prompt_slots(
    prompt_query_key="sowing_landing_pit_label",
    answer_hint_key="answer_hint_sowing_landing_pit_label",
    annotation_hint_key="annotation_hint_sowing_landing_pit_label",
    example_annotation=[[420, 140, 520, 204]],
    example_answer="G",
)


def _construct_landing_sample(*, rng: Any, axes: MancalaSceneAxes, target_label: str) -> MancalaSample:
    """Place a source pit so the final sown seed lands in the target label."""

    target_index = pit_index(str(target_label))
    min_source = int(axes.min_source_seed_count)
    max_source = int(axes.max_source_seed_count)
    viable_seed_counts = [
        seed_count
        for seed_count in range(max(1, min_source), max_source + 1)
        if seed_count <= 11
    ]
    rng.shuffle(viable_seed_counts)
    if not viable_seed_counts:
        raise ValueError("no viable Mancala source seed counts")
    source_seed_count = int(viable_seed_counts[0])
    source_index = (int(target_index) - int(source_seed_count)) % len(LABELS)
    counts = random_initial_counts(rng=rng, axes=axes)
    counts[int(source_index)] = int(source_seed_count)
    final_counts, path = sow_counts(counts, int(source_index))
    if not path or int(path[-1]) != int(target_index):
        raise ValueError("constructed Mancala landing mismatch")
    return MancalaSample(
        initial_counts=tuple(int(value) for value in counts),
        final_counts=tuple(int(value) for value in final_counts),
        source_index=int(source_index),
        sowing_path_indices=tuple(int(value) for value in path),
        landing_index=int(path[-1]),
        target_index=None,
        construction_mode="target_conditioned_last_seed_landing_label",
    )


def _prepare_landing_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query_id: str,
    _branch_probabilities: Mapping[str, float],
    _axes: MancalaSceneAxes,
    gen_defaults: Mapping[str, Any],
) -> MancalaObjectivePlan:
    """Resolve the landing-label target and bind landing-task construction."""

    target_axis = resolve_mancala_label_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=gen_defaults,
        namespace=f"{SCENE_ID}.landing.target_label",
        support_key="target_landing_label_support",
        explicit_key="target_landing_label",
        weights_key="target_landing_label_weights",
        balance_flag_key="balanced_target_landing_label_sampling",
        fallback_support=DEFAULTS.target_landing_label_support,
    )

    def construct_attempt(rng: Any, axes: MancalaSceneAxes) -> MancalaAttemptResult:
        """Bind the final landing pit label, annotation, and trace fields."""

        sample = _construct_landing_sample(
            rng=rng,
            axes=axes,
            target_label=str(target_axis.value),
        )
        landing_label = pit_label(sample.landing_index)
        landing_pit_id = f"pit_{landing_label}"
        return build_mancala_attempt_result(
            answer_gt=TypedValue(type="string", value=str(landing_label)),
            sample=sample,
            prompt_slots=PROMPT_SLOTS,
            build_annotation=lambda rendered: pit_bbox_set_annotation(
                rendered=rendered,
                pit_ids=[landing_pit_id],
                role_name="landing_pit",
            ),
            selected_query_id=str(selected_query_id),
            annotation_entity_ids={"landing_pit": landing_pit_id},
            extra_execution_fields={
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "target_landing_label": str(target_axis.value),
            },
            extra_query_params={
                "target_landing_label": str(target_axis.value),
                "target_landing_label_support": list(target_axis.support),
                "target_landing_label_probabilities": dict(target_axis.probabilities),
            },
            relations_extra={
                "source_pit": str(pit_label(sample.source_index)),
                "target_pit": None,
                "landing_pit": str(landing_label),
            },
        )

    return MancalaObjectivePlan(
        attempt_namespace=f"{SCENE_ID}.landing",
        construct_attempt=construct_attempt,
    )


@register_task
class GamesMancalaPitBoardSowingLandingPitLabelTask(MancalaSingleQueryTaskBase):
    """Select the pit where the last Mancala seed lands after one sowing move."""

    task_id = TASK_ID
    _namespace = f"{SCENE_ID}.landing"
    _prepare_objective = staticmethod(_prepare_landing_objective)

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_mancala_registered_task(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesMancalaPitBoardSowingLandingPitLabelTask", "TASK_ID"]
