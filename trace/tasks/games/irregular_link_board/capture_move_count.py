"""Count one-jump capture destinations for a marked irregular-link-board piece."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.scene import SCENE_ID, build_components, resolve_axes, sample_capture_scene


TASK_ID = "task_games__irregular_link_board__capture_move_count"
SUPPORTED_QUERY_IDS = ("capture_move_count",)
CAPTURE_BOARD_SIZE_SUPPORT = (5, 6)

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesIrregularLinkBoardCaptureMoveCountTask:
    """Count legal jump-capture landing points for one X-marked piece."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        params = dict(params or {})
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        axes = resolve_axes(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            namespace=TASK_ID,
            board_size_support_key="capture_board_size_support",
            fallback_board_size_support=CAPTURE_BOARD_SIZE_SUPPORT,
        )
        sampled = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled = sample_capture_scene(rng=rng, axes=axes, gen_defaults=_GEN_DEFAULTS)
            except ValueError:
                continue
            break
        if sampled is None:
            raise RuntimeError(f"{TASK_ID} failed to generate after {max_attempts} attempts")

        components = build_components(
            query_id=str(query_id),
            sampled=sampled,
            axes=axes,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            namespace=TASK_ID,
        )
        components.trace_payload["query_spec"]["params"]["query_id_probabilities"] = dict(query_id_probabilities)
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=TypedValue(type="integer", value=int(components.answer_value)),
            annotation_gt=TypedValue(type=str(components.annotation_type), value=components.annotation_value),
            image=components.image,
            image_id="img0",
            trace_payload=dict(components.trace_payload),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(components.query_id),
        )


__all__ = ["GamesIrregularLinkBoardCaptureMoveCountTask"]
