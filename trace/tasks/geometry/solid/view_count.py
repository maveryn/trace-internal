"""Geometry solid-view counting task with cube-stack orthographic projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_solid_view_complexity
from ..shared.consolidated_sampling import resolve_compatible_scene_query_variants
from ..shared.graph_paper import resolve_square_canvas_size
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.solid_scene import (
    FRONT_VIEW_QUERY,
    RIGHT_VIEW_QUERY,
    TOP_VIEW_QUERY,
    CubeStack,
    build_solid_render_style,
    draw_cube_stack_panel,
    draw_query_view_panel,
    projected_view_cells,
    sample_connected_cube_stack,
    view_grid_dimensions,
    view_title_for_query,
)


TASK_ID = "task_geometry_solid_view_count"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("cube_stack",)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    TOP_VIEW_QUERY,
    FRONT_VIEW_QUERY,
    RIGHT_VIEW_QUERY,
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "cube_stack": SUPPORTED_QUERY_VARIANTS,
}

POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="solid")
POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="solid")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for geometry solid-view scenes."""

    canvas_size_min: int = 720
    canvas_size_max: int = 800
    scene_supersample_scale: int = 2
    line_width: int = 3
    line_width_min: int = 2
    line_width_max: int = 4
    panel_gap_px: int = 22
    outer_margin_px: int = 28
    stack_panel_ratio: float = 0.58
    panel_title_font_size_px: int = 20
    panel_title_font_size_min: int = 18
    panel_title_font_size_max: int = 24
    footprint_width_min: int = 2
    footprint_width_max: int = 4
    footprint_depth_min: int = 2
    footprint_depth_max: int = 4
    max_height: int = 3
    total_cubes_min: int = 4
    total_cubes_max: int = 9
    target_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7)
    min_distinct_view_counts: int = 2
    allow_full_query_projection: bool = False


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved scene/query axes and answer-count support for one instance."""

    scene_variant: str
    query_variant: str
    target_count: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedSolidScene:
    """Rendered solid-view scene payload with evidence + trace artifacts."""

    stack: CubeStack
    answer_value: int
    evidence_bboxes: List[List[float]]
    query_panel_bbox: List[float]
    stack_panel_bbox: List[float]
    query_grid_bbox: List[float]
    query_grid_dims: Tuple[int, int]
    projection_cells: List[List[int]]
    visible_counts_by_query: Dict[str, int]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "solid")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _target_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported visible-cell counts for solid-view queries."""

    raw_support = params.get(
        "target_count_support",
        group_default(_GEN_DEFAULTS, "target_count_support", _DEFAULTS.target_count_support),
    )
    support: List[int] = []
    for value in raw_support:
        normalized = int(value)
        if 1 <= int(normalized) <= 9 and int(normalized) not in support:
            support.append(int(normalized))
    if not support:
        raise ValueError("target_count_support must contain at least one value in 1..9")
    return tuple(sorted(support))


def _resolve_target_count(
    rng,
    *,
    instance_seed: int,
    query_variant: str,
    params: Mapping[str, Any],
) -> Tuple[int, Dict[str, float]]:
    """Resolve the answer-count support with deterministic balanced defaults."""

    support = _target_count_support(params)
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    raw_weights = params.get("target_count_weights", {str(value): 1.0 for value in support})
    if not isinstance(raw_weights, Mapping):
        raise ValueError("target_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if int(key) in set(support)
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in support])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))

    balanced_enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    overridden = any(params.get(key) is not None for key in ("target_count", "target_count_weights"))
    if bool(balanced_enabled) and (not overridden):
        ordered_support = [int(value) for value in support]
        selection_index = abs(int(params.get("_sampling_index", instance_seed)))
        selected = int(ordered_support[int(selection_index) % len(ordered_support)])
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve chart-style scene/query axes plus balanced target-count support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_variants=SUPPORTED_QUERY_VARIANTS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_variant",
    )
    target_count, target_count_probs = _resolve_target_count(
        axis_rng,
        instance_seed=int(instance_seed),
        query_variant=str(query_variant),
        params=params,
    )
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        target_count=int(target_count),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        target_count_probabilities=dict(target_count_probs),
    )


def _sample_stack_matching_target(
    rng,
    *,
    query_variant: str,
    target_count: int,
    params: Mapping[str, Any],
) -> Tuple[CubeStack, Dict[str, int]]:
    """Sample one non-degenerate cube stack whose queried view matches the target count."""

    width_min = int(params.get("footprint_width_min", group_default(_GEN_DEFAULTS, "footprint_width_min", _DEFAULTS.footprint_width_min)))
    width_max = int(params.get("footprint_width_max", group_default(_GEN_DEFAULTS, "footprint_width_max", _DEFAULTS.footprint_width_max)))
    depth_min = int(params.get("footprint_depth_min", group_default(_GEN_DEFAULTS, "footprint_depth_min", _DEFAULTS.footprint_depth_min)))
    depth_max = int(params.get("footprint_depth_max", group_default(_GEN_DEFAULTS, "footprint_depth_max", _DEFAULTS.footprint_depth_max)))
    total_cubes_min = max(
        int(target_count),
        int(params.get("total_cubes_min", group_default(_GEN_DEFAULTS, "total_cubes_min", _DEFAULTS.total_cubes_min))),
    )
    total_cubes_max = max(
        int(total_cubes_min),
        int(params.get("total_cubes_max", group_default(_GEN_DEFAULTS, "total_cubes_max", _DEFAULTS.total_cubes_max))),
    )
    max_height = int(params.get("max_height", group_default(_GEN_DEFAULTS, "max_height", _DEFAULTS.max_height)))
    min_distinct_view_counts = int(
        params.get(
            "min_distinct_view_counts",
            group_default(_GEN_DEFAULTS, "min_distinct_view_counts", _DEFAULTS.min_distinct_view_counts),
        )
    )
    allow_full_query_projection = bool(
        params.get(
            "allow_full_query_projection",
            group_default(_GEN_DEFAULTS, "allow_full_query_projection", _DEFAULTS.allow_full_query_projection),
        )
    )

    for _ in range(512):
        stack = sample_connected_cube_stack(
            rng,
            width_min=int(width_min),
            width_max=int(width_max),
            depth_min=int(depth_min),
            depth_max=int(depth_max),
            total_cubes_min=int(total_cubes_min),
            total_cubes_max=int(total_cubes_max),
            max_height=int(max_height),
        )
        if int(stack.max_height) < 2 or len(stack.heights) < 2:
            continue
        visible_counts_by_query = {
            TOP_VIEW_QUERY: len(projected_view_cells(stack, query_variant=TOP_VIEW_QUERY)),
            FRONT_VIEW_QUERY: len(projected_view_cells(stack, query_variant=FRONT_VIEW_QUERY)),
            RIGHT_VIEW_QUERY: len(projected_view_cells(stack, query_variant=RIGHT_VIEW_QUERY)),
        }
        if int(visible_counts_by_query[str(query_variant)]) != int(target_count):
            continue
        query_grid_dims = view_grid_dimensions(stack, query_variant=str(query_variant))
        if (not allow_full_query_projection) and (
            int(visible_counts_by_query[str(query_variant)]) >= int(query_grid_dims[0]) * int(query_grid_dims[1])
        ):
            continue
        if len(set(int(value) for value in visible_counts_by_query.values())) < int(min_distinct_view_counts):
            continue
        return stack, {str(key): int(value) for key, value in visible_counts_by_query.items()}
    raise RuntimeError("failed to sample a cube stack matching the requested solid-view target count")


def _resolve_canvas_size(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve one square canvas size for the solid-view scene."""

    return int(
        resolve_square_canvas_size(
            rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_min=_DEFAULTS.canvas_size_min,
            fallback_max=_DEFAULTS.canvas_size_max,
        )
    )


def _panel_layout(
    *,
    canvas_size: int,
    scene_scale: int,
    params: Mapping[str, Any],
) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
    """Resolve left stack-panel and right query-panel bounding boxes."""

    outer_margin_px = float(params.get("outer_margin_px", group_default(_RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px)))
    panel_gap_px = float(params.get("panel_gap_px", group_default(_RENDER_DEFAULTS, "panel_gap_px", _DEFAULTS.panel_gap_px)))
    stack_ratio = float(params.get("stack_panel_ratio", group_default(_RENDER_DEFAULTS, "stack_panel_ratio", _DEFAULTS.stack_panel_ratio)))

    full_size = float(canvas_size * scene_scale)
    margin = float(outer_margin_px * scene_scale)
    gap = float(panel_gap_px * scene_scale)
    usable_width = max(160.0, float(full_size - (2.0 * margin) - gap))
    usable_height = max(160.0, float(full_size - (2.0 * margin)))
    stack_width = float(round(usable_width * stack_ratio))
    query_width = float(usable_width - stack_width)
    left = float(margin)
    top = float(margin)
    stack_bbox = (
        float(left),
        float(top),
        float(left + stack_width),
        float(top + usable_height),
    )
    query_left = float(stack_bbox[2] + gap)
    query_bbox = (
        float(query_left),
        float(top),
        float(query_left + query_width),
        float(top + usable_height),
    )
    return stack_bbox, query_bbox


def _sample_panel_title_font_size(
    rng,
    *,
    params: Mapping[str, Any],
) -> int:
    """Resolve one panel-title font size in final-image pixels."""

    explicit = params.get("panel_title_font_size_px")
    if explicit is not None:
        return max(10, int(explicit))
    minimum = int(group_default(_RENDER_DEFAULTS, "panel_title_font_size_min", _DEFAULTS.panel_title_font_size_min))
    maximum = int(group_default(_RENDER_DEFAULTS, "panel_title_font_size_max", _DEFAULTS.panel_title_font_size_max))
    return max(10, int(rng.randint(int(minimum), int(maximum))))


def _render_scene(
    rng,
    *,
    query: _ResolvedQuery,
    canvas_size: int,
    scene_scale: int,
    line_width: int,
    panel_title_font_size_px: int,
    params: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    shape_style,
    draw: ImageDraw.ImageDraw,
) -> _RenderedSolidScene:
    """Sample one stack matching the target count and render both panels."""

    stack, visible_counts_by_query = _sample_stack_matching_target(
        rng,
        query_variant=str(query.query_variant),
        target_count=int(query.target_count),
        params=params,
    )
    style = build_solid_render_style(shape_style=shape_style, background_meta=background_meta)
    stack_panel_bbox, query_panel_bbox = _panel_layout(
        canvas_size=int(canvas_size),
        scene_scale=int(scene_scale),
        params=params,
    )
    stack_panel_meta = draw_cube_stack_panel(
        draw,
        panel_bbox=stack_panel_bbox,
        stack=stack,
        scene_scale=int(scene_scale),
        line_width=int(line_width) * int(scene_scale),
        title_text="Cube stack",
        title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
        style=style,
    )

    projection_cells = projected_view_cells(stack, query_variant=str(query.query_variant))
    query_panel_meta = draw_query_view_panel(
        draw,
        panel_bbox=query_panel_bbox,
        grid_dims=view_grid_dimensions(stack, query_variant=str(query.query_variant)),
        occupied_cells=projection_cells,
        scene_scale=int(scene_scale),
        line_width=int(max(1, line_width - 1)) * int(scene_scale),
        title_text=view_title_for_query(str(query.query_variant)),
        title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
        style=style,
    )

    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": f"cube_{index:02d}",
            "type": "cube",
            "cell": [int(cell_x), int(cell_y), int(cell_z)],
        }
        for index, (cell_x, cell_y, cell_z) in enumerate(
            sorted(
                [
                    (x_value, y_value, z_value)
                    for (x_value, y_value), height in stack.heights.items()
                    for z_value in range(int(height))
                ],
                key=lambda item: (int(item[2]), int(item[1]), int(item[0])),
            )
        )
    ]
    scene_entities.append(
        {
            "entity_id": "query_panel",
            "type": "projection_panel",
            "bbox": list(query_panel_meta["panel_bbox"]),
            "query_variant": str(query.query_variant),
            "grid_dimensions": [int(view_grid_dimensions(stack, query_variant=str(query.query_variant))[0]), int(view_grid_dimensions(stack, query_variant=str(query.query_variant))[1])],
        }
    )

    evidence_bboxes = [list(bbox) for bbox in query_panel_meta["occupied_bboxes"]]
    projection_cells_out = [[int(col), int(row)] for col, row in projection_cells]
    render_map = {
        "image_id": "img0",
        "stack_panel_bbox": list(stack_panel_meta["panel_bbox"]),
        "query_panel_bbox": list(query_panel_meta["panel_bbox"]),
        "query_grid_bbox": list(query_panel_meta["grid_bbox"]),
        "query_grid_dimensions": list(view_grid_dimensions(stack, query_variant=str(query.query_variant))),
        "query_view_title": str(view_title_for_query(str(query.query_variant))),
        "projection_cells": list(projection_cells_out),
        "projection_cell_bboxes": list(evidence_bboxes),
        "stack_width": int(stack.width),
        "stack_depth": int(stack.depth),
        "stack_heights": [
            {"x": int(x_value), "y": int(y_value), "height": int(height)}
            for (x_value, y_value), height in sorted(stack.heights.items())
        ],
    }
    return _RenderedSolidScene(
        stack=stack,
        answer_value=int(len(evidence_bboxes)),
        evidence_bboxes=list(evidence_bboxes),
        query_panel_bbox=list(query_panel_meta["panel_bbox"]),
        stack_panel_bbox=list(stack_panel_meta["panel_bbox"]),
        query_grid_bbox=list(query_panel_meta["grid_bbox"]),
        query_grid_dims=tuple(int(value) for value in view_grid_dimensions(stack, query_variant=str(query.query_variant))),
        projection_cells=list(projection_cells_out),
        visible_counts_by_query={str(key): int(value) for key, value in visible_counts_by_query.items()},
        scene_entities=scene_entities,
        render_map=render_map,
    )


@register_task
class GeometrySolidViewCountTask:
    """Count occupied unit cells in one requested orthographic view of a cube stack."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "solid"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_axes(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")

        last_error: Exception | None = None
        canvas_size = None
        scene_scale = None
        line_width = None
        panel_title_font_size_px = None
        image = None
        background_meta = None
        shape_style = None
        rendered_scene = None

        for _ in range(max(1, int(max_attempts))):
            try:
                canvas_size_attempt = _resolve_canvas_size(rng, params=params)
                scene_scale_attempt = max(
                    1,
                    int(
                        params.get(
                            "scene_supersample_scale",
                            group_default(_RENDER_DEFAULTS, "scene_supersample_scale", _DEFAULTS.scene_supersample_scale),
                        )
                    ),
                )
                render_canvas_size = int(canvas_size_attempt) * int(scene_scale_attempt)
                line_width_attempt = sample_int_render_param(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    key="line_width",
                    fallback=_DEFAULTS.line_width,
                    minimum_value=1,
                )
                panel_title_font_size_px_attempt = _sample_panel_title_font_size(rng, params=params)
                image_attempt, background_meta_attempt = make_background_canvas(
                    canvas_size=int(render_canvas_size),
                    instance_seed=int(instance_seed),
                    params=dict(params),
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                    fallback_color=(252, 252, 252),
                )
                draw_attempt = ImageDraw.Draw(image_attempt)
                shape_style_attempt = sample_geometry_shape_style(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    anchor_colors=extract_background_anchor_colors(background_meta_attempt),
                )
                rendered_scene_attempt = _render_scene(
                    rng,
                    query=query,
                    canvas_size=int(canvas_size_attempt),
                    scene_scale=int(scene_scale_attempt),
                    line_width=int(line_width_attempt),
                    panel_title_font_size_px=int(panel_title_font_size_px_attempt),
                    params=params,
                    background_meta=background_meta_attempt,
                    shape_style=shape_style_attempt,
                    draw=draw_attempt,
                )
                canvas_size = int(canvas_size_attempt)
                scene_scale = int(scene_scale_attempt)
                line_width = int(line_width_attempt)
                panel_title_font_size_px = int(panel_title_font_size_px_attempt)
                image = image_attempt
                background_meta = dict(background_meta_attempt)
                shape_style = shape_style_attempt
                rendered_scene = rendered_scene_attempt
                break
            except Exception as exc:
                last_error = exc
                continue

        if (
            rendered_scene is None
            or image is None
            or background_meta is None
            or shape_style is None
            or canvas_size is None
            or scene_scale is None
            or line_width is None
            or panel_title_font_size_px is None
        ):
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        out_image = image
        if int(scene_scale) > 1:
            out_image = out_image.resize((int(canvas_size), int(canvas_size)), resample=Image.Resampling.LANCZOS)
        out_image, post_noise_meta = apply_post_image_noise(
            out_image,
            instance_seed=int(instance_seed),
            params=dict(params),
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        background_meta_final = dict(background_meta)
        background_meta_final["render_scale"] = int(scene_scale)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "evidence_hint_bbox_set",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=rendered_scene.evidence_bboxes,
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_bbox_set"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(rendered_scene.answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(rendered_scene.evidence_bboxes))

        query_params = {
            "scene_variant": str(query.scene_variant),
            "query_variant": str(query.query_variant),
            "task_variant": str(query.query_variant),
            "variant_probabilities": dict(query.query_variant_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "query_variant_probabilities": dict(query.query_variant_probabilities),
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_solid_view_count",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(query.scene_variant),
                    "query_variant": str(query.query_variant),
                    "task_variant": str(query.query_variant),
                    "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                    "target_count": int(query.target_count),
                },
            },
            "query_spec": {
                "task_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "scene_scale": int(scene_scale),
                "line_width_px": int(line_width),
                "panel_title_font_size_px": int(panel_title_font_size_px),
                "scene_variant": str(query.scene_variant),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(query.scene_variant),
                "query_variant": str(query.query_variant),
                "task_variant": str(query.query_variant),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "query_variant_probabilities": dict(query.query_variant_probabilities),
                "task_variant_probabilities": dict(query.query_variant_probabilities),
                "target_count": int(query.target_count),
                "target_count_probabilities": dict(query.target_count_probabilities),
                "cube_count": int(rendered_scene.stack.cube_count),
                "stack_width": int(rendered_scene.stack.width),
                "stack_depth": int(rendered_scene.stack.depth),
                "stack_max_height": int(rendered_scene.stack.max_height),
                "stack_heights": [
                    {"x": int(x_value), "y": int(y_value), "height": int(height)}
                    for (x_value, y_value), height in sorted(rendered_scene.stack.heights.items())
                ],
                "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                "projection_cells": list(rendered_scene.projection_cells),
                "question_format": "count_projection_cells",
            },
            "witness_symbolic": {
                "type": "projection_cell_set",
                "cells": list(rendered_scene.projection_cells),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "pixel_bbox_set": list(rendered_scene.evidence_bboxes),
                "projection_cells": list(rendered_scene.projection_cells),
                "query_panel_bbox": list(rendered_scene.query_panel_bbox),
                "query_grid_bbox": list(rendered_scene.query_grid_bbox),
                "query_grid_dimensions": [int(rendered_scene.query_grid_dims[0]), int(rendered_scene.query_grid_dims[1])],
            },
        }

        complexity = build_geometry_solid_view_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            query_variant=str(query.query_variant),
            cube_count=int(rendered_scene.stack.cube_count),
            max_height=int(rendered_scene.stack.max_height),
            target_count=int(query.target_count),
            evidence_count=len(rendered_scene.evidence_bboxes),
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=out_image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
