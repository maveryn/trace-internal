"""Shared dataset builders and render defaults for cycle-diagram tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import resolve_required_int_bounds
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.render_variation import resolve_layout_jitter
from .common import (
    resolve_diagrams_axis_variant,
    resolve_diagrams_int_param,
    resolve_diagrams_rgb_triple,
    sample_diagram_short_names,
)


SUPPORTED_DIAGRAM_CYCLE_SCENE_VARIANTS: Tuple[str, ...] = ("cycle_ring",)
SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS: Tuple[str, ...] = ("offset_stage_label",)
SUPPORTED_DIAGRAM_CYCLE_QUERY_RELATIONSHIPS: Tuple[str, ...] = ("after", "before")
SUPPORTED_DIAGRAM_CYCLE_DIRECTIONS: Tuple[str, ...] = (
    "clockwise",
    "counterclockwise",
)
SOURCE_CYCLE_QUERY_ID_QUERY_RELATIONSHIPS: Dict[str, str] = {
    "after_k_steps": "after",
    "before_k_steps": "before",
    "after_offset_stage_label": "after",
    "before_offset_stage_label": "before",
}

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
    stage_count_max: int = 12
    step_count_min: int = 2


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
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    label_color_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    edge_color_rgb: Tuple[int, int, int]
    layout_jitter_meta: Dict[str, Any]


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


def resolve_cycle_query_id(
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
        supported_variants=SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def normalize_cycle_query_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return params with source before/after query ids mapped to query relationship."""

    normalized = dict(params)
    explicit_query_id = normalized.get("query_id")
    if explicit_query_id is None:
        return normalized
    query_id = str(explicit_query_id)
    if query_id not in SOURCE_CYCLE_QUERY_ID_QUERY_RELATIONSHIPS:
        return normalized
    query_relationship = str(SOURCE_CYCLE_QUERY_ID_QUERY_RELATIONSHIPS[query_id])
    explicit_relationship = normalized.get("query_relationship")
    if explicit_relationship is not None and str(explicit_relationship) != str(query_relationship):
        raise ValueError(
            "source cycle query_id conflicts with query_relationship: "
            f"{query_id} vs {explicit_relationship}"
        )
    normalized["query_id"] = str(SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS[0])
    normalized["query_relationship"] = str(query_relationship)
    return normalized


def resolve_cycle_query_relationship(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve whether the prompt asks for a stage before or after the query stage."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_CYCLE_QUERY_RELATIONSHIPS,
        task_id=str(task_id),
        explicit_key="query_relationship",
        weights_key="query_relationship_weights",
        balance_flag_key="balanced_query_relationship_sampling",
        axis_namespace="query_relationship",
    )


def resolve_cycle_direction(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active visible arrow direction for a cycle scene."""

    direction_params: Mapping[str, Any] = params
    return resolve_diagrams_axis_variant(
        params=direction_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_CYCLE_DIRECTIONS,
        task_id=str(task_id),
        explicit_key="cycle_direction",
        weights_key="cycle_direction_weights",
        balance_flag_key="balanced_cycle_direction_sampling",
        axis_namespace="cycle_direction",
    )


def resolve_cycle_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> CycleRenderParams:
    """Resolve rendering params for cycle scenes."""

    def _int(key: str, fallback: int) -> int:
        return resolve_diagrams_int_param(
            params,
            render_defaults,
            key,
            fallback,
            instance_seed=instance_seed,
            namespace="pages.cycle",
        )

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(
            params,
            render_defaults,
            key,
            fallback,
            instance_seed=instance_seed,
            namespace="pages.cycle",
        )

    layout_jitter_meta = resolve_layout_jitter(
        params,
        render_defaults,
        instance_seed=instance_seed,
        namespace="pages.cycle.layout",
    )

    return CycleRenderParams(
        canvas_width=_int("canvas_width", 1200),
        canvas_height=_int("canvas_height", 900),
        outer_margin_px=_int("outer_margin_px", 52),
        panel_padding_px=_int("panel_padding_px", 28),
        panel_corner_radius_px=_int("panel_corner_radius_px", 30),
        title_font_size_px=_int("title_font_size_px", 32),
        title_band_height_px=_int("title_band_height_px", 78),
        node_width_px=_int("node_width_px", 122),
        node_height_px=_int("node_height_px", 58),
        node_corner_radius_px=_int("node_corner_radius_px", 24),
        node_border_width_px=_int("node_border_width_px", 3),
        ring_radius_x_px=_int("ring_radius_x_px", 360),
        ring_radius_y_px=_int("ring_radius_y_px", 250),
        edge_width_px=_int("edge_width_px", 5),
        arrow_head_length_px=_int("arrow_head_length_px", 17),
        arrow_head_width_px=_int("arrow_head_width_px", 14),
        label_font_size_px=_int("label_font_size_px", 22),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        node_fill_rgb=_triple("node_fill_rgb", (243, 247, 255)),
        node_border_rgb=_triple("node_border_rgb", (77, 90, 109)),
        label_color_rgb=_triple("label_color_rgb", (29, 34, 41)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        edge_color_rgb=_triple("edge_color_rgb", (88, 99, 114)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _title(*, rng) -> str:
    """Sample one short cycle scene title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def build_cycle_offset_dataset(
    *,
    query_id: str,
    query_relationship: str,
    scene_variant: str,
    cycle_direction: str,
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
    max_step_count = max(1, int(stage_count_max) - 1)
    step_count_min, step_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="step_count_min",
        max_key="step_count_max",
        fallback_min=int(defaults.step_count_min),
        fallback_max=int(max_step_count),
        context=f"{task_id} step count",
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
    step_count_max_for_stage = min(int(step_count_max), max(1, int(stage_count) - 1))
    step_count_min_for_stage = min(int(step_count_min), int(step_count_max_for_stage))
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
        int(step_count_min_for_stage)
        + (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.step_count",
            )
            % max(1, int(step_count_max_for_stage) - int(step_count_min_for_stage) + 1)
        )
    )
    if str(cycle_direction) not in SUPPORTED_DIAGRAM_CYCLE_DIRECTIONS:
        raise ValueError(f"unsupported cycle direction: {cycle_direction}")
    direction_delta = 1 if str(cycle_direction) == "clockwise" else -1
    if str(query_id) not in SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS:
        raise ValueError(f"unsupported cycle query id: {query_id}")

    if str(query_relationship) == "after":
        answer_index = int((query_index + (direction_delta * step_count)) % int(stage_count))
        relationship = "after"
        question_text = (
            f"Following the arrows around the cycle, what stage is {step_count} "
            f"{'step' if int(step_count) == 1 else 'steps'} after {stage_labels[query_index]}? "
            "Return the exact label shown."
        )
    elif str(query_relationship) == "before":
        answer_index = int((query_index - (direction_delta * step_count)) % int(stage_count))
        relationship = "before"
        question_text = (
            f"Following the arrows around the cycle, what stage is {step_count} "
            f"{'step' if int(step_count) == 1 else 'steps'} before {stage_labels[query_index]}? "
            "Return the exact label shown."
        )
    else:
        raise ValueError(f"unsupported cycle query relationship: {query_relationship}")

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
                "target_stage_id": f"stage_{(index + direction_delta) % int(stage_count)}",
                "direction": str(cycle_direction),
            }
        )

    return {
        "scene_title": _title(rng=rng),
        "query_id": str(query_id),
        "scene_variant": "cycle_ring",
        "question_text": str(question_text),
        "question_format": "cycle_offset_stage_label",
        "view_family": "cycle_diagram",
        "direction": str(cycle_direction),
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
    "SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS",
    "SUPPORTED_DIAGRAM_CYCLE_QUERY_RELATIONSHIPS",
    "SUPPORTED_DIAGRAM_CYCLE_DIRECTIONS",
    "SOURCE_CYCLE_QUERY_ID_QUERY_RELATIONSHIPS",
    "build_cycle_offset_dataset",
    "normalize_cycle_query_params",
    "resolve_cycle_direction",
    "resolve_cycle_query_relationship",
    "resolve_cycle_render_params",
    "resolve_cycle_scene_variant",
    "resolve_cycle_query_id",
]
