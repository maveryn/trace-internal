"""Rubik-style cube-net spatial puzzle tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.common import projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.rubiks_scene import (
    FACE_COLOR_COUNT_QUERY_IDS,
    MOVE_RESULT_QUERY_IDS,
    STICKER_COLOR_QUERY_IDS,
    SUPPORTED_RUBIKS_QUERY_IDS,
    SUPPORTED_RUBIKS_SCENE_VARIANTS,
    build_rubiks_dataset,
    render_rubiks_scene,
    resolve_rubiks_render_params,
    state_signature,
)
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


INTERNAL_TASK_ID = "puzzles_spatial_rubiks_cube_internal"
RUBIKS_STICKER_COLOR_LABEL_TASK_ID = "task_puzzles__rubiks_net__rubiks_sticker_color_label"
RUBIKS_FACE_COLOR_COUNT_LABEL_TASK_ID = "task_puzzles__rubiks_net__rubiks_face_color_count_label"
RUBIKS_MOVE_RESULT_LABEL_TASK_ID = "task_puzzles__rubiks_net__rubiks_move_result_label"
RUBIKS_SCENE_ID = "rubiks_net"

_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_RUBIKS_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_RUBIKS_SCENE_VARIANTS
_ANSWER_TYPES = {
    "sticker_color_label": "option_letter",
    "face_color_count_label": "option_letter",
    "move_result_label": "option_letter",
}
_REASONING_LOAD_BY_QUERY = {
    "static_sticker_color_label": 0.28,
    "one_move_sticker_color_label": 0.48,
    "short_sequence_sticker_color_label": 0.64,
    "static_face_color_count_label": 0.34,
    "one_move_face_color_count_label": 0.54,
    "short_sequence_face_color_count_label": 0.68,
    "one_move_result_label": 0.52,
    "two_move_result_label": 0.68,
    "inverse_sequence_result_label": 0.72,
}
_SCENE_LOAD = {
    "classic_net": 0.20,
    "paper_net": 0.22,
    "cool_net": 0.24,
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=INTERNAL_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=INTERNAL_TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the non-semantic Rubik panel style/layout variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
        task_id=INTERNAL_TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported_queries: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one internal Rubik query branch for a public task."""

    effective_params = dict(params)
    if effective_params.get("query_variant") is None and effective_params.get("query_variant") is not None:
        effective_params["query_variant"] = str(effective_params["query_variant"])
    return resolve_puzzle_axis_variant(
        params=effective_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=[str(query) for query in supported_queries],
        task_id=INTERNAL_TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _state_for_trace(state: Mapping[Any, str]) -> Dict[str, str]:
    """Serialize a tuple-key sticker-color state for trace metadata."""

    serialized: Dict[str, str] = {}
    for key, color_name in state.items():
        face, row, col = key
        serialized[f"{face}_r{int(row)}_c{int(col)}"] = str(color_name)
    return serialized


def _option_specs_for_trace(option_specs) -> list[dict[str, Any]]:
    """Serialize option specs without tuple-key state maps."""

    serialized = []
    for option in option_specs:
        item = {str(key): value for key, value in dict(option).items() if str(key) != "state"}
        if "state" in option:
            item["state"] = _state_for_trace(option["state"])
            item["state_signature"] = [
                [str(face), int(row), int(col), str(color_name)]
                for face, row, col, color_name in state_signature(option["state"])
            ]
        serialized.append(item)
    return serialized


def _solver_trace_for_trace(solver_trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Serialize solver trace values into canonical JSON-compatible structures."""

    serialized: Dict[str, Any] = {}
    for key, value in solver_trace.items():
        if str(key).endswith("state_signature"):
            serialized[str(key)] = [
                [str(face), int(row), int(col), str(color_name)]
                for face, row, col, color_name in value
            ]
        else:
            serialized[str(key)] = value
    return serialized


def _query_family(query_id: str) -> str:
    if str(query_id) in STICKER_COLOR_QUERY_IDS:
        return "sticker_color_label"
    if str(query_id) in FACE_COLOR_COUNT_QUERY_IDS:
        return "face_color_count_label"
    if str(query_id) in MOVE_RESULT_QUERY_IDS:
        return "move_result_label"
    raise ValueError(f"unsupported Rubik query id: {query_id}")


def _query_slot_values(dataset: Mapping[str, Any]) -> Dict[str, str]:
    sequence_text = str(dataset.get("move_sequence_text", "")).strip()
    base_sequence_text = str(dataset.get("base_sequence_text", "")).strip()
    return {
        "target_position_description": (
            f"position ({int(dataset.get('target_col', 0))}, {int(dataset.get('target_row', 0))}) "
            f"on the {dataset.get('target_face_name', '')} face"
        ),
        "target_face_name": str(dataset.get("target_face_name", "")),
        "move_sequence_text": sequence_text,
        "base_sequence_text": base_sequence_text,
    }


class _RubiksCubeBaseTask:
    """Base generator for public Rubik cube-net tasks."""

    domain = "puzzles"
    task_group = "spatial"
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
            raise ValueError(f"unsupported rubiks query_id: {query_id}")

        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_rubiks_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=INTERNAL_TASK_ID,
        )
        render_params = resolve_rubiks_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.rubiks_cube_net_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            net_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            target_swatch_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            sticker_outline_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            coordinate_fill_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
            coordinate_grid_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_rubiks_scene(
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
                "object_description_sticker_color_label",
                "object_description_face_color_count_label",
                "object_description_move_result_label",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_option_letter",
                "evidence_hint_option_panel",
                "json_example_option_label",
                "json_example_answer_only_option_label",
            ),
            context=f"prompt defaults for {INTERNAL_TASK_ID}",
        )
        family = _query_family(str(query_id))
        prompt_slots = {
            "object_description": str(prompt_defaults[f"object_description_{family}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_defaults["evidence_hint_option_panel"]),
            "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
            "json_example": str(prompt_defaults["json_example_option_label"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_option_label"]),
            **_query_slot_values(dataset),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_panel_id = f"option_{dataset['answer_option_label']}"
        option_projection = projected_puzzle_bbox_evidence(
            rendered_scene.option_panel_bbox_map,
            [str(correct_option_panel_id)],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in option_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        move_count = len(dataset.get("query_sequence", []))
        option_count = int(dataset["option_count"])
        visual_scan = clamp_unit_interval(
            0.38 * normalize_int_with_bounds(int(option_count), [4, 8])
            + 0.32 * normalize_int_with_bounds(54, [36, 72])
            + 0.30 * float(_SCENE_LOAD[str(scene_variant)])
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_QUERY[str(query_id)])
            + 0.08 * normalize_int_with_bounds(int(move_count), [0, 3])
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzle_spatial_rubiks_cube_net",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": "default",
                    "scene_id": RUBIKS_SCENE_ID,
                    "query_id": str(query_id),
                    "query_variant": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "view_family": RUBIKS_SCENE_ID,
                },
            },
            "query_spec": {
                "query_variant": "default",
                "scene_id": RUBIKS_SCENE_ID,
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": "default",
                    "scene_id": RUBIKS_SCENE_ID,
                    "query_id": str(query_id),
                    "query_variant": str(query_id),
                    "query_variant_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "option_count": int(option_count),
                    "move_count": int(move_count),
                    "answer_option_label": str(answer_value),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": RUBIKS_SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "net_panel_bbox_px": list(rendered_scene.net_panel_bbox_px),
                "net_bbox_px": list(rendered_scene.net_bbox_px),
                "target_swatch_bbox_px": (
                    list(rendered_scene.target_swatch_bbox_px)
                    if rendered_scene.target_swatch_bbox_px is not None
                    else None
                ),
                "unit_size_jitter": dict(render_params.unit_size_jitter or {}),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "net_panel_bbox_px": list(rendered_scene.net_panel_bbox_px),
                "net_bbox_px": list(rendered_scene.net_bbox_px),
                "sticker_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.sticker_bbox_map.items()
                },
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
                "candidate_net_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.candidate_net_bbox_map.items()
                },
                "evidence_source": "option_panel_bboxes_px",
            }, render_params.unit_size_jitter or {}),
            "execution_trace": {
                "query_variant": "default",
                "scene_id": RUBIKS_SCENE_ID,
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "scene_variant": str(scene_variant),
                "query_variant_probabilities": dict(query_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "face_color_names": dict(dataset["face_color_names"]),
                "color_map": dict(dataset["color_map"]),
                "scramble_sequence": [str(item) for item in dataset.get("scramble_sequence", [])],
                "query_sequence": [str(item) for item in dataset.get("query_sequence", [])],
                "base_sequence": [str(item) for item in dataset.get("base_sequence", [])],
                "move_sequence_text": str(dataset.get("move_sequence_text", "")),
                "base_sequence_text": str(dataset.get("base_sequence_text", "")),
                "start_state": _state_for_trace(dataset["start_state"]),
                "final_state": _state_for_trace(dataset["final_state"]),
                "target_face": str(dataset.get("target_face", "")),
                "target_face_name": str(dataset.get("target_face_name", "")),
                "target_row": int(dataset.get("target_row", -1)),
                "target_col": int(dataset.get("target_col", -1)),
                "target_sticker_id": str(dataset.get("target_sticker_id", "")),
                "answer_color_name": str(dataset.get("answer_color_name", "")),
                "answer_color_rgb": list(dataset.get("answer_color_rgb", [])),
                "target_color_name": str(dataset.get("target_color_name", "")),
                "target_color_rgb": list(dataset.get("target_color_rgb", [])),
                "counted_sticker_ids": [str(item) for item in dataset.get("counted_sticker_ids", [])],
                "answer_count": int(dataset.get("answer_count", -1)),
                "option_specs": _option_specs_for_trace(dataset["option_specs"]),
                "option_count": int(option_count),
                "answer_option_label": str(answer_value),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
                "question_format": str(query_id),
                "view_family": RUBIKS_SCENE_ID,
                "solver_trace": _solver_trace_for_trace(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=RUBIKS_SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesSpatialRubiksStickerColorLabelTask(_RubiksCubeBaseTask):
    """Choose the color-swatch option for a queried Rubik sticker."""

    task_id = RUBIKS_STICKER_COLOR_LABEL_TASK_ID
    supported_query_ids = STICKER_COLOR_QUERY_IDS


@register_task
class PuzzlesSpatialRubiksFaceColorCountLabelTask(_RubiksCubeBaseTask):
    """Choose the numeric option for a target-color count on one Rubik face."""

    task_id = RUBIKS_FACE_COLOR_COUNT_LABEL_TASK_ID
    supported_query_ids = FACE_COLOR_COUNT_QUERY_IDS


@register_task
class PuzzlesSpatialRubiksMoveResultLabelTask(_RubiksCubeBaseTask):
    """Choose the candidate net resulting from a Rubik move sequence."""

    task_id = RUBIKS_MOVE_RESULT_LABEL_TASK_ID
    supported_query_ids = MOVE_RESULT_QUERY_IDS


__all__ = [
    "PuzzlesSpatialRubiksFaceColorCountLabelTask",
    "PuzzlesSpatialRubiksMoveResultLabelTask",
    "PuzzlesSpatialRubiksStickerColorLabelTask",
]
