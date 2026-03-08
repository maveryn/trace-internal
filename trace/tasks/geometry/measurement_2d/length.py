"""Single-object geometry length measurement task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.conic_geometry import (
    CircleInstance,
    EllipseInstance,
    center_point_evidence_artifacts,
    circle_scene_entity,
    draw_circle_outline,
    draw_ellipse_outline,
    ellipse_axis_pairs,
    ellipse_scene_entity,
    feasible_circle_radii_on_graph_paper,
    feasible_ellipse_axis_pairs_on_graph_paper,
    sample_circle_instance_on_graph_paper,
    sample_ellipse_instance_on_graph_paper,
)
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.length_geometry import (
    draw_labeled_segment,
    sample_segment_instance_on_graph_paper,
    segment_length_units,
    segment_render_anchor,
    segment_scene_entity,
    two_point_evidence_artifacts,
)
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.polygon_geometry import (
    alphabetic_labels,
    draw_polygon_labels,
    draw_polygon_outline,
    polygon_render_anchor,
    polygon_scene_entity,
    sample_polygon_instance_on_graph_paper,
)
from ..shared.shape_style import sample_geometry_shape_style
from ..shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import MEASUREMENT_SHARED_DEFAULTS
from .variant_sampling import apply_balanced_variant_sampling, resolve_shape_variant

_QUERY_TYPE = "measure"
_POLYGON_VARIANT_TO_SIDES: Dict[str, int] = {
    "triangle": 3,
    "quadrilateral": 4,
    "pentagon": 5,
}
_POLYGON_VARIANTS = set(_POLYGON_VARIANT_TO_SIDES)
_CIRCLE_VARIANTS = {"circle_radius", "circle_diameter"}
_ELLIPSE_VARIANTS = {"ellipse_major_axis", "ellipse_minor_axis"}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for geometry length measurement."""

    canvas_size_min: int = MEASUREMENT_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = MEASUREMENT_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = MEASUREMENT_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = MEASUREMENT_SHARED_DEFAULTS.graph_cells_max
    line_width: int = MEASUREMENT_SHARED_DEFAULTS.line_width
    label_offset_px: float = MEASUREMENT_SHARED_DEFAULTS.label_offset_px
    label_font_size_min: int = MEASUREMENT_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = MEASUREMENT_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = MEASUREMENT_SHARED_DEFAULTS.label_stroke_width
    answer_min: int = 2
    answer_max: int = 8
    segment_length_min: int = 2
    segment_length_max: int = 8
    segment_vector_max_abs_component: int = 12
    polygon_allowed_sides: Tuple[int, ...] = MEASUREMENT_SHARED_DEFAULTS.polygon_allowed_sides
    circle_radius_min: int = 1
    circle_radius_max: int = 4
    ellipse_axis_min: int = 1
    ellipse_axis_max: int = 4
    ellipse_allow_circle: bool = False


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "measurement_2d")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_measurement_2d_length",
)


def _required_prompt_text(prompt_defaults: Mapping[str, Any], *, preferred_keys: Sequence[str], context: str) -> str:
    """Return first available non-empty prompt text among ordered key candidates."""
    for key in preferred_keys:
        if str(key) in prompt_defaults:
            return str(required_group_default(prompt_defaults, str(key), context=context))
    raise ValueError(f"missing required prompt key in {context}: one of {list(preferred_keys)}")


def _resolve_supported_polygon_sides(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any]) -> List[int]:
    """Resolve allowed polygon side counts for polygon-length variants."""
    raw = params.get(
        "polygon_allowed_sides",
        group_default(gen_defaults, "polygon_allowed_sides", list(_DEFAULTS.polygon_allowed_sides)),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("polygon_allowed_sides must be a sequence of ints")
    out = sorted({int(item) for item in raw if int(item) in {3, 4, 5}})
    if not out:
        raise ValueError("polygon_allowed_sides must include at least one of [3, 4, 5]")
    return [int(item) for item in out]


def _supported_variants_for_allowed_sides(allowed_polygon_sides: Sequence[int]) -> List[str]:
    """Return ordered supported variants for configured polygon sides."""
    variants = ["segment"]
    for variant, sides in _POLYGON_VARIANT_TO_SIDES.items():
        if int(sides) in {int(item) for item in allowed_polygon_sides}:
            variants.append(str(variant))
    variants.extend(["circle_radius", "circle_diameter", "ellipse_major_axis", "ellipse_minor_axis"])
    return variants


def _answer_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
) -> Tuple[int, int]:
    """Resolve integer answer bounds for length variants."""
    answer_min, answer_max = resolve_optional_int_bounds(
        params,
        gen_defaults,
        min_key="answer_min",
        max_key="answer_max",
        context="generation defaults for task_geometry_measurement_2d_length",
    )
    resolved_min = int(_DEFAULTS.answer_min if answer_min is None else answer_min)
    resolved_max = int(_DEFAULTS.answer_max if answer_max is None else answer_max)
    if int(resolved_min) > int(resolved_max):
        raise ValueError("answer_min must be <= answer_max")
    return int(resolved_min), int(resolved_max)


def _circle_radii_for_variant(
    *,
    variant_kind: str,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> List[int]:
    """Return feasible circle radii for one circle-length variant."""
    radius_min = int(group_default(gen_defaults, "circle_radius_min", _DEFAULTS.circle_radius_min))
    radius_max = int(group_default(gen_defaults, "circle_radius_max", _DEFAULTS.circle_radius_max))
    lo = max(1, int(radius_min))
    hi = max(int(lo), int(radius_max))
    out: List[int] = []
    for radius in range(int(lo), int(hi) + 1):
        value = int(radius) if str(variant_kind) == "circle_radius" else int(2 * int(radius))
        if int(value) < int(answer_min) or int(value) > int(answer_max):
            continue
        out.append(int(radius))
    return out


def _ellipse_pairs_for_variant(
    *,
    variant_kind: str,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> List[Tuple[int, int]]:
    """Return feasible ellipse semiaxis pairs for one ellipse-length variant."""
    axis_min = int(group_default(gen_defaults, "ellipse_axis_min", _DEFAULTS.ellipse_axis_min))
    axis_max = int(group_default(gen_defaults, "ellipse_axis_max", _DEFAULTS.ellipse_axis_max))
    allow_circle = bool(group_default(gen_defaults, "ellipse_allow_circle", _DEFAULTS.ellipse_allow_circle))
    candidates = ellipse_axis_pairs(
        axis_min=int(axis_min),
        axis_max=int(axis_max),
        coefficient_min=None,
        coefficient_max=None,
        allow_circle=bool(allow_circle),
    )
    out: List[Tuple[int, int]] = []
    for semi_x, semi_y in candidates:
        major = int(2 * max(int(semi_x), int(semi_y)))
        minor = int(2 * min(int(semi_x), int(semi_y)))
        value = int(major if str(variant_kind) == "ellipse_major_axis" else minor)
        if int(value) < int(answer_min) or int(value) > int(answer_max):
            continue
        out.append((int(semi_x), int(semi_y)))
    return out


def _resolve_required_graph_cells(
    *,
    variant_kind: str,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> int:
    """Return minimum graph-cell count required by one selected variant and bounds."""
    variant = str(variant_kind)
    if variant == "segment":
        segment_min = int(group_default(gen_defaults, "segment_length_min", _DEFAULTS.segment_length_min))
        feasible_min = max(int(segment_min), int(answer_min))
        if int(feasible_min) > int(answer_max):
            raise ValueError("no feasible segment lengths for requested answer bounds")
        return int((2 * int(feasible_min)) + 2)
    if variant in _CIRCLE_VARIANTS:
        radii = _circle_radii_for_variant(
            variant_kind=str(variant),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
        if not radii:
            raise ValueError("no feasible circle radii for requested answer bounds")
        return int((2 * min(int(radius) for radius in radii)) + 2)
    if variant in _ELLIPSE_VARIANTS:
        pairs = _ellipse_pairs_for_variant(
            variant_kind=str(variant),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
        if not pairs:
            raise ValueError("no feasible ellipse semiaxis pairs for requested answer bounds")
        min_extent = min(max(int(semi_x), int(semi_y)) for semi_x, semi_y in pairs)
        return int((2 * int(min_extent)) + 2)
    return 0


def _prompt_family_for_variant(variant_kind: str) -> str:
    """Return prompt-family suffix for one length variant."""
    variant = str(variant_kind)
    if variant in _POLYGON_VARIANTS:
        return "polygon"
    if variant in _CIRCLE_VARIANTS:
        return "circle"
    if variant in _ELLIPSE_VARIANTS:
        return "ellipse"
    return "segment"


def _question_key_candidates_for_variant(variant_kind: str) -> Tuple[str, ...]:
    """Return ordered prompt question-key candidates for one length variant."""
    variant = str(variant_kind)
    if variant == "segment":
        return ("question_template_segment", "question_text_segment", "question_text")
    if variant in _POLYGON_VARIANTS:
        return ("question_template_polygon_side", "question_text_polygon_side", "question_text_polygon", "question_text")
    if variant == "circle_radius":
        return ("question_text_circle_radius", "question_text_circle", "question_text")
    if variant == "circle_diameter":
        return ("question_text_circle_diameter", "question_text_circle", "question_text")
    if variant == "ellipse_major_axis":
        return ("question_text_ellipse_major_axis", "question_text_ellipse", "question_text")
    if variant == "ellipse_minor_axis":
        return ("question_text_ellipse_minor_axis", "question_text_ellipse", "question_text")
    return ("question_text",)


def _evidence_hint_key_candidates_for_variant(variant_kind: str) -> Tuple[str, ...]:
    """Return ordered evidence-hint key candidates for one length variant."""
    if str(variant_kind) in _CIRCLE_VARIANTS:
        return ("evidence_hint_center", "evidence_hint")
    return ("evidence_hint_endpoints", "evidence_hint")


def _json_example_key_candidates_for_variant(variant_kind: str) -> Tuple[str, ...]:
    """Return ordered JSON-example key candidates for one length variant."""
    if str(variant_kind) in _CIRCLE_VARIANTS:
        return ("json_example_center_integer", "json_example_integer", "json_example")
    return ("json_example_integer", "json_example")


def _format_question(template: str, *, label_a: str | None = None, label_b: str | None = None) -> str:
    """Format one question template with optional side/segment labels."""
    slot_values = {
        "label_a": ("" if label_a is None else str(label_a)),
        "label_b": ("" if label_b is None else str(label_b)),
    }
    try:
        return str(template).format_map(slot_values)
    except KeyError as exc:  # pragma: no cover - fail-fast defensive path
        raise ValueError(f"unsupported question placeholder in template: {exc}") from exc


def _segment_anchor(point_a: Sequence[float], point_b: Sequence[float]) -> Dict[str, Any]:
    """Build deterministic render anchor for a measured segment."""
    return {
        "point": [float(point_a[0]), float(point_a[1])],
        "polyline": [[float(point_a[0]), float(point_a[1])], [float(point_b[0]), float(point_b[1])]],
        "coord_space": "pixel",
    }


def _graph_segment_length_units(point_a: Sequence[float], point_b: Sequence[float], *, spacing: int) -> int:
    """Return integer segment length in graph units for two pixel-space points."""
    spacing_px = max(1, int(spacing))
    unit_a = (float(point_a[0]) / float(spacing_px), float(point_a[1]) / float(spacing_px))
    unit_b = (float(point_b[0]) / float(spacing_px), float(point_b[1]) / float(spacing_px))
    return int(segment_length_units(unit_a, unit_b))


def _graph_draw_bounds(*, canvas_size: int, graph_frame: Mapping[str, Any]) -> Tuple[float, float, float, float]:
    """Return drawable graph-paper bounds as `[left, top, right, bottom]` in pixels."""
    margin = max(0, int(graph_frame.get("outer_margin_px", 0)))
    size = int(canvas_size)
    left = float(margin)
    top = float(margin)
    right = float(max(int(margin), int(size) - 1 - int(margin)))
    bottom = float(max(int(margin), int(size) - 1 - int(margin)))
    return (left, top, right, bottom)


def _point_inside_bounds(point: Sequence[float], *, bounds: Sequence[float]) -> bool:
    """Return true when one pixel point lies inside inclusive bounds."""
    left, top, right, bottom = [float(value) for value in bounds]
    x_value = float(point[0])
    y_value = float(point[1])
    return left <= x_value <= right and top <= y_value <= bottom


def _all_points_inside_bounds(points: Sequence[Sequence[float]], *, bounds: Sequence[float]) -> bool:
    """Return true when every point lies inside inclusive bounds."""
    return all(_point_inside_bounds(point, bounds=bounds) for point in points)


@register_task
class GeometryLengthMeasure2DTask:
    """Measure one integer length from a single geometry object on graph paper."""

    task_id = "task_geometry_measurement_2d_length"
    domain = "geometry"
    task_group = "measurement_2d"
    scene_kind = "geometry_2d_length_measurement"
    query_template_id = "geometry_2d_length_measure_v1"

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None) -> List[str]:
        """Return query types supported by this task."""
        return [_QUERY_TYPE]

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic length-measurement instance."""
        query_type = str(params.get("query_type", _QUERY_TYPE))
        if query_type != _QUERY_TYPE:
            raise ValueError(f"unsupported query_type: {query_type}")

        scene_rng = spawn_rng(instance_seed, "scene")
        allowed_polygon_sides = _resolve_supported_polygon_sides(params, gen_defaults=_GEN_DEFAULTS)
        supported_variants = _supported_variants_for_allowed_sides(allowed_polygon_sides)
        selected_variant, variant_probabilities = resolve_shape_variant(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_variants=supported_variants,
        )
        variant_kind = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected_variant),
            variant_probabilities=variant_probabilities,
            supported_variants=supported_variants,
        )
        answer_min, answer_max = _answer_bounds(params, gen_defaults=_GEN_DEFAULTS)
        required_graph_cells = _resolve_required_graph_cells(
            variant_kind=str(variant_kind),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=_GEN_DEFAULTS,
        )

        context_params = dict(params)
        if int(required_graph_cells) > 0:
            if "graph_cells" in context_params:
                if int(context_params.get("graph_cells", 0)) < int(required_graph_cells):
                    raise ValueError("graph_cells is too small for selected shape variant and answer bounds")
            else:
                current_min_cells = int(
                    context_params.get(
                        "graph_cells_min",
                        group_default(_RENDER_DEFAULTS, "graph_cells_min", _DEFAULTS.graph_cells_min),
                    )
                )
                current_max_cells = int(
                    context_params.get(
                        "graph_cells_max",
                        group_default(_RENDER_DEFAULTS, "graph_cells_max", _DEFAULTS.graph_cells_max),
                    )
                )
                resolved_min_cells = max(int(current_min_cells), int(required_graph_cells))
                resolved_max_cells = max(int(current_max_cells), int(resolved_min_cells))
                context_params["graph_cells_min"] = int(resolved_min_cells)
                context_params["graph_cells_max"] = int(resolved_max_cells)

        context = resolve_graph_scene_context(
            scene_rng,
            params=context_params,
            render_defaults=_RENDER_DEFAULTS,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_canvas_min=_DEFAULTS.canvas_size_min,
            fallback_canvas_max=_DEFAULTS.canvas_size_max,
            fallback_cells_min=_DEFAULTS.graph_cells_min,
            fallback_cells_max=_DEFAULTS.graph_cells_max,
        )
        line_width = int(params.get("line_width", group_default(_RENDER_DEFAULTS, "line_width", _DEFAULTS.line_width)))
        label_offset_px = float(
            params.get("label_offset_px", group_default(_RENDER_DEFAULTS, "label_offset_px", _DEFAULTS.label_offset_px))
        )
        label_font_size_px = resolve_scene_label_font_size_px(
            canvas_size=int(context.canvas_size),
            graph_spacing=int(context.graph_spacing),
            scene_scale=int(context.scene_scale),
            min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
            max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
        )
        label_stroke_width = int(
            params.get(
                "label_stroke_width",
                group_default(_RENDER_DEFAULTS, "label_stroke_width", _DEFAULTS.label_stroke_width),
            )
        )

        shape_style = sample_geometry_shape_style(scene_rng, params=context_params, render_defaults=_RENDER_DEFAULTS)
        image, draw, background_meta = make_graph_scene_canvas(
            instance_seed=int(instance_seed),
            context=context,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        graph_bounds = _graph_draw_bounds(
            canvas_size=int(context.canvas_size),
            graph_frame=context.graph_frame,
        )

        entity: Dict[str, Any] | None = None
        anchor: Dict[str, Any] | None = None
        evidence: Dict[str, Any] | None = None
        answer_scalar: int | None = None
        object_description: str | None = None
        question_text: str | None = None
        polygon_sides: int | None = None
        variant_detail: Dict[str, Any] = {}
        last_error: Exception | None = None

        for _ in range(max(1, int(max_attempts))):
            try:
                if str(variant_kind) == "segment":
                    segment_min = int(group_default(_GEN_DEFAULTS, "segment_length_min", _DEFAULTS.segment_length_min))
                    segment_max = int(group_default(_GEN_DEFAULTS, "segment_length_max", _DEFAULTS.segment_length_max))
                    labels = alphabetic_labels(2, start_index=int(scene_rng.randrange(26)))
                    candidate = sample_segment_instance_on_graph_paper(
                        scene_rng,
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        min_length_units=max(int(segment_min), int(answer_min)),
                        max_length_units=min(int(segment_max), int(answer_max)),
                        max_abs_vector_component=int(
                            group_default(
                                _GEN_DEFAULTS,
                                "segment_vector_max_abs_component",
                                _DEFAULTS.segment_vector_max_abs_component,
                            )
                        ),
                        labels=labels,
                        padding_units=0,
                        max_attempts=12,
                    )
                    if not _all_points_inside_bounds(
                        [candidate.endpoint_a, candidate.endpoint_b],
                        bounds=graph_bounds,
                    ):
                        continue
                    draw_labeled_segment(
                        draw,
                        endpoint_a=scale_point(candidate.endpoint_a, int(context.scene_scale)),
                        endpoint_b=scale_point(candidate.endpoint_b, int(context.scene_scale)),
                        labels=candidate.labels,
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        label_offset_px=float(label_offset_px) * float(context.scene_scale),
                        font_size_px=int(label_font_size_px),
                        text_stroke_width=max(1, int(label_stroke_width)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                        label_color=tuple(int(value) for value in shape_style.label_color),
                        label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
                        canvas_size=int(context.canvas_size) * int(context.scene_scale),
                    )
                    answer_scalar = int(candidate.length_units)
                    entity = segment_scene_entity(candidate, segment_kind="segment")
                    anchor = segment_render_anchor(candidate)
                    evidence = two_point_evidence_artifacts(
                        point_a=candidate.endpoint_a,
                        point_b=candidate.endpoint_b,
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        witness_type="segment_endpoints",
                        roles=("endpoint_a", "endpoint_b"),
                    )
                    object_description = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=("object_description_segment", "object_description"),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_template = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=_question_key_candidates_for_variant("segment"),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_text = _format_question(
                        question_template,
                        label_a=str(candidate.labels[0]),
                        label_b=str(candidate.labels[1]),
                    )
                    variant_detail = {"segment_labels": [str(candidate.labels[0]), str(candidate.labels[1])]}
                    break

                if str(variant_kind) in _POLYGON_VARIANTS:
                    polygon_sides = int(_POLYGON_VARIANT_TO_SIDES[str(variant_kind)])
                    polygon_instance = sample_polygon_instance_on_graph_paper(
                        scene_rng,
                        allowed_sides=[int(polygon_sides)],
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        padding_units=0,
                        max_attempts=12,
                        min_area_square_units=4,
                    )
                    side_idx = int(scene_rng.randrange(int(polygon_instance.sides)))
                    next_idx = int((int(side_idx) + 1) % int(polygon_instance.sides))
                    point_a = polygon_instance.vertices[int(side_idx)]
                    point_b = polygon_instance.vertices[int(next_idx)]
                    candidate_answer = _graph_segment_length_units(
                        point_a,
                        point_b,
                        spacing=int(context.graph_spacing),
                    )
                    if int(candidate_answer) < int(answer_min) or int(candidate_answer) > int(answer_max):
                        continue
                    if not _all_points_inside_bounds(
                        list(polygon_instance.vertices),
                        bounds=graph_bounds,
                    ):
                        continue
                    draw_polygon_outline(
                        draw,
                        vertices=[scale_point(point, int(context.scene_scale)) for point in polygon_instance.vertices],
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                    )
                    draw_polygon_labels(
                        draw,
                        vertices=[scale_point(point, int(context.scene_scale)) for point in polygon_instance.vertices],
                        labels=polygon_instance.labels,
                        label_offset_px=float(label_offset_px) * float(context.scene_scale),
                        font_size_px=int(label_font_size_px),
                        text_stroke_width=max(1, int(label_stroke_width)),
                        label_color=tuple(int(value) for value in shape_style.label_color),
                        label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
                        canvas_size=int(context.canvas_size) * int(context.scene_scale),
                    )
                    draw.line(
                        [scale_point(point_a, int(context.scene_scale)), scale_point(point_b, int(context.scene_scale))],
                        fill=tuple(int(value) for value in shape_style.line_color),
                        width=max(1, int(line_width + 1) * int(context.scene_scale)),
                    )
                    answer_scalar = int(candidate_answer)
                    entity = polygon_scene_entity(polygon_instance)
                    entity["attrs"]["target_side_indices"] = [int(side_idx), int(next_idx)]
                    entity["attrs"]["target_side_labels"] = [
                        str(polygon_instance.labels[int(side_idx)]),
                        str(polygon_instance.labels[int(next_idx)]),
                    ]
                    entity["attrs"]["target_side_length_units"] = int(candidate_answer)
                    anchor = polygon_render_anchor(polygon_instance)
                    evidence = two_point_evidence_artifacts(
                        point_a=(float(point_a[0]), float(point_a[1])),
                        point_b=(float(point_b[0]), float(point_b[1])),
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        witness_type="polygon_side_endpoints",
                        roles=("side_endpoint_a", "side_endpoint_b"),
                    )
                    object_description = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=("object_description_polygon", "object_description"),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_template = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=_question_key_candidates_for_variant(str(variant_kind)),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_text = _format_question(
                        question_template,
                        label_a=str(polygon_instance.labels[int(side_idx)]),
                        label_b=str(polygon_instance.labels[int(next_idx)]),
                    )
                    variant_detail = {
                        "target_side_indices": [int(side_idx), int(next_idx)],
                        "target_side_labels": [
                            str(polygon_instance.labels[int(side_idx)]),
                            str(polygon_instance.labels[int(next_idx)]),
                        ],
                    }
                    break

                if str(variant_kind) in _CIRCLE_VARIANTS:
                    radii = _circle_radii_for_variant(
                        variant_kind=str(variant_kind),
                        answer_min=int(answer_min),
                        answer_max=int(answer_max),
                        gen_defaults=_GEN_DEFAULTS,
                    )
                    feasible_radii = feasible_circle_radii_on_graph_paper(
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        radii=radii,
                        padding_units=0,
                    )
                    if not feasible_radii:
                        continue
                    circle_instance = sample_circle_instance_on_graph_paper(
                        scene_rng,
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        radii=feasible_radii,
                        padding_units=0,
                        max_attempts=12,
                    )
                    axis_kind = str(scene_rng.choice(["horizontal", "vertical"]))
                    sign = int(scene_rng.choice([-1, 1]))
                    cx, cy = float(circle_instance.center[0]), float(circle_instance.center[1])
                    radius_px = int(circle_instance.radius_units) * int(context.graph_spacing)
                    if str(variant_kind) == "circle_radius":
                        point_a = (float(cx), float(cy))
                        if axis_kind == "horizontal":
                            point_b = (float(cx + (float(sign) * float(radius_px))), float(cy))
                        else:
                            point_b = (float(cx), float(cy + (float(sign) * float(radius_px))))
                        candidate_answer = int(circle_instance.radius_units)
                    else:
                        if axis_kind == "horizontal":
                            point_a = (float(cx - float(radius_px)), float(cy))
                            point_b = (float(cx + float(radius_px)), float(cy))
                        else:
                            point_a = (float(cx), float(cy - float(radius_px)))
                            point_b = (float(cx), float(cy + float(radius_px)))
                        candidate_answer = int(2 * int(circle_instance.radius_units))
                    if not _all_points_inside_bounds(
                        [
                            point_a,
                            point_b,
                            (float(cx - float(radius_px)), float(cy)),
                            (float(cx + float(radius_px)), float(cy)),
                            (float(cx), float(cy - float(radius_px))),
                            (float(cx), float(cy + float(radius_px))),
                        ],
                        bounds=graph_bounds,
                    ):
                        continue
                    draw_circle_outline(
                        draw,
                        center=scale_point(circle_instance.center, int(context.scene_scale)),
                        radius_px=int(circle_instance.radius_units) * int(context.graph_spacing) * int(context.scene_scale),
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                    )
                    answer_scalar = int(candidate_answer)
                    entity = circle_scene_entity(circle_instance)
                    entity["attrs"]["measurement_kind"] = (
                        "radius" if str(variant_kind) == "circle_radius" else "diameter"
                    )
                    entity["attrs"]["measurement_axis"] = str(axis_kind)
                    entity["attrs"]["measurement_points"] = [
                        [float(point_a[0]), float(point_a[1])],
                        [float(point_b[0]), float(point_b[1])],
                    ]
                    anchor = _segment_anchor(point_a, point_b)
                    evidence = center_point_evidence_artifacts(
                        center=(float(circle_instance.center[0]), float(circle_instance.center[1])),
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        entity_id="circle_1",
                        witness_type="circle_center",
                    )
                    object_description = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=("object_description_circle", "object_description"),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_template = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=_question_key_candidates_for_variant(str(variant_kind)),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_text = _format_question(question_template)
                    variant_detail = {
                        "measurement_kind": str(entity["attrs"]["measurement_kind"]),
                        "measurement_axis": str(axis_kind),
                    }
                    break

                if str(variant_kind) in _ELLIPSE_VARIANTS:
                    pairs = _ellipse_pairs_for_variant(
                        variant_kind=str(variant_kind),
                        answer_min=int(answer_min),
                        answer_max=int(answer_max),
                        gen_defaults=_GEN_DEFAULTS,
                    )
                    feasible_pairs = feasible_ellipse_axis_pairs_on_graph_paper(
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        axis_pairs=pairs,
                        padding_units=0,
                    )
                    if not feasible_pairs:
                        continue
                    ellipse_instance = sample_ellipse_instance_on_graph_paper(
                        scene_rng,
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        axis_pairs=feasible_pairs,
                        padding_units=0,
                        max_attempts=12,
                    )
                    cx, cy = float(ellipse_instance.center[0]), float(ellipse_instance.center[1])
                    semi_x_px = int(ellipse_instance.semi_axis_x_units) * int(context.graph_spacing)
                    semi_y_px = int(ellipse_instance.semi_axis_y_units) * int(context.graph_spacing)
                    major_axis_kind = "horizontal" if int(ellipse_instance.semi_axis_x_units) >= int(ellipse_instance.semi_axis_y_units) else "vertical"
                    if str(variant_kind) == "ellipse_major_axis":
                        axis_kind = str(major_axis_kind)
                    else:
                        axis_kind = "vertical" if str(major_axis_kind) == "horizontal" else "horizontal"
                    if axis_kind == "horizontal":
                        half_axis_px = int(semi_x_px)
                        point_a = (float(cx - float(half_axis_px)), float(cy))
                        point_b = (float(cx + float(half_axis_px)), float(cy))
                    else:
                        half_axis_px = int(semi_y_px)
                        point_a = (float(cx), float(cy - float(half_axis_px)))
                        point_b = (float(cx), float(cy + float(half_axis_px)))
                    candidate_answer = int(2 * int(half_axis_px) / int(context.graph_spacing))
                    if int(candidate_answer) < int(answer_min) or int(candidate_answer) > int(answer_max):
                        continue
                    if not _all_points_inside_bounds(
                        [
                            point_a,
                            point_b,
                            (float(cx - float(semi_x_px)), float(cy)),
                            (float(cx + float(semi_x_px)), float(cy)),
                            (float(cx), float(cy - float(semi_y_px))),
                            (float(cx), float(cy + float(semi_y_px))),
                        ],
                        bounds=graph_bounds,
                    ):
                        continue
                    draw_ellipse_outline(
                        draw,
                        center=scale_point(ellipse_instance.center, int(context.scene_scale)),
                        semi_axis_x_px=int(ellipse_instance.semi_axis_x_units) * int(context.graph_spacing) * int(context.scene_scale),
                        semi_axis_y_px=int(ellipse_instance.semi_axis_y_units) * int(context.graph_spacing) * int(context.scene_scale),
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                    )
                    answer_scalar = int(candidate_answer)
                    entity = ellipse_scene_entity(ellipse_instance)
                    entity["attrs"]["measurement_kind"] = (
                        "major_axis" if str(variant_kind) == "ellipse_major_axis" else "minor_axis"
                    )
                    entity["attrs"]["measurement_axis"] = str(axis_kind)
                    entity["attrs"]["measurement_points"] = [
                        [float(point_a[0]), float(point_a[1])],
                        [float(point_b[0]), float(point_b[1])],
                    ]
                    anchor = _segment_anchor(point_a, point_b)
                    evidence = two_point_evidence_artifacts(
                        point_a=point_a,
                        point_b=point_b,
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        witness_type="ellipse_measure_segment",
                        roles=("endpoint_a", "endpoint_b"),
                    )
                    object_description = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=("object_description_ellipse", "object_description"),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_template = _required_prompt_text(
                        _PROMPT_DEFAULTS,
                        preferred_keys=_question_key_candidates_for_variant(str(variant_kind)),
                        context=f"prompt defaults for {self.task_id}",
                    )
                    question_text = _format_question(question_template)
                    variant_detail = {
                        "measurement_kind": str(entity["attrs"]["measurement_kind"]),
                        "measurement_axis": str(axis_kind),
                    }
                    break

                raise ValueError(f"unsupported shape variant: {variant_kind}")
            except Exception as exc:
                last_error = exc
                continue

        if (
            answer_scalar is None
            or entity is None
            or anchor is None
            or evidence is None
            or object_description is None
            or question_text is None
        ):
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_type_key",
                "json_output_contract",
                "json_output_contract_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_task_type_key = str(prompt_defaults["task_type_key"])
        evidence_hint = _required_prompt_text(
            _PROMPT_DEFAULTS,
            preferred_keys=_evidence_hint_key_candidates_for_variant(str(variant_kind)),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = _required_prompt_text(
            _PROMPT_DEFAULTS,
            preferred_keys=("answer_hint_integer", "answer_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example = _required_prompt_text(
            _PROMPT_DEFAULTS,
            preferred_keys=_json_example_key_candidates_for_variant(str(variant_kind)),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example_answer_only = _required_prompt_text(
            _PROMPT_DEFAULTS,
            preferred_keys=("json_example_answer_only_integer", "json_example_answer_only"),
            context=f"prompt defaults for {self.task_id}",
        )

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_type_key=prompt_task_type_key,
            query_type=_QUERY_TYPE,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        complexity_variant_weight = {
            "segment": 0.35,
            "triangle": 0.45,
            "quadrilateral": 0.55,
            "pentagon": 0.65,
            "circle_radius": 0.55,
            "circle_diameter": 0.58,
            "ellipse_major_axis": 0.64,
            "ellipse_minor_axis": 0.62,
        }
        complexity = TaskComplexity(
            complexity_score=max(
                0.0,
                min(
                    1.0,
                    0.24
                    + (0.44 * float(complexity_variant_weight.get(str(variant_kind), 0.5)))
                    + (0.32 * min(1.0, float(answer_scalar) / float(max(1, answer_max)))),
                ),
            ),
            complexity_components={
                "shape_variant": str(variant_kind),
                "answer_scalar": int(answer_scalar),
                "polygon_sides": (int(polygon_sides) if polygon_sides is not None else None),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": str(self.scene_kind),
                "entities": [dict(entity)],
                "relations": {},
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "query_type": _QUERY_TYPE,
                "template_id": str(self.query_template_id),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "shape_variant": str(variant_kind),
                    "supported_shape_variants": [str(item) for item in supported_variants],
                    "variant_probabilities": dict(variant_probabilities),
                    "answer_min": int(answer_min),
                    "answer_max": int(answer_max),
                    "required_graph_cells": int(required_graph_cells),
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "text_style": {
                    "font_size_px": int(label_font_size_px // max(1, int(context.scene_scale))),
                    "stroke_width_px": int(max(1, int(label_stroke_width))),
                },
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            },
            "render_map": {"image_id": "img0", "anchors": {"target_1": dict(anchor)}},
            "execution_trace": {
                "shape_variant": str(variant_kind),
                "answer_scalar": int(answer_scalar),
                "answer_format": "integer",
                "variant_probabilities": dict(variant_probabilities),
                "required_graph_cells": int(required_graph_cells),
                "question_text": str(question_text),
                **dict(variant_detail),
            },
            "witness_symbolic": dict(evidence["witness_symbolic"]),
            "projected_evidence": dict(evidence["projected_evidence"]),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_scalar)),
            evidence_gt=TypedValue(type=str(evidence["evidence_type"]), value=evidence["evidence_value"]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_type=_QUERY_TYPE,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
