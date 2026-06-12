"""Choose the labeled Connect Four column that wins immediately."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.connect_four.shared.annotations import cell_bboxes_for_coords
from trace.tasks.games.connect_four.shared.output import common_trace_params, common_trace_sections
from trace.tasks.games.connect_four.shared.prompts import (
    build_connect_four_prompt_artifacts,
    connect_four_object_description,
    connect_four_output_slots,
    connect_four_rule_slots,
    json_examples_for_label_answer,
)
from trace.tasks.games.connect_four.shared.rendering import render_connect_four_sample
from trace.tasks.games.connect_four.shared.sampling import (
    resolve_connect_four_scene_axes,
    sample_winning_column_label_scene,
)
from trace.tasks.games.connect_four.shared.state import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__connect_four__winning_move_column_label"
QUERY_ID = "winning_move_column_label"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesConnectFourWinningMoveColumnLabelTask:
    """Return the visible column label for the immediate winning drop."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        axes = resolve_connect_four_scene_axes(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            namespace_suffix=str(selected_query),
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.connect_four.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_winning_column_label_scene(
                    rng=rng,
                    axes=axes,
                    params=task_params,
                    instance_seed=int(instance_seed),
                    gen_defaults=_GEN_DEFAULTS,
                )
            except ValueError as exc:
                last_error = exc
                continue

            rendered_context = render_connect_four_sample(
                sample=sample,
                params=task_params,
                instance_seed=int(instance_seed),
                marked_square=sample.evaluation.annotation_coords[0],
                column_labels=sample.column_labels,
            )
            annotation_bboxes = cell_bboxes_for_coords(
                rendered_context.rendered_scene,
                sample.evaluation.annotation_coords,
            )
            annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
            json_example, json_example_answer_only = json_examples_for_label_answer()
            dynamic_slots = {
                "object_description": connect_four_object_description(str(sample.scene_variant)),
                **connect_four_rule_slots(current_player=int(sample.current_player)),
                **connect_four_output_slots(
                    prompt_query_key=PROMPT_QUERY_KEY,
                    json_example=json_example,
                    json_example_answer_only=json_example_answer_only,
                ),
            }
            _prompt_defaults, prompt_artifacts = build_connect_four_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=PROMPT_QUERY_KEY,
                dynamic_slots=dynamic_slots,
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="string", value=str(sample.answer_label))
            query_params = {
                "answer_label": str(sample.answer_label),
                "answer_column": int(sample.answer_column),
                "answer_support": [str(label) for label in sample.column_labels],
                "query_id_probabilities": dict(query_probabilities),
                "threat_kind": str(sample.threat_kind),
                "threat_kind_probabilities": dict(sample.threat_kind_probabilities),
            }
            query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=str(selected_query),
                params=common_trace_params(axes=axes, sample=sample, extra_params=query_params),
            )
            trace_payload = common_trace_sections(
                axes=axes,
                sample=sample,
                rendered_context=rendered_context,
                annotation_artifacts=annotation_artifacts,
                query_spec=query_spec,
                execution_extra={
                    "query_id": str(selected_query),
                    "answer_label": str(sample.answer_label),
                    "answer_column": int(sample.answer_column),
                    "answer_support": [str(label) for label in sample.column_labels],
                    "column_labels": [str(label) for label in sample.column_labels],
                    "winning_line_coords": [[int(row), int(col)] for row, col in sample.winning_line_coords],
                    "threat_kind": str(sample.threat_kind),
                    "answer": str(answer_gt.value),
                },
            )
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_artifacts.annotation_gt,
                image=rendered_context.image,
                image_id="img0",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(selected_query),
            )

        raise RuntimeError(f"{TASK_ID} failed to generate a Connect Four winning-column scene") from last_error


__all__ = ["GamesConnectFourWinningMoveColumnLabelTask"]
