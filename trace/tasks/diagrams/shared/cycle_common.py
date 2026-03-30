"""Shared dataset builders and render defaults for cycle-diagram tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.common import (
    resolve_diagrams_axis_variant,
    resolve_diagrams_int_param,
    resolve_diagrams_rgb_triple,
    sample_diagram_short_names,
)


SUPPORTED_DIAGRAM_CYCLE_SCENE_VARIANTS: Tuple[str, ...] = ("cycle_ring",)
SUPPORTED_DIAGRAM_CYCLE_TASK_VARIANTS: Tuple[str, ...] = (
    "after_k_steps",
    "before_k_steps",
)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Cycle Diagram",
    "Stage Loop",
    "Process Ring",
    "Cycle Overview",
    "Loop Stages",
)


@dataclass(frozen=True)
class CycleDefaults:
    """Default generation bounds for cycle offset-stage tasks."""

    stage_count_min: int = 5
    stage_count_max: int = 10


@dataclass(frozen=True)
class CycleRenderParams:
    """Resolved rendering knobs for one cycle-diagram scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    title_font_size_px: int
    title_band_height_px: int
    node_width_px: int
    node_height_px: int
    node_corner_radius_px: int
    node_border_width_px: int
    ring_radius_x_px: int
    ring_radius_y_px: int
    edge_width_px: int
    arrow_head_length_px: int
    arrow_head_width_px: int
    label_font_size_px: int
    badge_width_px: int
    badge_height_px: int
    badge_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    label_color_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    edge_color_rgb: Tuple[int, int, int]
    badge_fill_rgb: Tuple[int, int, int]
    badge_border_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]


def resolve_cycle_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active cycle scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_CYCLE_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_cycle_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active cycle semantic variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_CYCLE_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_cycle_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> CycleRenderParams:
    """Resolve rendering params for cycle scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(params, render_defaults, key, fallback)

    return CycleRenderParams(
        canvas_width=int(resolve_diagrams_int_param(params, render_defaults, "canvas_width", 1200)),
        canvas_height=int(resolve_diagrams_int_param(params, render_defaults, "canvas_height", 900)),
        outer_margin_px=int(resolve_diagrams_int_param(params, render_defaults, "outer_margin_px", 52)),
        panel_padding_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_padding_px", 28)),
        panel_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_corner_radius_px", 30)),
        title_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "title_font_size_px", 32)),
        title_band_height_px=int(resolve_diagrams_int_param(params, render_defaults, "title_band_height_px", 78)),
        node_width_px=int(resolve_diagrams_int_param(params, render_defaults, "node_width_px", 122)),
        node_height_px=int(resolve_diagrams_int_param(params, render_defaults, "node_height_px", 58)),
        node_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "node_corner_radius_px", 24)),
        node_border_width_px=int(resolve_diagrams_int_param(params, render_defaults, "node_border_width_px", 3)),
        ring_radius_x_px=int(resolve_diagrams_int_param(params, render_defaults, "ring_radius_x_px", 360)),
        ring_radius_y_px=int(resolve_diagrams_int_param(params, render_defaults, "ring_radius_y_px", 250)),
        edge_width_px=int(resolve_diagrams_int_param(params, render_defaults, "edge_width_px", 5)),
        arrow_head_length_px=int(resolve_diagrams_int_param(params, render_defaults, "arrow_head_length_px", 17)),
        arrow_head_width_px=int(resolve_diagrams_int_param(params, render_defaults, "arrow_head_width_px", 14)),
        label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "label_font_size_px", 22)),
        badge_width_px=int(resolve_diagrams_int_param(params, render_defaults, "badge_width_px", 136)),
        badge_height_px=int(resolve_diagrams_int_param(params, render_defaults, "badge_height_px", 42)),
        badge_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "badge_font_size_px", 18)),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        node_fill_rgb=_triple("node_fill_rgb", (243, 247, 255)),
        node_border_rgb=_triple("node_border_rgb", (77, 90, 109)),
        label_color_rgb=_triple("label_color_rgb", (29, 34, 41)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        edge_color_rgb=_triple("edge_color_rgb", (88, 99, 114)),
        badge_fill_rgb=_triple("badge_fill_rgb", (246, 248, 252)),
        badge_border_rgb=_triple("badge_border_rgb", (180, 188, 200)),
        badge_text_rgb=_triple("badge_text_rgb", (61, 69, 79)),
    )


def _title(*, rng) -> str:
    """Sample one short cycle scene title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def build_cycle_offset_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CycleDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one cycle-diagram offset-stage dataset instance."""

    del scene_variant  # The first active cycle renderer keeps one shared visual grammar.
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    stage_count_min, stage_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="stage_count_min",
        max_key="stage_count_max",
        fallback_min=int(defaults.stage_count_min),
        fallback_max=int(defaults.stage_count_max),
        context=f"{task_id} stage count",
    )
    stage_count = int(
        stage_count_min
        + (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.stage_count",
            )
            % (int(stage_count_max) - int(stage_count_min) + 1)
        )
    )
    stage_labels = sample_diagram_short_names(count=int(stage_count), rng=rng)
    query_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.query_stage_index",
        )
        % int(stage_count)
    )
    step_count = int(
        1
        + (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.step_count",
            )
            % max(1, int(stage_count) - 1)
        )
    )
    if str(task_variant) == "after_k_steps":
        answer_index = int((query_index + step_count) % int(stage_count))
        relationship = "after"
        question_text = (
            f"Moving clockwise around the cycle, what stage is {step_count} "
            f"{'step' if int(step_count) == 1 else 'steps'} after {stage_labels[query_index]}? "
            "Return the exact label shown."
        )
    elif str(task_variant) == "before_k_steps":
        answer_index = int((query_index - step_count) % int(stage_count))
        relationship = "before"
        question_text = (
            f"Moving clockwise around the cycle, what stage is {step_count} "
            f"{'step' if int(step_count) == 1 else 'steps'} before {stage_labels[query_index]}? "
            "Return the exact label shown."
        )
    else:
        raise ValueError(f"unsupported cycle task variant: {task_variant}")

    stage_specs = []
    edge_specs = []
    for index, label in enumerate(stage_labels):
        stage_specs.append(
            {
                "stage_id": f"stage_{index}",
                "stage_bbox_id": f"stage_bbox_{index}",
                "stage_label_bbox_id": f"stage_label_bbox_{index}",
                "stage_label": str(label),
                "order_index": int(index),
            }
        )
        edge_specs.append(
            {
                "edge_id": f"edge_{index}",
                "source_stage_id": f"stage_{index}",
                "target_stage_id": f"stage_{(index + 1) % int(stage_count)}",
            }
        )

    return {
        "scene_title": _title(rng=rng),
        "task_variant": str(task_variant),
        "scene_variant": "cycle_ring",
        "question_text": str(question_text),
        "question_format": "cycle_offset_stage_label",
        "view_family": "cycle_diagram",
        "direction": "clockwise",
        "stage_count": int(stage_count),
        "step_count": int(step_count),
        "query_stage_index": int(query_index),
        "query_stage_id": f"stage_{query_index}",
        "query_stage_label": str(stage_labels[query_index]),
        "answer_stage_index": int(answer_index),
        "answer_stage_id": f"stage_{answer_index}",
        "answer_stage_label": str(stage_labels[answer_index]),
        "answer_stage_bbox_id": f"stage_bbox_{answer_index}",
        "query_relationship": str(relationship),
        "stage_specs": stage_specs,
        "edge_specs": edge_specs,
    }


__all__ = [
    "CycleDefaults",
    "CycleRenderParams",
    "SUPPORTED_DIAGRAM_CYCLE_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_CYCLE_TASK_VARIANTS",
    "build_cycle_offset_dataset",
    "resolve_cycle_render_params",
    "resolve_cycle_scene_variant",
    "resolve_cycle_task_variant",
]
