"""Sokoban-style game tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Tuple

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.annotation_artifacts import bbox_set_annotation_artifacts
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.layout import attach_games_unit_size_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from .shared.rendering import (
    SUPPORTED_SOKOBAN_QUERY_IDS,
    SUPPORTED_SOKOBAN_SCENE_VARIANTS,
    build_sokoban_dataset,
    render_sokoban_scene,
    resolve_sokoban_render_params,
)
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "sokoban"
INTERNAL_TASK_ID = "games_sokoban_grid_internal"
PATH_VALIDITY_SEQUENCE_TASK_ID = "task_games__sokoban__path_validity_sequence_label"
SHORTEST_PATH_SEQUENCE_TASK_ID = "task_games__sokoban__shortest_path_sequence_label"
NEAREST_COUNTERPART_TASK_ID = "task_games__sokoban__nearest_counterpart_label"
BOX_TARGET_MANHATTAN_RANK_TASK_ID = "task_games__sokoban__box_target_manhattan_rank_label"
SOKOBAN_SCENE_ID = "sokoban"

PATH_VALIDITY_SEQUENCE_QUERY_IDS: Tuple[str, ...] = (
    "valid_path_sequence_label",
    "blocked_path_sequence_label",
)
SHORTEST_PATH_SEQUENCE_QUERY_IDS: Tuple[str, ...] = ("shortest_path_sequence_label",)
NEAREST_COUNTERPART_QUERY_IDS: Tuple[str, ...] = (
    "nearest_target_for_marked_box_label",
    "box_closest_to_marked_target_label",
)
BOX_TARGET_MANHATTAN_RANK_QUERY_IDS: Tuple[str, ...] = ("box_target_manhattan_rank_label",)

_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_SOKOBAN_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_SOKOBAN_SCENE_VARIANTS
_REASONING_LOAD_BY_QUERY = {
    "shortest_path_sequence_label": 0.55,
    "valid_path_sequence_label": 0.50,
    "blocked_path_sequence_label": 0.48,
    "nearest_target_for_marked_box_label": 0.42,
    "box_closest_to_marked_target_label": 0.42,
    "box_target_manhattan_rank_label": 0.56,
}
_SCENE_LOAD = {
    "warehouse_classic": 0.22,
    "paper_grid": 0.20,
    "cool_room": 0.24,
}

_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=INTERNAL_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="sokoban", apply_prob=0.0)


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=INTERNAL_TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
    )


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported_queries: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    return resolve_games_query_id(
        task_id=INTERNAL_TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=[str(query) for query in supported_queries],
    )


def _query_family(query_id: str) -> str:
    if str(query_id) in (*PATH_VALIDITY_SEQUENCE_QUERY_IDS, *SHORTEST_PATH_SEQUENCE_QUERY_IDS):
        return "path_sequence_label"
    if str(query_id) in (*NEAREST_COUNTERPART_QUERY_IDS, *BOX_TARGET_MANHATTAN_RANK_QUERY_IDS):
        return "box_target_relation_label"
    raise ValueError(f"unsupported Sokoban query id: {query_id}")


def _resolve_option_count(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    family = _query_family(str(query_id))
    if str(family) == "path_sequence_label":
        support_key = "path_option_count_support"
        fallback = (4, 6)
        balance_key = "balanced_path_option_count_sampling"
    else:
        support_key = "relation_option_count_support"
        fallback = (4, 5, 6)
        balance_key = "balanced_relation_option_count_sampling"
    option_count, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="option_count",
        fallback_support=fallback,
        namespace=f"{INTERNAL_TASK_ID}.{str(family)}.option_count",
        balanced_flag_key=str(balance_key),
        namespace_support_permutation=True,
    )
    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=fallback,
    )
    return int(option_count), tuple(int(value) for value in support), dict(probabilities)


def _entity_description(dataset: Mapping[str, Any]) -> str:
    entity_type = str(dataset.get("query_entity_type", "player"))
    entity_label = str(dataset.get("query_entity_label", "player"))
    if entity_type == "box":
        return f"the marked box {entity_label}"
    return "the player"


def _query_slot_values(dataset: Mapping[str, Any]) -> Dict[str, str]:
    support = dataset.get("relation_support", {})
    if not isinstance(support, Mapping):
        support = {}
    return {
        "query_entity_description": _entity_description(dataset),
        "rank_word": str(support.get("rank_word", "requested")),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _cell_id(cell: Any) -> str:
    row, col = tuple(cell)
    return f"cell_r{int(row)}_c{int(col)}"


class _SokobanGridBaseTask:
    """Base generator for public Sokoban grid tasks."""

    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids: Tuple[str, ...]

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probabilities = _resolve_query_id(
            params,
            instance_seed=int(instance_seed),
            supported_queries=tuple(self.supported_query_ids),
        )
        if query_id not in _SUPPORTED_QUERY_IDS:
            raise ValueError(f"unsupported Sokoban query_id: {query_id}")
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        option_count, option_count_support, option_count_probabilities = _resolve_option_count(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
        )
        dataset_params = dict(params)
        dataset_params["option_count"] = int(option_count)
        dataset = build_sokoban_dataset(
            mode=str(query_id),
            params=dataset_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace_key=INTERNAL_TASK_ID,
        )
        render_params = resolve_sokoban_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.sokoban_grid_background",
        )
        render_params = replace(
            render_params,
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            style_overrides={
                "panel": tuple(int(value) for value in scene_style.panel_fill_rgb),
                "floor": tuple(int(value) for value in scene_style.option_fill_rgb),
                "floor_alt": tuple(int(value) for value in scene_style.step_fill_rgb),
                "wall": tuple(int(value) for value in scene_style.grid_rgb),
                "wall_dark": tuple(int(value) for value in scene_style.panel_border_rgb),
                "grid": tuple(int(value) for value in scene_style.notebook_line_rgb),
                "border": tuple(int(value) for value in scene_style.panel_border_rgb),
                "box": tuple(int(value) for value in scene_style.panel_accent_rgb),
                "box_light": tuple(int(value) for value in scene_style.agent_rgb),
                "target": tuple(int(value) for value in scene_style.mark_rgb),
                "player": tuple(int(value) for value in scene_style.text_rgb),
                "option": tuple(int(value) for value in scene_style.panel_fill_rgb),
                "accent": tuple(int(value) for value in scene_style.mark_rgb),
            },
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_sokoban_scene(
            background,
            dataset=dataset,
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description_path_sequence_label",
                "object_description_box_target_relation_label",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_option_letter",
                "annotation_hint_option_panel",
                "annotation_hint_relation_option_marker",
                "json_example_option_label",
                "json_example_relation_option_label",
                "json_example_answer_only_option_label",
            ),
            context=f"prompt defaults for {INTERNAL_TASK_ID}",
        )
        family = _query_family(str(query_id))
        relation_family = family == "box_target_relation_label"
        board_cell_option_family = relation_family
        prompt_slots = {
            "object_description": str(prompt_defaults[f"object_description_{family}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(
                prompt_defaults["annotation_hint_relation_option_marker"]
                if relation_family
                else prompt_defaults["annotation_hint_option_panel"]
            ),
            "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
            "json_example": str(
                prompt_defaults["json_example_relation_option_label"]
                if relation_family
                else prompt_defaults["json_example_option_label"]
            ),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_option_label"]),
            **_query_slot_values(dataset),
        }
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = str(dataset["answer_option_label"])
        correct_option_panel_id = f"option_{answer_value}"
        supporting_option_cell_ids: list[str] = []
        if board_cell_option_family:
            correct_option = next(
                option
                for option in dataset.get("option_specs", [])
                if str(option.get("option_label")) == str(answer_value)
            )
            supporting_option_cell_ids = [_cell_id(cell) for cell in correct_option.get("candidate_cells", [])]
            annotation_bboxes = [
                [round(float(value), 3) for value in rendered_scene.cell_bbox_map[str(cell_id)]]
                for cell_id in supporting_option_cell_ids
            ]
        else:
            annotation_bboxes = [
                [round(float(value), 3) for value in rendered_scene.option_panel_bbox_map[str(correct_option_panel_id)]]
            ]
        annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
        annotation_bboxes = list(annotation_artifacts.value)
        answer_gt = TypedValue(type="option_letter", value=answer_value)
        annotation_gt = annotation_artifacts.annotation_gt

        board_cells = int(dataset["rows"]) * int(dataset["cols"])
        option_count = int(dataset["option_count"])
        move_count = len(dataset.get("move_sequence", []))
        visual_scan = clamp_unit_interval(
            0.42 * normalize_int_with_bounds(int(board_cells), [36, 100])
            + 0.34 * normalize_int_with_bounds(int(option_count), [4, 8])
            + 0.24 * float(_SCENE_LOAD[str(scene_variant)])
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_QUERY[str(query_id)])
            + 0.06 * normalize_int_with_bounds(int(move_count), [0, 10])
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "game_sokoban_grid",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_id": SOKOBAN_SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "view_family": SOKOBAN_SCENE_ID,
                },
            },
            "query_spec": {
                "scene_id": SOKOBAN_SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": SOKOBAN_SCENE_ID,
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "option_count": int(option_count),
                    "option_count_support": [int(value) for value in option_count_support],
                    "option_count_probabilities": dict(option_count_probabilities),
                    "move_count": int(move_count),
                    "answer_option_label": str(answer_value),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": SOKOBAN_SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "board_bbox_px": list(rendered_scene.board_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": attach_games_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "board_bbox_px": list(rendered_scene.board_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
                "annotation_source": "cell_bboxes_px" if board_cell_option_family else "option_panel_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                "scene_id": SOKOBAN_SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "rows": int(dataset["rows"]),
                "cols": int(dataset["cols"]),
                "walls": _json_safe(dataset.get("walls", [])),
                "player_start": _json_safe(dataset.get("player_start")),
                "boxes_start": _json_safe(dataset.get("boxes_start", {})),
                "targets": _json_safe(dataset.get("targets", {})),
                "move_sequence": [str(item) for item in dataset.get("move_sequence", [])],
                "move_sequence_text": str(dataset.get("move_sequence_text", "")),
                "path_start": _json_safe(dataset.get("path_start")),
                "path_goal": _json_safe(dataset.get("path_goal")),
                "shortest_path_cells": _json_safe(dataset.get("shortest_path_cells", [])),
                "query_entity_type": str(dataset.get("query_entity_type", "")),
                "query_entity_label": str(dataset.get("query_entity_label", "")),
                "answer_cell": _json_safe(dataset.get("answer_cell")),
                "relation_support": _json_safe(dataset.get("relation_support", {})),
                "option_specs": _json_safe(dataset.get("option_specs", [])),
                "option_count": int(option_count),
                "answer_option_label": str(answer_value),
                "supporting_option_panel_ids": [] if board_cell_option_family else [str(correct_option_panel_id)],
                "supporting_option_cell_ids": [str(cell_id) for cell_id in supporting_option_cell_ids],
                "question_format": str(query_id),
                "view_family": SOKOBAN_SCENE_ID,
                "solver_trace": _json_safe(dataset.get("solver_trace", {})),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_artifacts.projected_annotation),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SOKOBAN_SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class GamesSokobanPathValiditySequenceLabelTask(_SokobanGridBaseTask):
    """Choose the option matching a Sokoban path-validity property."""

    task_id = PATH_VALIDITY_SEQUENCE_TASK_ID
    supported_query_ids = PATH_VALIDITY_SEQUENCE_QUERY_IDS


@register_task
class GamesSokobanShortestPathSequenceLabelTask(_SokobanGridBaseTask):
    """Choose the option matching a shortest path sequence."""

    task_id = SHORTEST_PATH_SEQUENCE_TASK_ID
    supported_query_ids = SHORTEST_PATH_SEQUENCE_QUERY_IDS


class GamesSokobanNearestCounterpartLabelTask(_SokobanGridBaseTask):
    """Choose the nearest counterpart for a marked box or target."""

    task_id = NEAREST_COUNTERPART_TASK_ID
    supported_query_ids = NEAREST_COUNTERPART_QUERY_IDS


class GamesSokobanBoxTargetManhattanRankLabelTask(_SokobanGridBaseTask):
    """Choose the box-target relation by Manhattan-distance rank."""

    task_id = BOX_TARGET_MANHATTAN_RANK_TASK_ID
    supported_query_ids = BOX_TARGET_MANHATTAN_RANK_QUERY_IDS


__all__ = [
    "GamesSokobanBoxTargetManhattanRankLabelTask",
    "GamesSokobanNearestCounterpartLabelTask",
    "GamesSokobanPathValiditySequenceLabelTask",
    "GamesSokobanShortestPathSequenceLabelTask",
]
