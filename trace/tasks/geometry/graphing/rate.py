"""Geometry graphing average-rate task over marked points on a plotted function."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text, draw_dashed_line
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font, resolve_scene_label_font_size_px
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import (
    build_geometry_task_complexity,
    clamp_unit_interval,
    normalize_linear,
    resolve_geometry_complexity_weights,
)
from ..shared.fixed_query_task import FixedGeometryQueryTaskMixin
from ..shared.function_graph_scene import (
    build_query_line_color,
    draw_function_polyline,
    graph_units_to_pixel_float,
)
from ..shared.graph_rendering import graph_paper_grid_from_frame
from ..shared.labeled_point_annotation import graph_point_set_annotation_artifacts
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)


TASK_ID = "task_geometry__function_graph__average_rate_value"
AVERAGE_RATE_BETWEEN_MARKED_POINTS = "average_rate_between_marked_points"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (AVERAGE_RATE_BETWEEN_MARKED_POINTS,)
DEFAULT_RATE_SUPPORT: Tuple[float, ...] = (-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0)

POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="graphing")
POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="graphing")

GraphPoint = Tuple[float, float]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallbacks for the average-rate graphing task."""

    canvas_size_min: int = 660
    canvas_size_max: int = 740
    graph_cells_min: int = 20
    graph_cells_max: int = 20
    line_width: int = 4
    guide_line_width: int = 3
    marker_radius: int = 7
    label_font_size_min: int = 18
    label_font_size_max: int = 26
    average_rate_support: Tuple[float, ...] = DEFAULT_RATE_SUPPORT


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved query and balanced average-rate target."""

    query_id: str
    target_rate: float
    query_id_probabilities: Dict[str, float]
    target_rate_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledRateScene:
    """Sampled plotted-function scene before raster rendering."""

    polyline_graph: Tuple[GraphPoint, ...]
    point_a: GraphPoint
    point_b: GraphPoint
    answer_value: float
    scene_entities: list[Dict[str, Any]]
    render_map: Dict[str, Any]
    execution_trace: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedRateScene:
    """Rendered scene and metadata-backed annotation artifacts."""

    answer_value: float
    annotation_type: str
    annotation_value: list[list[float]]
    projected_annotation: Dict[str, Any]
    witness_symbolic: Dict[str, Any]
    required_annotation_labels: list[str]
    scene_entities: list[Dict[str, Any]]
    render_map: Dict[str, Any]
    execution_trace: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "graphing")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _rate_key(value: float) -> str:
    """Return the stable metadata key for one one-decimal rate value."""

    return f"{float(value):.1f}"


def _float_tuple_default(
    defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[float],
) -> Tuple[float, ...]:
    """Resolve one numeric sequence from task-group defaults."""

    raw_value = defaults.get(str(key), fallback)
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
        raise ValueError(f"{key} must be a sequence of numbers for {TASK_ID}")
    values = tuple(round(float(value), 1) for value in raw_value)
    if not values:
        raise ValueError(f"{key} cannot be empty for {TASK_ID}")
    if any(abs(float(value)) <= 1e-9 for value in values):
        raise ValueError(f"{key} cannot include zero for {TASK_ID}")
    return values


def _target_rate_support() -> Tuple[float, ...]:
    """Return configured answer support."""

    return _float_tuple_default(
        _GEN_DEFAULTS,
        "average_rate_support",
        _DEFAULTS.average_rate_support,
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve the fixed query plus balanced target average rate."""

    explicit_query = params.get("query_id", AVERAGE_RATE_BETWEEN_MARKED_POINTS)
    query_id = str(explicit_query).strip().lower()
    if query_id not in set(SUPPORTED_QUERY_IDS):
        raise ValueError(f"unsupported query_id for {TASK_ID}: {explicit_query}")

    support = _target_rate_support()
    explicit_rate = params.get("target_rate", params.get("average_rate"))
    if explicit_rate is not None:
        target_rate = round(float(explicit_rate), 1)
        probabilities = {
            _rate_key(rate): (1.0 if abs(float(rate) - float(target_rate)) <= 1e-9 else 0.0)
            for rate in support
        }
        if all(float(value) <= 0.0 for value in probabilities.values()):
            probabilities[_rate_key(target_rate)] = 1.0
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_rate",
        )
        target_rate = float(support[int(selection_index) % len(support)])
        probability = 1.0 / float(len(support))
        probabilities = {_rate_key(rate): float(probability) for rate in support}

    return _ResolvedQuery(
        query_id=str(query_id),
        target_rate=float(target_rate),
        query_id_probabilities={AVERAGE_RATE_BETWEEN_MARKED_POINTS: 1.0},
        target_rate_probabilities=dict(sorted(probabilities.items())),
    )


def _sample_endpoint_y(rng, *, target_rate: float, delta_x: int) -> Tuple[float, float]:
    """Sample integer endpoint y-values that realize the requested rate."""

    delta_y = int(round(float(target_rate) * float(delta_x)))
    if abs(float(delta_y) - (float(target_rate) * float(delta_x))) > 1e-9:
        raise ValueError(f"target_rate {target_rate} is incompatible with delta_x {delta_x}")
    y0_min = max(-4, -4 - int(delta_y))
    y0_max = min(4, 4 - int(delta_y))
    if int(y0_min) > int(y0_max):
        raise RuntimeError(f"failed to sample endpoint y-values for target_rate={target_rate}")
    y0 = int(rng.randint(int(y0_min), int(y0_max)))
    return float(y0), float(y0 + int(delta_y))


def _sample_midpoint_y(rng, *, y0: float, y1: float) -> float:
    """Sample a non-collinear middle y-value within the visible grid."""

    secant_mid = 0.5 * (float(y0) + float(y1))
    candidates = [
        float(secant_mid + offset)
        for offset in (-2.0, -1.5, -1.0, 1.0, 1.5, 2.0)
        if -4.0 <= float(secant_mid + offset) <= 4.0
    ]
    if not candidates:
        candidates = [float(secant_mid)]
    return float(rng.choice(candidates))


def _sample_outer_y(rng, *, anchor_y: float) -> float:
    """Sample one outer function endpoint without leaving the graph window."""

    candidates = [float(value) for value in range(-4, 5) if abs(float(value) - float(anchor_y)) >= 1.0]
    if not candidates:
        candidates = [float(anchor_y)]
    return float(rng.choice(candidates))


def _sample_rate_scene(rng, query: _ResolvedQuery) -> _SampledRateScene:
    """Sample a piecewise-linear function with two marked endpoints A and B."""

    delta_x = 4
    x0 = float(rng.choice((-4, -2, 0)))
    x1 = float(x0 + delta_x)
    y0, y1 = _sample_endpoint_y(rng, target_rate=float(query.target_rate), delta_x=int(delta_x))
    x_mid = float(x0 + (0.5 * delta_x))
    y_mid = _sample_midpoint_y(rng, y0=float(y0), y1=float(y1))
    x_left = float(x0 - 4.0)
    x_right = float(x1 + 4.0)
    y_left = _sample_outer_y(rng, anchor_y=float(y0))
    y_right = _sample_outer_y(rng, anchor_y=float(y1))
    point_a = (float(x0), float(y0))
    point_b = (float(x1), float(y1))
    polyline = (
        (float(x_left), float(y_left)),
        point_a,
        (float(x_mid), float(y_mid)),
        point_b,
        (float(x_right), float(y_right)),
    )
    answer_value = round((float(y1) - float(y0)) / (float(x1) - float(x0)), 1)
    scene_entities = [
        {
            "entity_id": "function_graph",
            "entity_type": "function_graph",
            "draw_kind": "piecewise_linear",
            "polyline_graph": [[float(x), float(y)] for x, y in polyline],
        },
        {
            "entity_id": "marked_point_A",
            "entity_type": "marked_graph_point",
            "label": "A",
            "graph_point": [float(point_a[0]), float(point_a[1])],
        },
        {
            "entity_id": "marked_point_B",
            "entity_type": "marked_graph_point",
            "label": "B",
            "graph_point": [float(point_b[0]), float(point_b[1])],
        },
    ]
    render_map = {
        "marked_points_graph": {
            "A": [float(point_a[0]), float(point_a[1])],
            "B": [float(point_b[0]), float(point_b[1])],
        },
        "secant_segment_graph": [[float(point_a[0]), float(point_a[1])], [float(point_b[0]), float(point_b[1])]],
    }
    execution_trace = {
        "question_format": "average_rate_between_marked_points",
        "point_a_graph": [float(point_a[0]), float(point_a[1])],
        "point_b_graph": [float(point_b[0]), float(point_b[1])],
        "delta_x": float(x1 - x0),
        "delta_y": float(y1 - y0),
        "average_rate": float(answer_value),
        "average_rate_formula": "(y_B - y_A) / (x_B - x_A)",
    }
    return _SampledRateScene(
        polyline_graph=tuple(polyline),
        point_a=point_a,
        point_b=point_b,
        answer_value=float(answer_value),
        scene_entities=list(scene_entities),
        render_map=dict(render_map),
        execution_trace=dict(execution_trace),
    )


def _pixel_point(point: GraphPoint, *, context: GraphSceneContext) -> Tuple[float, float]:
    """Project one graph coordinate into canonical pixel coordinates."""

    return graph_units_to_pixel_float(
        point,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
    )


def _draw_marked_point(
    draw: ImageDraw.ImageDraw,
    *,
    canonical_point: Tuple[float, float],
    label: str,
    label_direction: int,
    context: GraphSceneContext,
    marker_radius: int,
    label_font_size_px: int,
    marker_color: Sequence[int],
    label_color: Sequence[int],
    label_stroke_color: Sequence[int],
) -> list[float]:
    """Draw a marked endpoint and return the rendered label bbox."""

    scale = max(1, int(context.scene_scale))
    render_point = (float(canonical_point[0]) * float(scale), float(canonical_point[1]) * float(scale))
    radius = int(max(3, int(marker_radius))) * int(scale)
    draw.ellipse(
        (
            float(render_point[0] - radius),
            float(render_point[1] - radius),
            float(render_point[0] + radius),
            float(render_point[1] + radius),
        ),
        fill=tuple(int(value) for value in marker_color),
        outline=tuple(int(value) for value in label_stroke_color),
        width=max(1, int(2 * scale)),
    )
    offset_x = float(int(label_direction) * 18 * scale)
    offset_y = float(-18 * scale)
    font = load_font(int(label_font_size_px), bold=True)
    return draw_centered_text(
        draw,
        text=str(label),
        center=(float(render_point[0] + offset_x), float(render_point[1] + offset_y)),
        font=font,
        fill=tuple(int(value) for value in label_color),
        stroke_fill=tuple(int(value) for value in label_stroke_color),
        stroke_width=max(1, int(scale)),
    )


def _render_scene(
    draw: ImageDraw.ImageDraw,
    *,
    context: GraphSceneContext,
    sampled_scene: _SampledRateScene,
    shape_style,
    line_width: int,
    guide_line_width: int,
    marker_radius: int,
    label_font_size_px: int,
) -> _RenderedRateScene:
    """Render the plotted function, marked endpoints, and annotation payload."""

    render_polyline = draw_function_polyline(
        draw,
        polyline_graph=sampled_scene.polyline_graph,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
        scene_scale=int(context.scene_scale),
        line_width=int(line_width),
        line_color=shape_style.line_color,
    )
    point_a_pixel = _pixel_point(sampled_scene.point_a, context=context)
    point_b_pixel = _pixel_point(sampled_scene.point_b, context=context)
    secant_color = build_query_line_color(
        line_color=shape_style.line_color,
        label_color=shape_style.label_color,
    )
    scale = max(1, int(context.scene_scale))
    draw_dashed_line(
        draw,
        start=(float(point_a_pixel[0]) * float(scale), float(point_a_pixel[1]) * float(scale)),
        end=(float(point_b_pixel[0]) * float(scale), float(point_b_pixel[1]) * float(scale)),
        fill=secant_color,
        width=max(1, int(guide_line_width)),
        dash_px=12.0 * float(scale),
        gap_px=7.0 * float(scale),
    )
    label_bbox_a = _draw_marked_point(
        draw,
        canonical_point=point_a_pixel,
        label="A",
        label_direction=-1,
        context=context,
        marker_radius=int(marker_radius),
        label_font_size_px=int(label_font_size_px),
        marker_color=shape_style.line_color,
        label_color=shape_style.label_color,
        label_stroke_color=shape_style.label_stroke_color,
    )
    label_bbox_b = _draw_marked_point(
        draw,
        canonical_point=point_b_pixel,
        label="B",
        label_direction=1,
        context=context,
        marker_radius=int(marker_radius),
        label_font_size_px=int(label_font_size_px),
        marker_color=shape_style.line_color,
        label_color=shape_style.label_color,
        label_stroke_color=shape_style.label_stroke_color,
    )

    render_map = dict(sampled_scene.render_map)
    render_map.update(
        {
            "function_polyline_pixel": [
                [round(float(_pixel_point(point, context=context)[0]), 3), round(float(_pixel_point(point, context=context)[1]), 3)]
                for point in sampled_scene.polyline_graph
            ],
            "function_polyline_render": [
                [round(float(point[0]), 3), round(float(point[1]), 3)]
                for point in render_polyline
            ],
            "marked_points_pixel": {
                "A": [round(float(point_a_pixel[0]), 3), round(float(point_a_pixel[1]), 3)],
                "B": [round(float(point_b_pixel[0]), 3), round(float(point_b_pixel[1]), 3)],
            },
            "marked_point_label_bboxes": {
                "A": [round(float(value) / float(scale), 3) for value in label_bbox_a],
                "B": [round(float(value) / float(scale), 3) for value in label_bbox_b],
            },
            "secant_segment_pixel": [
                [round(float(point_a_pixel[0]), 3), round(float(point_a_pixel[1]), 3)],
                [round(float(point_b_pixel[0]), 3), round(float(point_b_pixel[1]), 3)],
            ],
        }
    )
    points_by_label = {
        "A": point_a_pixel,
        "B": point_b_pixel,
    }
    annotation = graph_point_set_annotation_artifacts(
        points_by_label=points_by_label,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
        witness_type="marked_average_rate_points",
        ordered_labels=("A", "B"),
    )
    witness_symbolic = dict(annotation["witness_symbolic"])
    witness_symbolic.update(
        {
            "type": "marked_average_rate_points",
            "point_a_graph": [float(sampled_scene.point_a[0]), float(sampled_scene.point_a[1])],
            "point_b_graph": [float(sampled_scene.point_b[0]), float(sampled_scene.point_b[1])],
            "average_rate": float(sampled_scene.answer_value),
        }
    )
    return _RenderedRateScene(
        answer_value=float(sampled_scene.answer_value),
        annotation_type=str(annotation["annotation_type"]),
        annotation_value=[list(point) for point in annotation["annotation_value"]],
        projected_annotation=dict(annotation["projected_annotation"]),
        witness_symbolic=dict(witness_symbolic),
        required_annotation_labels=list(annotation["required_labels"]),
        scene_entities=list(sampled_scene.scene_entities),
        render_map=dict(render_map),
        execution_trace=dict(sampled_scene.execution_trace),
    )


def _build_complexity(*, target_rate: float, annotation_count: int) -> Any:
    """Build normalized complexity metadata for the average-rate task."""

    weights = resolve_geometry_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": 0.42,
            "graphing_reasoning": clamp_unit_interval(0.64 + (0.10 * normalize_linear(abs(float(target_rate)), min_value=0.5, max_value=2.0))),
            "ambiguity": 0.46,
            "output_burden": normalize_linear(float(annotation_count), min_value=0.0, max_value=6.0),
        },
    )


class GeometryGraphingAverageRateValueBaseTask:
    """Compute average rate of change between two marked points on a function graph."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "graphing"
    scene_id = "function_graph"
    public_scene_id = "function_graph"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_average_rate",
                "answer_hint_number_one_decimal",
                "annotation_hint_average_rate_points",
            ),
            context=f"prompt defaults for {self.task_id}",
        )

        scene_context = resolve_graph_scene_context(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_canvas_min=_DEFAULTS.canvas_size_min,
            fallback_canvas_max=_DEFAULTS.canvas_size_max,
            fallback_cells_min=_DEFAULTS.graph_cells_min,
            fallback_cells_max=_DEFAULTS.graph_cells_max,
            require_graph_paper_background=True,
            graph_style_overrides={
                "origin_fraction_x": 0.5,
                "origin_fraction_y": 0.5,
                "axis_scale_label_max_abs": 8,
                "origin_label_enabled": False,
            },
        )
        image, draw, background_meta = make_graph_scene_canvas(
            instance_seed=int(instance_seed),
            context=scene_context,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            require_graph_paper=True,
        )
        line_width = int(
            params.get("line_width", group_default(_RENDER_DEFAULTS, "line_width", _DEFAULTS.line_width))
        ) * int(scene_context.scene_scale)
        guide_line_width = int(
            params.get("guide_line_width", group_default(_RENDER_DEFAULTS, "guide_line_width", _DEFAULTS.guide_line_width))
        ) * int(scene_context.scene_scale)
        marker_radius = int(
            params.get("marker_radius", group_default(_RENDER_DEFAULTS, "marker_radius", _DEFAULTS.marker_radius))
        )
        label_font_size_px = int(
            params.get(
                "label_font_size_px",
                resolve_scene_label_font_size_px(
                    canvas_size=int(scene_context.canvas_size),
                    graph_spacing=int(scene_context.graph_spacing),
                    scene_scale=int(scene_context.scene_scale),
                    min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                    max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
                ),
            )
        )
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )
        sampled_scene = _sample_rate_scene(rng, query)
        rendered_scene = _render_scene(
            draw,
            context=scene_context,
            sampled_scene=sampled_scene,
            shape_style=shape_style,
            line_width=int(line_width),
            guide_line_width=int(guide_line_width),
            marker_radius=int(marker_radius),
            label_font_size_px=int(label_font_size_px),
        )
        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=scene_context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=rendered_scene.annotation_value,
            answer_type="number",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_average_rate"]),
                "point_label_start": "A",
                "point_label_end": "B",
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_average_rate_points"]),
                "answer_hint": str(prompt_defaults["answer_hint_number_one_decimal"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="number", value=float(round(rendered_scene.answer_value, 1)))
        annotation_gt = TypedValue(type=str(rendered_scene.annotation_type), value=list(rendered_scene.annotation_value))
        query_params = {
            "query_id": str(query.query_id),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "target_rate": float(query.target_rate),
            "target_rate_probabilities": dict(query.target_rate_probabilities),
        }
        execution_trace = {
            "query_id": str(query.query_id),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "target_rate": float(query.target_rate),
            "target_rate_probabilities": dict(query.target_rate_probabilities),
            "answer_type": "number",
            "answer_value": float(answer_gt.value),
            "required_annotation_labels": list(rendered_scene.required_annotation_labels),
            **dict(rendered_scene.execution_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_graphing_average_rate",
                "entities": list(rendered_scene.scene_entities),
                "relations": {
                    "query_id": str(query.query_id),
                    "target_rate": float(query.target_rate),
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(scene_context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "graph_coordinate_frame": dict(scene_context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(scene_context.graph_frame),
                **dict(scene_context.graph_layout_metadata),
                "scene_variant": "piecewise_linear",
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": dict(execution_trace),
            "witness_symbolic": dict(rendered_scene.witness_symbolic),
            "projected_annotation": dict(rendered_scene.projected_annotation),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(
                target_rate=float(query.target_rate),
                annotation_count=len(rendered_scene.annotation_value),
            ),
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryGraphingAverageRateValueTask(FixedGeometryQueryTaskMixin, GeometryGraphingAverageRateValueBaseTask):
    """Public average-rate task over the function-graph scene."""

    task_id = TASK_ID
    fixed_query_id = AVERAGE_RATE_BETWEEN_MARKED_POINTS
    public_scene_id = "function_graph"
