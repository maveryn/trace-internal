"""Puzzle spatial task that asks for the result of a spatial transformation."""

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
from ..shared.common import decouple_axis_sampling, projected_puzzle_bbox_annotation, resolve_puzzle_axis_variant
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.fixed_query_task import FixedPuzzleQueryVariantTaskMixin
from ..shared.paper_fold_common import (
    PuzzleFoldResultDefaults,
    SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS,
    SUPPORTED_PUZZLE_FOLD_RESULT_VARIANTS,
    build_fold_result_dataset_for_variant,
    resolve_fold_result_render_params,
    resolve_fold_result_scene_variant,
)
from ..shared.paper_fold_cut_common import (
    PuzzleFoldCutDefaults,
    SUPPORTED_PUZZLE_FOLD_CUT_QUERY_IDS,
    build_fold_cut_result_dataset_for_variant,
)
from ..shared.paper_fold_scene import (
    FOLD_RESULT_SUPERSAMPLE_SCALE,
    render_puzzle_fold_cut_result_scene,
    render_puzzle_fold_result_scene,
)
from ..shared.overlay_common import (
    PuzzleOverlayDefaults,
    SUPPORTED_PUZZLE_OVERLAY_SCENE_VARIANTS,
    build_overlay_dataset_for_variant,
    resolve_overlay_render_params,
    resolve_overlay_scene_variant,
)
from ..shared.overlay_scene import render_puzzle_overlay_scene
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


TASK_ID = "puzzles_spatial_transform_result_internal"
PAPER_FOLD_RESULT_LABEL_TASK_ID = "task_puzzles__paper_fold__paper_fold_result_label"
PAPER_FOLD_CUT_RESULT_LABEL_TASK_ID = "task_puzzles__paper_fold_cut__paper_fold_cut_result_label"
OVERLAY_RESULT_LABEL_TASK_ID = "task_puzzles__overlay__overlay_result_label"
PAPER_FOLD_SCENE_ID = "paper_fold"
PAPER_FOLD_CUT_SCENE_ID = "paper_fold_cut"
OVERLAY_SCENE_ID = "overlay"
_FOLD_RESULT_QUERY_IDS: Tuple[str, ...] = SUPPORTED_PUZZLE_FOLD_RESULT_VARIANTS
_FOLD_CUT_QUERY_IDS: Tuple[str, ...] = SUPPORTED_PUZZLE_FOLD_CUT_QUERY_IDS
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "paper_fold_result",
    "paper_fold_cut_result",
    "overlay_result",
)
_SUPPORTED_FOLD_COUNTS: Tuple[str, ...] = ("1", "2")
_SUPPORTED_FOLD_AXES: Tuple[str, ...] = ("vertical", "horizontal")
_SOURCE_QUERY_ID_TO_PUBLIC = {
    "fold_result": "paper_fold_result",
    "vertical_fold_result": "paper_fold_result",
    "horizontal_fold_result": "paper_fold_result",
    "single_fold_cut_result": "paper_fold_cut_result",
    "single_vertical_fold_cut_result": "paper_fold_cut_result",
    "single_horizontal_fold_cut_result": "paper_fold_cut_result",
    "double_fold_cut_result": "paper_fold_cut_result",
    "overlay_union_same_grid": "overlay_result",
}
_INTERNAL_FOLD_RESULT_VARIANT_BY_AXIS = {
    "vertical": "vertical_fold_result",
    "horizontal": "horizontal_fold_result",
}
_INTERNAL_SINGLE_FOLD_CUT_VARIANT_BY_AXIS = {
    "vertical": "single_vertical_fold_cut_result",
    "horizontal": "single_horizontal_fold_cut_result",
}
_REASONING_LOAD_BASE_BY_VARIANT = {
    "paper_fold_result": 0.38,
    "paper_fold_cut_result": 0.44,
    "overlay_result": 0.37,
}
_SCENE_LOAD_BY_VARIANT = {
    "fold_strip": 0.16,
    "fold_card": 0.22,
    "fold_outline": 0.2,
    "overlay_strip": 0.14,
    "overlay_card": 0.20,
    "overlay_outline": 0.18,
}
_SUPPORTED_FOLD_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS
_SUPPORTED_OVERLAY_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_PUZZLE_OVERLAY_SCENE_VARIANTS

_FOLD_RESULT_DEFAULTS = PuzzleFoldResultDefaults()
_FOLD_CUT_DEFAULTS = PuzzleFoldCutDefaults()
_OVERLAY_DEFAULTS = PuzzleOverlayDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


def _resolve_transform_scene_style(instance_seed: int, *, task_id: str, scene_id: str):
    return resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{scene_id}.background",
    )


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the requested spatial result variant."""

    explicit_variant = params.get("query_id")
    if explicit_variant is not None and str(explicit_variant) in _SOURCE_QUERY_ID_TO_PUBLIC:
        selected = str(_SOURCE_QUERY_ID_TO_PUBLIC[str(explicit_variant)])
        return selected, {str(variant): float(variant == selected) for variant in _SUPPORTED_QUERY_IDS}

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_fold_axis(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    preceding_axis_size: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the orientation axis for public variants that admit mirrored folds."""

    explicit_variant = params.get("query_id")
    if explicit_variant is not None:
        if str(explicit_variant) in {"vertical_fold_result", "single_vertical_fold_cut_result"}:
            return "vertical", {"vertical": 1.0, "horizontal": 0.0}
        if str(explicit_variant) in {"horizontal_fold_result", "single_horizontal_fold_cut_result"}:
            return "horizontal", {"vertical": 0.0, "horizontal": 1.0}

    axis_params = decouple_axis_sampling(
        params,
        preceding_axis_size=int(preceding_axis_size),
        explicit_key="fold_axis",
    )
    return resolve_puzzle_axis_variant(
        params=axis_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_FOLD_AXES,
        task_id=TASK_ID,
        explicit_key="fold_axis",
        weights_key="fold_axis_weights",
        balance_flag_key="balanced_fold_axis_sampling",
        axis_namespace="fold_axis",
    )


def _resolve_fold_count(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Dict[str, float]]:
    """Resolve one-fold versus two-fold cut puzzles as a parameter axis."""

    explicit_variant = params.get("query_id")
    if explicit_variant is not None:
        if str(explicit_variant) in {"single_fold_cut_result", "single_vertical_fold_cut_result", "single_horizontal_fold_cut_result"}:
            return 1, {"1": 1.0, "2": 0.0}
        if str(explicit_variant) == "double_fold_cut_result":
            return 2, {"1": 0.0, "2": 1.0}

    explicit_fold_count = params.get("fold_count")
    if explicit_fold_count is not None:
        selected = int(explicit_fold_count)
        if selected not in {1, 2}:
            raise ValueError("fold_count must be 1 or 2 for paper_fold_cut_result")
        return int(selected), {str(value): float(value == selected) for value in (1, 2)}

    fold_count_params = decouple_axis_sampling(
        params,
        preceding_axis_size=len(_SUPPORTED_QUERY_IDS),
        explicit_key="fold_count",
    )
    selected, probabilities = resolve_puzzle_axis_variant(
        params=fold_count_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_FOLD_COUNTS,
        task_id=TASK_ID,
        explicit_key="fold_count",
        weights_key="fold_count_weights",
        balance_flag_key="balanced_fold_count_sampling",
        axis_namespace="fold_count",
    )
    return int(selected), {str(key): float(value) for key, value in probabilities.items()}


def _internal_query_id_for_public(
    query_id: str,
    *,
    fold_axis: str | None,
    fold_count: int | None,
) -> str:
    """Map the public variant and orientation axis to the renderer's internal grammar."""

    if str(query_id) == "paper_fold_result":
        if str(fold_axis) not in _INTERNAL_FOLD_RESULT_VARIANT_BY_AXIS:
            raise ValueError("paper_fold_result requires fold_axis=vertical|horizontal")
        return str(_INTERNAL_FOLD_RESULT_VARIANT_BY_AXIS[str(fold_axis)])
    if str(query_id) == "paper_fold_cut_result" and int(fold_count or 0) == 1:
        if str(fold_axis) not in _INTERNAL_SINGLE_FOLD_CUT_VARIANT_BY_AXIS:
            raise ValueError("one-fold paper_fold_cut_result requires fold_axis=vertical|horizontal")
        return str(_INTERNAL_SINGLE_FOLD_CUT_VARIANT_BY_AXIS[str(fold_axis)])
    if str(query_id) == "paper_fold_cut_result" and int(fold_count or 0) == 2:
        return "double_fold_cut_result"
    if str(query_id) == "overlay_result":
        return "overlay_union_same_grid"
    raise ValueError(f"unsupported public fold query id: {query_id}")


def _source_variant_fixes_fold_axis(params: Mapping[str, Any]) -> bool:
    """Return true when a compatibility variant already encodes orientation."""

    explicit_variant = params.get("query_id")
    return explicit_variant is not None and str(explicit_variant) in {
        "vertical_fold_result",
        "horizontal_fold_result",
        "single_vertical_fold_cut_result",
        "single_horizontal_fold_cut_result",
    }


def _source_variant_fixes_fold_count(params: Mapping[str, Any]) -> bool:
    """Return true when a compatibility variant already encodes fold count."""

    explicit_variant = params.get("query_id")
    return explicit_variant is not None and str(explicit_variant) in {
        "single_fold_cut_result",
        "single_vertical_fold_cut_result",
        "single_horizontal_fold_cut_result",
        "double_fold_cut_result",
    }


def _axis_decoupling_factor(
    params: Mapping[str, Any],
    *,
    query_id: str,
    fold_count: int | None = None,
    include_scene_axis: bool,
) -> int:
    """Return the review-sampling axis product consumed before answer balancing."""

    factor = 1
    if params.get("query_id") is None:
        factor *= len(_SUPPORTED_QUERY_IDS)
    if (
        str(query_id) == "paper_fold_cut_result"
        and params.get("fold_count") is None
        and not _source_variant_fixes_fold_count(params)
    ):
        factor *= len(_SUPPORTED_FOLD_COUNTS)
    needs_fold_axis = (
        str(query_id) == "paper_fold_result"
        or (str(query_id) == "paper_fold_cut_result" and int(fold_count or 0) == 1)
    )
    if (
        bool(needs_fold_axis)
        and params.get("fold_axis") is None
        and not _source_variant_fixes_fold_axis(params)
    ):
        factor *= len(_SUPPORTED_FOLD_AXES)
    if include_scene_axis and params.get("scene_variant") is None:
        if str(query_id) == "overlay_result":
            factor *= len(_SUPPORTED_OVERLAY_SCENE_VARIANTS)
        else:
            factor *= len(_SUPPORTED_FOLD_SCENE_VARIANTS)
    return max(1, int(factor))


def _decouple_sampling(
    params: Mapping[str, Any],
    *,
    factor: int,
) -> Mapping[str, Any]:
    """No-op hook for axis-decoupling call sites."""

    _ = int(factor)
    return params


def _builder_params_for_option_balance(
    params: Mapping[str, Any],
    *,
    query_id: str,
    internal_query_id: str,
    fold_count: int | None = None,
) -> Dict[str, Any]:
    """Return builder params with the internal query grammar selected."""

    builder_params = dict(params)
    builder_params["query_id"] = str(internal_query_id)
    return builder_params


class _PuzzlesSpatialTransformResultBaseTask:
    """Choose the labeled option that shows the result of a spatial transformation."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        if str(query_id) == "overlay_result":
            return self._generate_overlay_result(
                int(instance_seed),
                params=params,
                query_id_probabilities=dict(query_id_probabilities),
            )

        fold_axis: str | None = None
        fold_axis_probabilities: Dict[str, float] = {}
        fold_count: int | None = None
        fold_count_probabilities: Dict[str, float] = {}
        if str(query_id) == "paper_fold_cut_result":
            fold_count, fold_count_probabilities = _resolve_fold_count(params, instance_seed=int(instance_seed))
        if str(query_id) == "paper_fold_result" or (
            str(query_id) == "paper_fold_cut_result" and int(fold_count or 0) == 1
        ):
            fold_axis_preceding = len(_SUPPORTED_QUERY_IDS)
            if (
                str(query_id) == "paper_fold_cut_result"
                and params.get("fold_count") is None
                and not _source_variant_fixes_fold_count(params)
            ):
                fold_axis_preceding *= len(_SUPPORTED_FOLD_COUNTS)
            fold_axis, fold_axis_probabilities = _resolve_fold_axis(
                params,
                instance_seed=int(instance_seed),
                preceding_axis_size=int(fold_axis_preceding),
            )
        internal_query_id = _internal_query_id_for_public(
            str(query_id),
            fold_axis=fold_axis,
            fold_count=fold_count,
        )
        scene_params = _decouple_sampling(
            params,
            factor=_axis_decoupling_factor(
                params,
                query_id=str(query_id),
                fold_count=fold_count,
                include_scene_axis=False,
            ),
        )
        scene_variant, scene_variant_probabilities = resolve_fold_result_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )

        builder_params = _builder_params_for_option_balance(
            params,
            query_id=str(query_id),
            internal_query_id=str(internal_query_id),
            fold_count=fold_count,
        )
        render_params = resolve_fold_result_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = _resolve_transform_scene_style(
            int(instance_seed),
            task_id=str(self.task_id),
            scene_id=PAPER_FOLD_CUT_SCENE_ID if str(query_id) == "paper_fold_cut_result" else PAPER_FOLD_SCENE_ID,
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            paper_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            paper_shadow_rgb=tuple(int(value) for value in scene_style.background_accent_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            fold_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            grid_line_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
            arrow_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            instruction_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            cut_hole_fill_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            cut_hole_outline_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )

        is_fold_cut_variant = str(internal_query_id) in _FOLD_CUT_QUERY_IDS
        if is_fold_cut_variant:
            dataset = build_fold_cut_result_dataset_for_variant(
                query_id=str(internal_query_id),
                params=builder_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_FOLD_CUT_DEFAULTS,
                task_id=self.task_id,
            )
            rendered_scene = render_puzzle_fold_cut_result_scene(
                background,
                scene_variant=str(scene_variant),
                grid_size=int(dataset["grid_size"]),
                fold_sequence=list(dataset["fold_sequence"]),
                folded_grid_cols=int(dataset["folded_grid_cols"]),
                folded_grid_rows=int(dataset["folded_grid_rows"]),
                cut_specs=list(dataset["cut_specs"]),
                option_specs=list(dataset["option_specs"]),
                render_params=render_params,
            )
        else:
            dataset = build_fold_result_dataset_for_variant(
                query_id=str(internal_query_id),
                params=builder_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_FOLD_RESULT_DEFAULTS,
                task_id=self.task_id,
            )
            rendered_scene = render_puzzle_fold_result_scene(
                background,
                scene_variant=str(scene_variant),
                fold_axis=str(dataset["fold_axis"]),
                fold_direction=str(dataset["fold_direction"]),
                grid_size=int(dataset["grid_size"]),
                original_mark_specs=list(dataset["original_mark_specs"]),
                option_specs=list(dataset["option_specs"]),
                result_grid_cols=int(dataset["result_grid_cols"]),
                result_grid_rows=int(dataset["result_grid_rows"]),
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
                "object_description_fold_strip",
                "object_description_fold_card",
                "object_description_fold_outline",
                "annotation_hint_paper_fold_result",
                "annotation_hint_paper_fold_cut_result",
                "json_example_paper_fold_result",
                "json_example_paper_fold_cut_result",
                "json_example_answer_only_paper_fold_result",
                "json_example_answer_only_paper_fold_cut_result",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_choice_id = str(dataset["correct_option_choice_id"])
        annotation_projection = projected_puzzle_bbox_annotation(
            rendered_scene.option_choice_bbox_map,
            [str(correct_option_choice_id)],
        )
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        if is_fold_cut_variant:
            visual_scan = normalize_int_with_bounds(int(dataset["unfolded_hole_count"]), [2, 8])
            cut_scan = normalize_int_with_bounds(int(dataset["cut_count"]), [1, 3])
            reasoning_load = float(
                clamp_unit_interval(
                    float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)])
                    + (0.16 * float(cut_scan))
                    + (0.12 if int(dataset["fold_count"]) == 2 else 0.0)
                )
            )
        else:
            mark_scan = normalize_int_with_bounds(int(dataset["mark_count"]), [3, 5])
            folded_source_scan = normalize_int_with_bounds(int(dataset["folded_mark_count"]), [1, 4])
            visual_scan = float(mark_scan)
            reasoning_load = float(
                clamp_unit_interval(
                    float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)])
                    + (0.22 * float(folded_source_scan))
                )
            )
        complexity_components = {
            "visual_scan": float(visual_scan),
            "reasoning_load": float(reasoning_load),
            "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
        }
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components=complexity_components,
        )

        render_map = {
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "reference_panel_bbox_px": list(rendered_scene.reference_panel_bbox_px),
            "reference_paper_bbox_px": list(rendered_scene.reference_paper_bbox_px),
            "option_choice_bboxes_px": {
                str(key): list(value) for key, value in rendered_scene.option_choice_bbox_map.items()
            },
        }
        if is_fold_cut_variant:
            render_map["folded_packet_bbox_px"] = list(rendered_scene.folded_packet_bbox_px)
        render_map = with_puzzle_unit_size_jitter(render_map, render_params.unit_size_jitter)

        execution_trace: Dict[str, Any]
        if is_fold_cut_variant:
            execution_trace = {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
                "scene_variant": str(scene_variant),
                "fold_count_probabilities": dict(fold_count_probabilities),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "grid_size": int(dataset["grid_size"]),
                "folded_grid_cols": int(dataset["folded_grid_cols"]),
                "folded_grid_rows": int(dataset["folded_grid_rows"]),
                "fold_sequence": [dict(step) for step in dataset["fold_sequence"]],
                "fold_count": int(dataset["fold_count"]),
                "folded_dimensions_by_step": [list(item) for item in dataset["folded_dimensions_by_step"]],
                "cut_count": int(dataset["cut_count"]),
                "cut_count_range": list(dataset["cut_count_range"]),
                "cut_cells": [list(item) for item in dataset["cut_cells"]],
                "cut_specs": [dict(item) for item in dataset["cut_specs"]],
                "unfolded_hole_cells": [list(item) for item in dataset["unfolded_hole_cells"]],
                "unfolded_hole_specs": [dict(item) for item in dataset["unfolded_hole_specs"]],
                "unfolded_hole_count": int(dataset["unfolded_hole_count"]),
                "cut_hole_shape": str(render_params.cut_hole_shape),
                "option_count": int(dataset["option_count"]),
                "option_count_range": list(dataset["option_count_range"]),
                "option_specs": [dict(item) for item in dataset["option_specs"]],
                "answer_option_label": str(answer_value),
                "correct_option_choice_id": str(correct_option_choice_id),
                "correct_option_index": int(dataset["correct_option_index"]),
                "supporting_option_choice_ids": [str(correct_option_choice_id)],
                "solver_trace": dict(dataset["solver_trace"]),
            }
            view_family = "paper_fold_cut_result_mcq"
        else:
            execution_trace = {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "fold_axis": str(dataset["fold_axis"]),
                "fold_direction": str(dataset["fold_direction"]),
                "grid_size": int(dataset["grid_size"]),
                "result_grid_cols": int(dataset["result_grid_cols"]),
                "result_grid_rows": int(dataset["result_grid_rows"]),
                "mark_count": int(dataset["mark_count"]),
                "mark_count_range": [
                    int(_GEN_DEFAULTS.get("mark_count_min", _FOLD_RESULT_DEFAULTS.mark_count_min)),
                    int(_GEN_DEFAULTS.get("mark_count_max", _FOLD_RESULT_DEFAULTS.mark_count_max)),
                ],
                "folded_mark_count": int(dataset["folded_mark_count"]),
                "kept_mark_count": int(dataset["kept_mark_count"]),
                "original_mark_specs": [dict(item) for item in dataset["original_mark_specs"]],
                "folded_result_mark_specs": [dict(item) for item in dataset["folded_result_mark_specs"]],
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(item) for item in dataset["option_specs"]],
                "answer_option_label": str(answer_value),
                "correct_option_choice_id": str(correct_option_choice_id),
                "correct_option_index": int(dataset["correct_option_index"]),
                "supporting_option_choice_ids": [str(correct_option_choice_id)],
                "solver_trace": {
                    "correct_option_label": str(answer_value),
                    "correct_option_index": int(dataset["correct_option_index"]),
                    "folded_result_mark_specs": [dict(item) for item in dataset["folded_result_mark_specs"]],
                },
            }
            view_family = "paper_fold_result_mcq"

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_spatial_folding_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "correct_option_choice_id": str(correct_option_choice_id),
                    "view_family": str(view_family),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "fold_axis_probabilities": dict(fold_axis_probabilities),
                    "fold_count_probabilities": dict(fold_count_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "option_count": int(dataset["option_count"]),
                    "grid_size": int(dataset["grid_size"]),
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
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "text_style": {
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                },
                "antialias_supersample_scale": int(FOLD_RESULT_SUPERSAMPLE_SCALE),
            },
            "render_map": render_map,
            "execution_trace": execution_trace,
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
            "projected_annotation": dict(annotation_projection),
            "complexity": complexity.to_dict(),
        }

        if is_fold_cut_variant:
            trace_payload["query_spec"]["params"].update(
                {
                    "fold_count": int(dataset["fold_count"]),
                    "cut_count": int(dataset["cut_count"]),
                    "unfolded_hole_count": int(dataset["unfolded_hole_count"]),
                }
            )
            if fold_axis is not None:
                trace_payload["query_spec"]["params"]["fold_axis"] = str(fold_axis)
                trace_payload["execution_trace"]["fold_axis"] = str(fold_axis)
            trace_payload["render_spec"]["cut_hole_style"] = {
                "shape": str(render_params.cut_hole_shape),
                "fill_rgb": list(render_params.cut_hole_fill_rgb),
                "outline_rgb": list(render_params.cut_hole_outline_rgb),
            }
        else:
            trace_payload["query_spec"]["params"].update(
                {
                    "mark_count": int(dataset["mark_count"]),
                    "fold_axis": str(dataset["fold_axis"]),
                    "fold_direction": str(dataset["fold_direction"]),
                }
            )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def _generate_overlay_result(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        query_id_probabilities: Dict[str, float],
    ) -> TaskOutput:
        scene_params = _decouple_sampling(
            params,
            factor=_axis_decoupling_factor(
                params,
                query_id="overlay_result",
                include_scene_axis=False,
            ),
        )
        scene_variant, scene_variant_probabilities = resolve_overlay_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        builder_params = dict(params)
        builder_params["query_id"] = "overlay_union_same_grid"
        dataset = build_overlay_dataset_for_variant(
            query_id="overlay_union_same_grid",
            params=builder_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_OVERLAY_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_overlay_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = _resolve_transform_scene_style(
            int(instance_seed),
            task_id=str(self.task_id),
            scene_id=OVERLAY_SCENE_ID,
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            paper_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            paper_shadow_rgb=tuple(int(value) for value in scene_style.background_accent_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            mark_fill_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            mark_outline_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            instruction_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_puzzle_overlay_scene(
            background,
            scene_variant=str(scene_variant),
            grid_size=int(dataset["grid_size"]),
            left_mark_specs=list(dataset["left_mark_specs"]),
            right_mark_specs=list(dataset["right_mark_specs"]),
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
                "object_description_overlay_strip",
                "object_description_overlay_card",
                "object_description_overlay_outline",
                "annotation_hint_overlay_result",
                "json_example_overlay_result",
                "json_example_answer_only_overlay_result",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key="overlay_result",
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_overlay_result"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example_overlay_result"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_overlay_result"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_choice_id = str(dataset["correct_option_choice_id"])
        annotation_projection = projected_puzzle_bbox_annotation(
            rendered_scene.option_choice_bbox_map,
            [str(correct_option_choice_id)],
        )
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        sheet_scan = max(
            normalize_int_with_bounds(int(dataset["left_mark_count"]), [2, 5]),
            normalize_int_with_bounds(int(dataset["right_mark_count"]), [2, 5]),
        )
        grid_scan = normalize_int_with_bounds(int(dataset["grid_size"]), [4, 5])
        option_scan = normalize_int_with_bounds(int(dataset["option_count"]), [5, 6])
        union_scan = normalize_int_with_bounds(int(dataset["union_mark_count"]), [3, 9])
        overlap_scan = normalize_int_with_bounds(int(dataset["overlap_count"]), [1, 2])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT["overlay_result"])
            + (0.18 * float(overlap_scan))
            + (0.12 * float(union_scan))
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float((0.4 * grid_scan) + (0.35 * sheet_scan) + (0.25 * option_scan)),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_spatial_transform_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": "overlay_result",
                    "internal_query_id": "overlay_union_same_grid",
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "correct_option_choice_id": str(correct_option_choice_id),
                    "view_family": str(dataset["view_family"]),
                },
            },
            "query_spec": {
                "query_id": "overlay_result",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": "overlay_result",
                    "internal_query_id": "overlay_union_same_grid",
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "grid_size": int(dataset["grid_size"]),
                    "grid_size_range": list(dataset["grid_size_range"]),
                    "option_count": int(dataset["option_count"]),
                    "option_count_range": list(dataset["option_count_range"]),
                    "left_mark_count": int(dataset["left_mark_count"]),
                    "right_mark_count": int(dataset["right_mark_count"]),
                    "sheet_mark_count_range": list(dataset["sheet_mark_count_range"]),
                    "overlap_count": int(dataset["overlap_count"]),
                    "overlap_count_range": list(dataset["overlap_count_range"]),
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
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "text_style": {
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                    "combine_symbol_font_size_px": int(render_params.combine_symbol_font_size_px),
                },
                "mark_style": {
                    "shape": str(render_params.mark_shape),
                    "fill_rgb": list(render_params.mark_fill_rgb),
                    "outline_rgb": list(render_params.mark_outline_rgb),
                },
            },
            "render_map": with_puzzle_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "reference_panel_bbox_px": list(rendered_scene.reference_panel_bbox_px),
                    "source_sheet_bboxes_px": {
                        str(key): list(value) for key, value in rendered_scene.source_sheet_bbox_map.items()
                    },
                    "option_choice_bboxes_px": {
                        str(key): list(value) for key, value in rendered_scene.option_choice_bbox_map.items()
                    },
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                "query_id": "overlay_result",
                "internal_query_id": "overlay_union_same_grid",
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "grid_size": int(dataset["grid_size"]),
                "grid_size_range": list(dataset["grid_size_range"]),
                "option_count": int(dataset["option_count"]),
                "option_count_range": list(dataset["option_count_range"]),
                "sheet_mark_count_range": list(dataset["sheet_mark_count_range"]),
                "overlap_count_range": list(dataset["overlap_count_range"]),
                "left_cells": [list(cell) for cell in dataset["left_cells"]],
                "right_cells": [list(cell) for cell in dataset["right_cells"]],
                "overlap_cells": [list(cell) for cell in dataset["overlap_cells"]],
                "union_cells": [list(cell) for cell in dataset["union_cells"]],
                "left_mark_specs": [dict(item) for item in dataset["left_mark_specs"]],
                "right_mark_specs": [dict(item) for item in dataset["right_mark_specs"]],
                "left_mark_count": int(dataset["left_mark_count"]),
                "right_mark_count": int(dataset["right_mark_count"]),
                "mark_shape": str(render_params.mark_shape),
                "overlap_count": int(dataset["overlap_count"]),
                "union_mark_count": int(dataset["union_mark_count"]),
                "option_specs": [dict(spec) for spec in dataset["option_specs"]],
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_choice_id": str(correct_option_choice_id),
                "supporting_option_choice_ids": [str(item) for item in dataset["valid_option_choice_ids"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "complexity_components": dict(complexity.complexity_components),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
            "projected_annotation": dict(annotation_projection),
            "complexity": complexity.to_dict(),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id="overlay_result",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

@register_task
class PuzzlesSpatialPaperFoldResultLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialTransformResultBaseTask):
    """Choose the labeled option showing the folded paper result."""

    task_id = PAPER_FOLD_RESULT_LABEL_TASK_ID
    fixed_query_id = "paper_fold_result"
    public_scene_id = PAPER_FOLD_SCENE_ID


@register_task
class PuzzlesSpatialPaperFoldCutResultLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialTransformResultBaseTask):
    """Choose the labeled option showing the unfolded paper-cut result."""

    task_id = PAPER_FOLD_CUT_RESULT_LABEL_TASK_ID
    fixed_query_id = "paper_fold_cut_result"
    public_scene_id = PAPER_FOLD_CUT_SCENE_ID


@register_task
class PuzzlesSpatialOverlayResultLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialTransformResultBaseTask):
    """Choose the labeled option showing the overlay union result."""

    task_id = OVERLAY_RESULT_LABEL_TASK_ID
    fixed_query_id = "overlay_result"
    public_scene_id = OVERLAY_SCENE_ID


__all__ = [
    "PuzzlesSpatialOverlayResultLabelTask",
    "PuzzlesSpatialPaperFoldCutResultLabelTask",
    "PuzzlesSpatialPaperFoldResultLabelTask",
]
