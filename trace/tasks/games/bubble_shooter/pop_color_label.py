"""Choose the labeled Bubble-shooter color option that would make bubbles pop."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.sampling import uniform_choice
from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults

from ._lifecycle import (
    BubbleShooterObjectivePlan,
    bbox_set_attempt,
    resolve_bubble_shooter_board_axis_specs,
    run_bubble_shooter_lifecycle,
)
from .shared.defaults import SCENE_ID
from .shared.sampling import (
    ResolvedBubbleShooterSceneAxes,
    bubble_entity_ids_for_coords,
    resolve_bubble_shooter_integer_axis,
    sample_pop_color_state,
)
from .shared.state import BUBBLE_OPTION_LABELS


TASK_ID = "task_games__bubble_shooter__pop_color_label"
QUERY_ID = "pop_color_label"
PROMPT_QUERY_KEY = "pop_color_label"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
ROW_COUNT_SUPPORT = (7, 8, 9)
COL_COUNT_SUPPORT = (8, 9, 10)
OPTION_COUNT_SUPPORT = (4, 5, 6)
LABEL_SUPPORT = BUBBLE_OPTION_LABELS
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _string_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    """Resolve the task-owned option-label support."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    if isinstance(raw, str):
        values = (raw,)
    else:
        values = tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> tuple[str, Dict[str, float], Tuple[str, ...]]:
    """Resolve the requested answer label for this option-label objective."""

    support = _string_support(params, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}, support

    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(uniform_choice(rng, support)), probabilities, support


def _prepare_pop_color_label_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    _query_id: str,
    _query_probabilities: Mapping[str, float],
) -> BubbleShooterObjectivePlan:
    """Prepare the label target and color-option attempt for one sample."""

    board_axes, board_query_params = resolve_bubble_shooter_board_axis_specs(
        instance_seed=int(instance_seed),
        task_params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        row_count_support=ROW_COUNT_SUPPORT,
        col_count_support=COL_COUNT_SUPPORT,
    )
    option_count_axis = resolve_bubble_shooter_integer_axis(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=OPTION_COUNT_SUPPORT,
        namespace=f"{TASK_ID}.option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )
    target_label, target_label_probabilities, target_label_support = _resolve_label_choice(
        instance_seed=int(instance_seed),
        params=params,
        support_key="pop_color_label_support",
        explicit_key="target_label",
        fallback_support=LABEL_SUPPORT,
        namespace=f"{TASK_ID}.target_label",
        balanced_flag_key="balanced_target_label_sampling",
    )
    option_count = max(int(option_count_axis.value), BUBBLE_OPTION_LABELS.index(str(target_label)) + 1)

    def construct_attempt(rng, scene_axes: ResolvedBubbleShooterSceneAxes):
        state = sample_pop_color_state(
            rng=rng,
            scene_axes=scene_axes,
            board_axes=board_axes,
            target_option_label=str(target_label),
            option_count=int(option_count),
        )
        answer_options = [option for option in state.option_specs if option.is_answer]
        if len(answer_options) != 1 or str(answer_options[0].label) != str(target_label):
            raise ValueError("Bubble-shooter color-option state has ambiguous answer")
        annotation_entity_ids = bubble_entity_ids_for_coords(state.outcome.popped_coords)
        return bbox_set_attempt(
            state=state,
            answer_gt=TypedValue(type="string", value=str(target_label)),
            annotation_entity_ids=annotation_entity_ids,
            execution_extra={"target_label": str(target_label)},
        )

    return BubbleShooterObjectivePlan(
        attempt_namespace="games.bubble_shooter.pop_color_label",
        prompt_query_key=PROMPT_QUERY_KEY,
        query_params={
            "target_label": str(target_label),
            "target_label_support": [str(value) for value in target_label_support],
            "target_label_probabilities": dict(target_label_probabilities),
            "option_count": int(option_count),
            "option_count_support": [int(value) for value in option_count_axis.support],
            "option_count_probabilities": dict(option_count_axis.probabilities),
            **dict(board_query_params),
        },
        construct_attempt=construct_attempt,
    )


@register_task
class GamesBubbleShooterPopColorLabelTask:
    """Choose the color option that would pop bubbles at the marked landing target."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_bubble_shooter_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_pop_color_label_objective,
            domain=self.domain,
        )


__all__ = ["GamesBubbleShooterPopColorLabelTask"]
