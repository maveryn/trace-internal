"""Puzzle logic task that completes a missing grid cell using image options."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
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
from ..shared.common import decouple_axis_sampling, projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.fixed_query_task import FixedPuzzleQueryVariantTaskMixin, forced_puzzle_query_params, rewrite_fixed_puzzle_query_output
from ..shared.logic_common import (
    PuzzleLogicDefaults,
    SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS,
    build_logic_adjacency_dataset_for_variant,
    build_logic_grid_dataset_for_variant,
    resolve_logic_board_size_bounds,
    resolve_logic_render_params,
    resolve_logic_scene_variant,
)
from ..shared.logic_scene import render_puzzle_logic_scene
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "puzzles_logic_grid_completion_internal"
GRID_UNIQUENESS_COMPLETION_LABEL_TASK_ID = "task_puzzles__logic_grid__grid_uniqueness_completion_label"
GRID_KING_NON_TOUCH_LABEL_TASK_ID = "task_puzzles__logic_grid__grid_king_non_touch_label"
SCENE_ID = "logic_grid"
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "axis_uniqueness",
    "row_and_column_uniqueness",
    "king_non_touch",
)
_SOURCE_AXIS_BY_QUERY_VARIANT = {
    "row_uniqueness": "row",
    "column_uniqueness": "column",
}
_INTERNAL_QUERY_VARIANT_BY_AXIS = {
    "row": "row_uniqueness",
    "column": "column_uniqueness",
}
_SUPPORTED_UNIQUENESS_AXES: Tuple[str, ...] = ("row", "column")
_SUPPORTED_UNIQUENESS_QUERY_VARIANTS: Tuple[str, ...] = ("axis_uniqueness", "row_and_column_uniqueness")
_SAMPLING_VARIANT_AXIS_SIZE = 4
_REASONING_LOAD_BASE_BY_VARIANT = {
    "row_uniqueness": 0.00,
    "row_and_column_uniqueness": 0.50,
    "column_uniqueness": 1.00,
    "king_non_touch": 0.46,
}
_SCENE_LOAD_BY_VARIANT = {
    "logic_strip": 0.16,
    "logic_card": 0.24,
    "logic_outline": 0.2,
}

_DEFAULTS = PuzzleLogicDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.0)


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic logic-grid variant."""

    explicit = params.get("query_variant")
    if explicit is not None and str(explicit) in _SOURCE_AXIS_BY_QUERY_VARIANT:
        return "axis_uniqueness", {
            key: (1.0 if key == "axis_uniqueness" else 0.0)
            for key in _SUPPORTED_QUERY_VARIANTS
        }
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _resolve_uniqueness_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str | None, Dict[str, float]]:
    """Resolve row vs column for the axis-uniqueness public variant."""

    explicit_query_variant = params.get("query_variant")
    if explicit_query_variant is not None and str(explicit_query_variant) in _SOURCE_AXIS_BY_QUERY_VARIANT:
        selected = str(_SOURCE_AXIS_BY_QUERY_VARIANT[str(explicit_query_variant)])
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_UNIQUENESS_AXES}

    explicit_axis = params.get("uniqueness_axis", params.get("axis"))
    if explicit_axis is not None:
        selected = str(explicit_axis).strip().lower()
        if selected not in _SUPPORTED_UNIQUENESS_AXES:
            raise ValueError(f"unsupported uniqueness_axis: {explicit_axis}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_UNIQUENESS_AXES}

    axis, probabilities = resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_UNIQUENESS_AXES,
        task_id=TASK_ID,
        explicit_key="uniqueness_axis",
        weights_key="uniqueness_axis_weights",
        balance_flag_key="balanced_uniqueness_axis_sampling",
        axis_namespace="uniqueness_axis",
    )
    return str(axis), dict(probabilities)


def _dataset_params_for_variant(params: Mapping[str, Any], *, internal_query_variant: str) -> Dict[str, Any]:
    """Return generation params adjusted for variant-local support ranges."""

    updated = dict(params)
    if str(internal_query_variant) != "king_non_touch":
        return updated
    lower = int(_GEN_DEFAULTS.get("king_non_touch_board_size_min", updated.get("board_size_min", _DEFAULTS.board_size_min)))
    upper = int(_GEN_DEFAULTS.get("king_non_touch_board_size_max", updated.get("board_size_max", _DEFAULTS.board_size_max)))
    if "board_size" in updated and not lower <= int(updated["board_size"]) <= upper:
        updated.pop("board_size", None)
    updated["board_size_min"] = int(lower)
    updated["board_size_max"] = int(upper)
    return updated


def _select_uniqueness_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Choose the internal uniqueness-grid query while keeping it inside one public task."""

    explicit = params.get("uniqueness_query")
    if explicit is None:
        query_variant = params.get("query_variant")
        if query_variant is not None and str(query_variant) != "grid_uniqueness_completion":
            explicit = query_variant
    if explicit is not None:
        selected = str(explicit)
        updated = dict(params)
        updated.pop("query_variant", None)
        if selected in _SOURCE_AXIS_BY_QUERY_VARIANT:
            axis = str(_SOURCE_AXIS_BY_QUERY_VARIANT[selected])
            updated["uniqueness_axis"] = axis
            selected = "axis_uniqueness"
        if selected not in _SUPPORTED_UNIQUENESS_QUERY_VARIANTS:
            raise ValueError(f"unsupported uniqueness query variant: {explicit}")
        return selected, {key: float(key == selected) for key in _SUPPORTED_UNIQUENESS_QUERY_VARIANTS}, updated

    updated = dict(params)
    updated.pop("query_variant", None)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.uniqueness_query_variant")
    selected = _SUPPORTED_UNIQUENESS_QUERY_VARIANTS[int(rng.randrange(len(_SUPPORTED_UNIQUENESS_QUERY_VARIANTS)))]
    return selected, {key: 0.5 for key in _SUPPORTED_UNIQUENESS_QUERY_VARIANTS}, updated


class _PuzzlesLogicGridCompletionBaseTask:
    """Choose the image option that correctly completes one logic-grid puzzle."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "logic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        uniqueness_axis: str | None = None
        uniqueness_axis_probabilities: Dict[str, float] = {}
        if str(query_variant) == "axis_uniqueness":
            uniqueness_axis, uniqueness_axis_probabilities = _resolve_uniqueness_axis(
                params,
                instance_seed=int(instance_seed),
            )
            internal_query_variant = str(_INTERNAL_QUERY_VARIANT_BY_AXIS[str(uniqueness_axis)])
        else:
            internal_query_variant = str(query_variant)
        dataset_params = _dataset_params_for_variant(params, internal_query_variant=str(internal_query_variant))
        board_size_range = resolve_logic_board_size_bounds(
            dataset_params,
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        board_size_axis_size = (
            1
            if params.get("board_size") is not None
            else int(board_size_range[1] - board_size_range[0] + 1)
        )
        scene_params = decouple_axis_sampling(
            params,
            preceding_axis_size=(1 if "query_variant" in params else _SAMPLING_VARIANT_AXIS_SIZE) * int(board_size_axis_size),
            explicit_key="scene_variant",
        )
        scene_variant, scene_variant_probabilities = resolve_logic_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        if str(internal_query_variant) == "king_non_touch":
            dataset = build_logic_adjacency_dataset_for_variant(
                query_variant=str(internal_query_variant),
                params=dataset_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        else:
            dataset = build_logic_grid_dataset_for_variant(
                query_variant=str(internal_query_variant),
                params=dataset_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )

        render_params = resolve_logic_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.logic_grid_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            cell_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            unknown_cell_fill_rgb=tuple(int(value) for value in scene_style.panel_accent_rgb),
            option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            option_symbol_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            accent_color_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_puzzle_logic_scene(
            background,
            scene_variant=str(scene_variant),
            grid_rows=list(dataset["grid_rows"]),
            option_specs=list(dataset["option_specs"]),
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
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_logic_strip",
                "object_description_logic_card",
                "object_description_logic_outline",
                "evidence_hint_axis_uniqueness",
                "evidence_hint_row_and_column_uniqueness",
                "evidence_hint_king_non_touch",
                "json_example_axis_uniqueness",
                "json_example_row_and_column_uniqueness",
                "json_example_king_non_touch",
                "json_example_answer_only_axis_uniqueness",
                "json_example_answer_only_row_and_column_uniqueness",
                "json_example_answer_only_king_non_touch",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "uniqueness_axis": str(uniqueness_axis or ""),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_panel_id = str(dataset["correct_option_panel_id"])
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.option_panel_bbox_map,
            [str(correct_option_panel_id)],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_logic_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "internal_query_variant": str(internal_query_variant),
                    "uniqueness_axis": uniqueness_axis,
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "query_cell_id": str(dataset["query_cell_id"]),
                    "correct_option_panel_id": str(correct_option_panel_id),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "internal_query_variant": str(internal_query_variant),
                    "uniqueness_axis": uniqueness_axis,
                    "scene_variant": str(scene_variant),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "uniqueness_axis_probabilities": dict(uniqueness_axis_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "board_size": int(dataset["board_size"]),
                    "board_size_range": list(dataset["board_size_range"]),
                    "cell_count": int(dataset["cell_count"]),
                    "cell_count_range": list(dataset["cell_count_range"]),
                    "option_count": int(dataset["option_count"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "value_font_size_px": int(render_params.value_font_size_px),
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            }, render_params.unit_size_jitter),
            "execution_trace": {
                "query_variant": str(query_variant),
                "internal_query_variant": str(internal_query_variant),
                "uniqueness_axis": uniqueness_axis,
                "scene_variant": str(scene_variant),
                "query_cell_id": str(dataset["query_cell_id"]),
                "query_row_index": int(dataset["query_row_index"]),
                "query_col_index": int(dataset["query_col_index"]),
                "board_size": int(dataset["board_size"]),
                "board_size_range": list(dataset["board_size_range"]),
                "cell_count": int(dataset["cell_count"]),
                "cell_count_range": list(dataset["cell_count_range"]),
                "board_values": [[str(value) for value in row] for row in dataset["board_values"]],
                "grid_rows": [[dict(cell) for cell in row] for row in dataset["grid_rows"]],
                "symbol_pool": [str(value) for value in dataset["symbol_pool"]],
                "answer_object_type": str(dataset["answer_object_type"]),
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(correct_option_panel_id),
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "uniqueness_axis_probabilities": dict(uniqueness_axis_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
                "question_format": "logic_grid_mcq",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        if str(internal_query_variant) == "king_non_touch":
            trace_payload["query_spec"]["params"]["query_neighbor_count"] = int(len(dataset["neighbor_coords"]))
            trace_payload["execution_trace"].update(
                {
                    "neighbor_coords": [list(coords) for coords in dataset["neighbor_coords"]],
                    "forced_neighbor_coords": [list(coords) for coords in dataset["forced_neighbor_coords"]],
                    "forced_neighbor_types": [str(value) for value in dataset["forced_neighbor_types"]],
                    "query_neighbor_object_types": [
                        str(value) for value in dataset["query_neighbor_object_types"]
                    ],
                    "valid_option_object_types": [
                        str(value) for value in dataset["valid_option_object_types"]
                    ],
                }
            )

        board_size_norm = normalize_int_with_bounds(
            int(dataset["board_size"]),
            list(dataset["board_size_range"]),
        )
        reasoning_load = min(
            1.0,
            (0.75 * float(_REASONING_LOAD_BASE_BY_VARIANT[str(internal_query_variant)]))
            + (0.25 * float(board_size_norm)),
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(dataset["cell_count"]), list(dataset["cell_count_range"])),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesLogicGridUniquenessCompletionLabelTask(_PuzzlesLogicGridCompletionBaseTask):
    """Complete a row/column uniqueness logic grid."""

    task_id = GRID_UNIQUENESS_COMPLETION_LABEL_TASK_ID
    default_dataset_enabled = True
    fixed_query_variant = "grid_uniqueness_completion"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected, probabilities, selected_params = _select_uniqueness_query_variant(
            params,
            instance_seed=int(instance_seed),
        )
        normalized_params = dict(selected_params)
        normalized_params.pop("query_variant", None)
        forced_params = forced_puzzle_query_params(normalized_params, query_variant=str(selected))
        output = super().generate(int(instance_seed), params=forced_params, max_attempts=int(max_attempts))
        rewritten = rewrite_fixed_puzzle_query_output(
            output,
            query_id="grid_uniqueness_completion",
            scene_id=SCENE_ID,
        )
        trace_payload = dict(rewritten.trace_payload)
        query_spec = trace_payload.get("query_spec")
        if isinstance(query_spec, dict):
            params_map = query_spec.get("params")
            if isinstance(params_map, dict):
                params_map["uniqueness_query"] = str(selected)
                params_map["uniqueness_query_probabilities"] = dict(probabilities)
        execution_trace = trace_payload.get("execution_trace")
        if isinstance(execution_trace, dict):
            execution_trace["uniqueness_query"] = str(selected)
            execution_trace["uniqueness_query_probabilities"] = dict(probabilities)
        return rewritten.__class__(
            prompt=rewritten.prompt,
            answer_gt=rewritten.answer_gt,
            evidence_gt=rewritten.evidence_gt,
            image=rewritten.image,
            image_id=rewritten.image_id,
            trace_payload=trace_payload,
            complexity=rewritten.complexity,
            task_versions=rewritten.task_versions,
            query_variant=rewritten.query_variant,
            prompt_variants=rewritten.prompt_variants,
            scene_id=rewritten.scene_id,
            query_id=rewritten.query_id,
        )


@register_task
class PuzzlesLogicGridKingNonTouchLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesLogicGridCompletionBaseTask):
    """Complete a logic grid under the king non-touch rule."""

    task_id = GRID_KING_NON_TOUCH_LABEL_TASK_ID
    fixed_query_variant = "king_non_touch"
    public_scene_id = SCENE_ID


__all__ = [
    "PuzzlesLogicGridKingNonTouchLabelTask",
    "PuzzlesLogicGridUniquenessCompletionLabelTask",
]
