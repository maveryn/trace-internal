"""Non-grid geometry counting task over multiple labeled triangles."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from ...base import TaskOutput
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_counting_complexity
from ..shared.graph_rendering import graph_units_to_pixel
from ..shared.multi_polygon_scene import PolygonSceneObject, draw_polygon_objects
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import COUNTING_SHARED_DEFAULTS
from .shared import (
    assign_counting_labels,
    bounds_from_points,
    bounds_have_clearance,
    resolve_counting_cardinality_pair,
)
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
_SUPPORTED_VARIANTS: Tuple[str, ...] = (
    "equilateral_triangle",
    "isosceles_triangle",
    "scalene_triangle",
    "right_triangle",
    "acute_triangle",
    "obtuse_triangle",
)

@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for triangle-counting generation."""
    canvas_size_min: int = COUNTING_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COUNTING_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = 24
    graph_cells_max: int = 32
    line_width: int = COUNTING_SHARED_DEFAULTS.line_width
    label_font_size_min: int = COUNTING_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COUNTING_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COUNTING_SHARED_DEFAULTS.label_stroke_width
    object_label_offset_px: float = 16.0
    object_count_min: int = 5
    object_count_max: int = 8
    min_side_units: float = 3.0
    max_side_units: float = 5.6
    right_angle_margin_degrees: float = 8.0
    min_obtuse_angle_degrees: float = 102.0
    max_acute_angle_degrees: float = 80.0
    min_side_gap_units: float = 0.8

@dataclass(frozen=True)
class _TrianglePrototype:
    """Centered local triangle geometry plus its classification metadata."""
    local_vertices: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]
    side_kind: str
    angle_kind: str
    angles_degrees: Tuple[float, float, float]
    side_lengths: Tuple[float, float, float]

@dataclass(frozen=True)
class _TriangleSceneObject:
    """One placed triangle object in the counting scene."""
    polygon: PolygonSceneObject
    side_kind: str
    angle_kind: str
    angles_degrees: Tuple[float, float, float]
    side_lengths: Tuple[float, float, float]

@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one multi-triangle counting instance."""
    query_id: str
    object_count: int
    target_count: int
    objects: Tuple[_TriangleSceneObject, ...]
    matching_labels: Tuple[str, ...]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]

_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="source_geometry_counting_triangle",
)
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="counting")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="counting")

def _triangle_slots_graph_units(*, object_count: int, graph_cells: int, rng) -> List[Tuple[int, int]]:
    """Return a roomy hidden-grid slot bank for up to 12 triangle objects."""
    half_span = max(16, int(graph_cells // 2))
    outer_x = max(8, min(int(round(float(half_span) * 0.78)), int(half_span - 4)))
    inner_x = max(4, min(int(round(float(half_span) * 0.28)), max(4, int(outer_x - 5))))
    row_y = max(7, min(int(round(float(half_span) * 0.48)), int(half_span - 4)))
    base_slots = [
        (-int(outer_x), int(row_y)),
        (-int(inner_x), int(row_y)),
        (int(inner_x), int(row_y)),
        (int(outer_x), int(row_y)),
        (-int(outer_x), 0),
        (-int(inner_x), 0),
        (int(inner_x), 0),
        (int(outer_x), 0),
        (-int(outer_x), -int(row_y)),
        (-int(inner_x), -int(row_y)),
        (int(inner_x), -int(row_y)),
        (int(outer_x), -int(row_y)),
    ]
    rng.shuffle(base_slots)
    return list(base_slots[: int(object_count)])

def _center_vertices(vertices: Sequence[Tuple[float, float]]) -> Tuple[Tuple[float, float], ...]:
    """Translate vertices so their centroid sits at the origin."""
    cx = sum(float(x) for x, _ in vertices) / float(len(vertices))
    cy = sum(float(y) for _, y in vertices) / float(len(vertices))
    return tuple((float(x) - float(cx), float(y) - float(cy)) for x, y in vertices)

def _side_lengths(vertices: Sequence[Tuple[float, float]]) -> Tuple[float, float, float]:
    """Return triangle side lengths opposite vertices A, B, C."""
    point_a, point_b, point_c = vertices
    side_a = math.hypot(float(point_b[0]) - float(point_c[0]), float(point_b[1]) - float(point_c[1]))
    side_b = math.hypot(float(point_a[0]) - float(point_c[0]), float(point_a[1]) - float(point_c[1]))
    side_c = math.hypot(float(point_a[0]) - float(point_b[0]), float(point_a[1]) - float(point_b[1]))
    return (float(side_a), float(side_b), float(side_c))

def _triangle_angles_degrees(vertices: Sequence[Tuple[float, float]]) -> Tuple[float, float, float]:
    """Return the three interior angles in degrees."""
    side_a, side_b, side_c = _side_lengths(vertices)
    def _angle(opposite: float, adjacent_a: float, adjacent_b: float) -> float:
        cosine = (
            (float(adjacent_a) * float(adjacent_a))
            + (float(adjacent_b) * float(adjacent_b))
            - (float(opposite) * float(opposite))
        ) / max(1e-9, 2.0 * float(adjacent_a) * float(adjacent_b))
        cosine = max(-1.0, min(1.0, float(cosine)))
        return math.degrees(math.acos(float(cosine)))
    angle_a = _angle(side_a, side_b, side_c)
    angle_b = _angle(side_b, side_a, side_c)
    angle_c = 180.0 - float(angle_a) - float(angle_b)
    return (float(angle_a), float(angle_b), float(angle_c))

def _classify_side_kind(side_lengths: Sequence[float], *, min_side_gap_units: float) -> str:
    """Return one side-based triangle class label."""
    lengths = [float(value) for value in side_lengths]
    pair_diffs = [
        abs(lengths[0] - lengths[1]),
        abs(lengths[0] - lengths[2]),
        abs(lengths[1] - lengths[2]),
    ]
    threshold = float(min_side_gap_units)
    if max(pair_diffs) <= 1e-6:
        return "equilateral"
    equal_pairs = sum(1 for diff in pair_diffs if diff <= 1e-6)
    if equal_pairs >= 1 and max(pair_diffs) >= float(threshold):
        return "isosceles"
    return "scalene"

def _classify_angle_kind(angles_degrees: Sequence[float], *, right_angle_margin_degrees: float) -> str:
    """Return one angle-based triangle class label."""
    max_angle = max(float(value) for value in angles_degrees)
    margin = float(right_angle_margin_degrees)
    if abs(float(max_angle) - 90.0) <= 1e-4:
        return "right"
    if float(max_angle) < 90.0 - float(margin):
        return "acute"
    if float(max_angle) > 90.0 + float(margin):
        return "obtuse"
    return "near_right"

def _build_triangle_prototype(
    vertices: Sequence[Tuple[float, float]],
    *,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
) -> _TrianglePrototype:
    """Compute canonical metadata for one centered triangle."""
    centered = _center_vertices(vertices)
    lengths = _side_lengths(centered)
    angles = _triangle_angles_degrees(centered)
    side_kind = _classify_side_kind(lengths, min_side_gap_units=float(min_side_gap_units))
    angle_kind = _classify_angle_kind(angles, right_angle_margin_degrees=float(right_angle_margin_degrees))
    return _TrianglePrototype(
        local_vertices=tuple(centered),  # type: ignore[arg-type]
        side_kind=str(side_kind),
        angle_kind=str(angle_kind),
        angles_degrees=tuple(float(value) for value in angles),
        side_lengths=tuple(float(value) for value in lengths),
    )

def _sample_equilateral_triangle(rng, *, min_side_units: float, max_side_units: float, **_kwargs: Any) -> _TrianglePrototype:
    """Return one equilateral triangle prototype."""
    side = float(rng.uniform(float(min_side_units), float(max_side_units)))
    height = float(side * math.sqrt(3.0) / 2.0)
    return _build_triangle_prototype(
        [(-0.5 * float(side), 0.0), (0.5 * float(side), 0.0), (0.0, float(height))],
        min_side_gap_units=0.0,
        right_angle_margin_degrees=1.0,
    )

def _sample_isosceles_triangle(
    rng,
    *,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    **_kwargs: Any,
) -> _TrianglePrototype:
    """Return one isosceles but non-equilateral triangle prototype."""
    for _ in range(400):
        base = float(rng.uniform(float(min_side_units), float(max_side_units)))
        height = float(rng.uniform(float(min_side_units) * 0.75, float(max_side_units) * 1.05))
        prototype = _build_triangle_prototype(
            [(-0.5 * float(base), 0.0), (0.5 * float(base), 0.0), (0.0, float(height))],
            min_side_gap_units=float(min_side_gap_units),
            right_angle_margin_degrees=float(right_angle_margin_degrees),
        )
        if str(prototype.side_kind) == "isosceles":
            return prototype
    raise ValueError("failed to sample isosceles triangle prototype")

def _sample_scalene_triangle(
    rng,
    *,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    **_kwargs: Any,
) -> _TrianglePrototype:
    """Return one clear scalene triangle prototype."""
    for _ in range(500):
        base = float(rng.uniform(float(min_side_units), float(max_side_units)))
        height = float(rng.uniform(float(min_side_units) * 0.75, float(max_side_units) * 1.05))
        apex_x = float(rng.uniform(-0.22 * float(base), 0.30 * float(base)))
        prototype = _build_triangle_prototype(
            [(-0.5 * float(base), 0.0), (0.5 * float(base), 0.0), (float(apex_x), float(height))],
            min_side_gap_units=float(min_side_gap_units),
            right_angle_margin_degrees=float(right_angle_margin_degrees),
        )
        if str(prototype.side_kind) == "scalene" and str(prototype.angle_kind) != "near_right":
            return prototype
    raise ValueError("failed to sample scalene triangle prototype")

def _sample_right_triangle(
    rng,
    *,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    **_kwargs: Any,
) -> _TrianglePrototype:
    """Return one right triangle prototype."""
    for _ in range(400):
        base = float(rng.uniform(float(min_side_units), float(max_side_units)))
        height = float(rng.uniform(float(min_side_units), float(max_side_units)))
        if abs(float(base) - float(height)) < float(min_side_gap_units):
            continue
        prototype = _build_triangle_prototype(
            [(0.0, 0.0), (float(base), 0.0), (0.0, float(height))],
            min_side_gap_units=float(min_side_gap_units),
            right_angle_margin_degrees=float(right_angle_margin_degrees),
        )
        if str(prototype.angle_kind) == "right":
            return prototype
    raise ValueError("failed to sample right triangle prototype")

def _sample_acute_triangle(
    rng,
    *,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    max_acute_angle_degrees: float,
    **_kwargs: Any,
) -> _TrianglePrototype:
    """Return one visibly acute triangle prototype."""
    for _ in range(600):
        base = float(rng.uniform(float(min_side_units), float(max_side_units)))
        apex_x = float(rng.uniform(-0.12 * float(base), 0.12 * float(base)))
        height = float(rng.uniform(0.95 * float(base), 1.28 * float(base)))
        prototype = _build_triangle_prototype(
            [(-0.5 * float(base), 0.0), (0.5 * float(base), 0.0), (float(apex_x), float(height))],
            min_side_gap_units=float(min_side_gap_units),
            right_angle_margin_degrees=float(right_angle_margin_degrees),
        )
        if str(prototype.angle_kind) == "acute" and max(float(value) for value in prototype.angles_degrees) <= float(max_acute_angle_degrees):
            return prototype
    raise ValueError("failed to sample acute triangle prototype")

def _sample_obtuse_triangle(
    rng,
    *,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    min_obtuse_angle_degrees: float,
    **_kwargs: Any,
) -> _TrianglePrototype:
    """Return one visibly obtuse triangle prototype."""
    for _ in range(600):
        base = float(rng.uniform(float(min_side_units), float(max_side_units)))
        height = float(rng.uniform(float(min_side_units) * 0.7, float(max_side_units)))
        apex_x = float(rng.uniform(0.58 * float(base), 0.95 * float(base)))
        prototype = _build_triangle_prototype(
            [(-0.5 * float(base), 0.0), (0.5 * float(base), 0.0), (float(apex_x), float(height))],
            min_side_gap_units=float(min_side_gap_units),
            right_angle_margin_degrees=float(right_angle_margin_degrees),
        )
        if str(prototype.angle_kind) == "obtuse" and max(float(value) for value in prototype.angles_degrees) >= float(min_obtuse_angle_degrees):
            return prototype
    raise ValueError("failed to sample obtuse triangle prototype")

_SAMPLERS = {
    "equilateral": _sample_equilateral_triangle,
    "isosceles": _sample_isosceles_triangle,
    "scalene": _sample_scalene_triangle,
    "right": _sample_right_triangle,
    "acute": _sample_acute_triangle,
    "obtuse": _sample_obtuse_triangle,
}

def _triangle_matches_variant(prototype: _TrianglePrototype, query_id: str) -> bool:
    """Return whether one prototype satisfies the requested counting predicate."""
    variant = str(query_id)
    if variant == "equilateral_triangle":
        return str(prototype.side_kind) == "equilateral"
    if variant == "isosceles_triangle":
        return str(prototype.side_kind) == "isosceles"
    if variant == "scalene_triangle":
        return str(prototype.side_kind) == "scalene"
    if variant == "right_triangle":
        return str(prototype.angle_kind) == "right"
    if variant == "acute_triangle":
        return str(prototype.angle_kind) == "acute"
    if variant == "obtuse_triangle":
        return str(prototype.angle_kind) == "obtuse"
    raise ValueError(f"unsupported query_id: {query_id}")

def _positive_sampler_names(query_id: str) -> Tuple[str, ...]:
    """Return likely-positive prototype sampler names for one variant."""
    mapping = {
        "equilateral_triangle": ("equilateral",),
        "isosceles_triangle": ("isosceles",),
        "scalene_triangle": ("scalene",),
        "right_triangle": ("right",),
        "acute_triangle": ("acute", "equilateral"),
        "obtuse_triangle": ("obtuse",),
    }
    return tuple(mapping[str(query_id)])

def _negative_sampler_names(query_id: str) -> Tuple[str, ...]:
    """Return likely-negative sampler names for one variant."""
    mapping = {
        "equilateral_triangle": ("isosceles", "scalene", "right", "obtuse"),
        "isosceles_triangle": ("equilateral", "scalene", "right", "obtuse", "acute"),
        "scalene_triangle": ("equilateral", "isosceles"),
        "right_triangle": ("acute", "obtuse", "equilateral", "isosceles", "scalene"),
        "acute_triangle": ("right", "obtuse"),
        "obtuse_triangle": ("acute", "right", "equilateral"),
    }
    return tuple(mapping[str(query_id)])

def _sample_triangle_for_match(
    rng,
    *,
    query_id: str,
    positive: bool,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    max_acute_angle_degrees: float,
    min_obtuse_angle_degrees: float,
) -> _TrianglePrototype:
    """Sample one triangle prototype that either matches or rejects the query class."""
    preferred = (
        _positive_sampler_names(str(query_id))
        if bool(positive)
        else _negative_sampler_names(str(query_id))
    )
    fallback = tuple(_SAMPLERS.keys())
    last_error: Exception | None = None
    for sampler_names in (preferred, fallback):
        for _ in range(700):
            sampler_name = str(rng.choice(list(sampler_names)))
            sampler = _SAMPLERS[str(sampler_name)]
            try:
                prototype = sampler(
                    rng,
                    min_side_units=float(min_side_units),
                    max_side_units=float(max_side_units),
                    min_side_gap_units=float(min_side_gap_units),
                    right_angle_margin_degrees=float(right_angle_margin_degrees),
                    max_acute_angle_degrees=float(max_acute_angle_degrees),
                    min_obtuse_angle_degrees=float(min_obtuse_angle_degrees),
                )
            except Exception as exc:
                last_error = exc
                continue
            if bool(_triangle_matches_variant(prototype, str(query_id))) == bool(positive):
                return prototype
    raise RuntimeError("failed to sample triangle prototype for counting scene") from last_error

def _variant_class_label(query_id: str) -> str:
    """Return a normalized human-readable triangle class label."""
    mapping = {
        "equilateral_triangle": "equilateral",
        "isosceles_triangle": "isosceles_but_not_equilateral",
        "scalene_triangle": "scalene",
        "right_triangle": "right",
        "acute_triangle": "acute",
        "obtuse_triangle": "obtuse",
    }
    return str(mapping[str(query_id)])

def _place_triangle_object(
    prototype: _TrianglePrototype,
    *,
    label: str,
    slot_units: Tuple[int, int],
    context: GraphSceneContext,
) -> _TriangleSceneObject:
    """Project one centered triangle prototype into pixel space at the requested slot."""
    pixel_vertices = tuple(
        graph_units_to_pixel(
            (float(slot_units[0]) + float(x), float(slot_units[1]) + float(y)),  # type: ignore[arg-type]
            origin=context.graph_origin,
            spacing=int(context.graph_spacing),
        )
        for x, y in prototype.local_vertices
    )
    center = graph_units_to_pixel(
        (float(slot_units[0]), float(slot_units[1])),  # type: ignore[arg-type]
        origin=context.graph_origin,
        spacing=int(context.graph_spacing),
    )
    return _TriangleSceneObject(
        polygon=PolygonSceneObject(
            label=str(label),
            vertices=tuple((float(point[0]), float(point[1])) for point in pixel_vertices),
            center=(float(center[0]), float(center[1])),
        ),
        side_kind=str(prototype.side_kind),
        angle_kind=str(prototype.angle_kind),
        angles_degrees=tuple(float(value) for value in prototype.angles_degrees),
        side_lengths=tuple(float(value) for value in prototype.side_lengths),
    )

def _sample_scene(
    rng,
    *,
    query_id: str,
    target_count: int,
    object_count: int,
    context: GraphSceneContext,
    min_side_units: float,
    max_side_units: float,
    min_side_gap_units: float,
    right_angle_margin_degrees: float,
    max_acute_angle_degrees: float,
    min_obtuse_angle_degrees: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw,
    shape_style,
    draw_object_labels: bool = True,
) -> _ScenePayload:
    """Sample and draw one multi-triangle counting scene."""
    last_error: Exception | None = None
    for _ in range(600):
        labels = list(assign_counting_labels(rng, object_count=int(object_count)))
        slots = _triangle_slots_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        positives = set(rng.sample(labels, int(target_count)))
        matching_labels: List[str] = []
        objects: List[_TriangleSceneObject] = []
        try:
            for label, slot in zip(labels, slots):
                prototype = _sample_triangle_for_match(
                    rng,
                    query_id=str(query_id),
                    positive=str(label) in positives,
                    min_side_units=float(min_side_units),
                    max_side_units=float(max_side_units),
                    min_side_gap_units=float(min_side_gap_units),
                    right_angle_margin_degrees=float(right_angle_margin_degrees),
                    max_acute_angle_degrees=float(max_acute_angle_degrees),
                    min_obtuse_angle_degrees=float(min_obtuse_angle_degrees),
                )
                if str(label) in positives:
                    matching_labels.append(str(label))
                objects.append(
                    _place_triangle_object(
                        prototype,
                        label=str(label),
                        slot_units=tuple(slot),
                        context=context,
                    )
                )
        except Exception as exc:
            last_error = exc
            continue
        render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
        vertex_padding_px = max(4.0, 0.65 * float(context.graph_spacing) * float(context.scene_scale))
        from ...shared.geometry_primitives import point_inside_square_canvas
        if not all(
            point_inside_square_canvas(
                (float(point[0]) * float(context.scene_scale), float(point[1]) * float(context.scene_scale)),
                canvas_size=int(render_canvas_size),
                padding=float(vertex_padding_px),
            )
            for obj in objects
            for point in obj.polygon.vertices
        ):
            continue
        object_bounds = [bounds_from_points(obj.polygon.vertices) for obj in objects]
        if not bounds_have_clearance(
            object_bounds,
            min_clearance_px=max(6.0, 0.35 * float(context.graph_spacing)),
        ):
            continue
        label_centers = draw_polygon_objects(
            draw,
            objects=[obj.polygon for obj in objects],
            scene_scale=int(context.scene_scale),
            line_width=int(line_width) * int(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            object_label_offset_px=float(object_label_offset_px),
            render_canvas_size=int(render_canvas_size),
            shape_style=shape_style,
            draw_object_labels=bool(draw_object_labels),
        )
        matching_labels_sorted = tuple(sorted(str(label) for label in matching_labels))
        return _ScenePayload(
            query_id=str(query_id),
            object_count=int(object_count),
            target_count=int(target_count),
            objects=tuple(objects),
            matching_labels=matching_labels_sorted,
            object_label_centers=label_centers,
            render_anchor={
                "matching_labels": list(matching_labels_sorted),
                "query_id": str(query_id),
            },
        )
    raise RuntimeError("failed to sample triangle-counting scene") from last_error

class GeometryCountingTriangleTask:
    """Count how many labeled triangles belong to one requested class."""
    task_id = "source_geometry_counting_triangle"
    domain = "geometry"
    task_group = "counting"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic multi-triangle counting instance."""
        scene_rng = spawn_rng(int(instance_seed), "scene")
        selected_variant, variant_probabilities = resolve_variant(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_variants=_SUPPORTED_VARIANTS,
            explicit_key="query_id",
            weights_key="variant_weights",
        )
        query_id = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected_variant),
            variant_probabilities=variant_probabilities,
            supported_variants=_SUPPORTED_VARIANTS,
            balance_flag_key="balanced_variant_sampling",
            explicit_key="query_id",
            weights_key="variant_weights",
        )
        object_count, object_count_probabilities, target_count, target_count_probabilities = resolve_counting_cardinality_pair(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_object_min=_DEFAULTS.object_count_min,
            fallback_object_max=_DEFAULTS.object_count_max,
        )
        min_side_units = float(
            params.get("min_side_units", group_default(_GEN_DEFAULTS, "min_side_units", _DEFAULTS.min_side_units))
        )
        max_side_units = float(
            params.get("max_side_units", group_default(_GEN_DEFAULTS, "max_side_units", _DEFAULTS.max_side_units))
        )
        right_angle_margin_degrees = float(
            params.get(
                "right_angle_margin_degrees",
                group_default(_GEN_DEFAULTS, "right_angle_margin_degrees", _DEFAULTS.right_angle_margin_degrees),
            )
        )
        max_acute_angle_degrees = float(
            params.get(
                "max_acute_angle_degrees",
                group_default(_GEN_DEFAULTS, "max_acute_angle_degrees", _DEFAULTS.max_acute_angle_degrees),
            )
        )
        min_obtuse_angle_degrees = float(
            params.get(
                "min_obtuse_angle_degrees",
                group_default(_GEN_DEFAULTS, "min_obtuse_angle_degrees", _DEFAULTS.min_obtuse_angle_degrees),
            )
        )
        min_side_gap_units = float(
            params.get(
                "min_side_gap_units",
                group_default(_GEN_DEFAULTS, "min_side_gap_units", _DEFAULTS.min_side_gap_units),
            )
        )
        if float(min_side_units) <= 0.0 or float(min_side_units) >= float(max_side_units):
            raise ValueError("min_side_units must be > 0 and < max_side_units")
        context_params = dict(params)
        context = None
        image = None
        background_meta = None
        shape_style = None
        label_font_size_px = None
        label_stroke_width_scene = None
        line_width = None
        scene_payload: _ScenePayload | None = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            context_attempt = resolve_graph_scene_context(
                scene_rng,
                instance_seed=int(instance_seed),
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                background_defaults=_BACKGROUND_DEFAULTS,
                fallback_canvas_min=_DEFAULTS.canvas_size_min,
                fallback_canvas_max=_DEFAULTS.canvas_size_max,
                fallback_cells_min=_DEFAULTS.graph_cells_min,
                fallback_cells_max=_DEFAULTS.graph_cells_max,
                require_graph_paper_background=False,
            )
            line_width_attempt = sample_int_render_param(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                key="line_width",
                fallback=_DEFAULTS.line_width,
                minimum_value=1,
            )
            label_font_size_px_attempt = int(
                params.get(
                    "label_font_size_px",
                    resolve_scene_label_font_size_px(
                        canvas_size=int(context_attempt.canvas_size),
                        graph_spacing=int(context_attempt.graph_spacing),
                        scene_scale=int(context_attempt.scene_scale),
                        min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                        max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
                    ),
                )
            )
            label_stroke_width_attempt = sample_int_render_param(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                key="label_stroke_width",
                fallback=_DEFAULTS.label_stroke_width,
                minimum_value=1,
            )
            label_stroke_width_scene_attempt = int(
                max(1, int(label_stroke_width_attempt) * int(context_attempt.scene_scale))
            )
            object_label_offset_px = float(
                context_params.get(
                    "object_label_offset_px",
                    group_default(_RENDER_DEFAULTS, "object_label_offset_px", _DEFAULTS.object_label_offset_px),
                )
            )
            image_attempt, draw_attempt, background_meta_attempt = make_graph_scene_canvas(
                instance_seed=int(instance_seed),
                context=context_attempt,
                background_defaults=_BACKGROUND_DEFAULTS,
                require_graph_paper=False,
            )
            shape_style_attempt = sample_geometry_shape_style(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                anchor_colors=extract_background_anchor_colors(background_meta_attempt),
            )
            try:
                scene_payload_attempt = _sample_scene(
                    scene_rng,
                    query_id=str(query_id),
                    target_count=int(target_count),
                    object_count=int(object_count),
                    context=context_attempt,
                    min_side_units=float(min_side_units),
                    max_side_units=float(max_side_units),
                    min_side_gap_units=float(min_side_gap_units),
                    right_angle_margin_degrees=float(right_angle_margin_degrees),
                    max_acute_angle_degrees=float(max_acute_angle_degrees),
                    min_obtuse_angle_degrees=float(min_obtuse_angle_degrees),
                    line_width=int(line_width_attempt),
                    label_font_size_px=int(label_font_size_px_attempt),
                    label_stroke_width=int(label_stroke_width_scene_attempt),
                    object_label_offset_px=float(object_label_offset_px),
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
                    draw_object_labels=bool(context_params.get("draw_object_labels", True)),
                )
                context = context_attempt
                image = image_attempt
                background_meta = background_meta_attempt
                shape_style = shape_style_attempt
                label_font_size_px = int(label_font_size_px_attempt)
                label_stroke_width_scene = int(label_stroke_width_scene_attempt)
                line_width = int(line_width_attempt)
                scene_payload = scene_payload_attempt
                break
            except Exception as exc:
                last_error = exc
                continue
        if (
            scene_payload is None
            or context is None
            or image is None
            or background_meta is None
            or shape_style is None
            or label_font_size_px is None
            or label_stroke_width_scene is None
            or line_width is None
        ):
            raise RuntimeError("failed to generate source_geometry_counting_triangle instance") from last_error
        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_equilateral_triangle",
                "question_text_isosceles_triangle",
                "question_text_scalene_triangle",
                "question_text_right_triangle",
                "question_text_acute_triangle",
                "question_text_obtuse_triangle",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(prompt_defaults[f"question_text_{str(query_id)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(type="label_set", value=list(scene_payload.matching_labels))
        class_by_label = {
            str(obj.polygon.label): {
                "side_kind": str(obj.side_kind),
                "angle_kind": str(obj.angle_kind),
            }
            for obj in scene_payload.objects
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_triangle_counting",
                "entities": [
                    {
                        "entity_id": f"triangle_{str(obj.polygon.label)}",
                        "entity_type": "triangle",
                        "attrs": {
                            "label": str(obj.polygon.label),
                            "side_kind": str(obj.side_kind),
                            "angle_kind": str(obj.angle_kind),
                            "angles_degrees": [float(value) for value in obj.angles_degrees],
                            "side_lengths": [float(value) for value in obj.side_lengths],
                            "vertices": [[float(point[0]), float(point[1])] for point in obj.polygon.vertices],
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "counting_target": "triangle_class",
                    "query_id": str(query_id),
                    "matching_labels": list(scene_payload.matching_labels),
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
                    "variant_probabilities": dict(variant_probabilities),
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "text_style": {
                    "font_size_px": int(label_font_size_px),
                    "stroke_width_px": int(label_stroke_width_scene),
                    "draw_object_labels": bool(context_params.get("draw_object_labels", True)),
                },
                "layout_coordinate_frame": dict(context.graph_frame),
                **dict(context.graph_layout_metadata),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {"matching": dict(scene_payload.render_anchor)},
                "object_label_centers": dict(scene_payload.object_label_centers),
            },
            "execution_trace": {
                "scene_variant": str(query_id),
                "query_id": str(query_id),
                "counting_class": str(_variant_class_label(str(query_id))),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "object_labels": [str(obj.polygon.label) for obj in scene_payload.objects],
                "matching_labels": list(scene_payload.matching_labels),
                "class_by_label": dict(class_by_label),
                "question_format": "count_matching_labeled_objects",
            },
            "witness_symbolic": {
                "counting_class": str(_variant_class_label(str(query_id))),
                "matching_labels": list(scene_payload.matching_labels),
            },
            "projected_evidence": {
                "labels": list(scene_payload.matching_labels),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=build_geometry_counting_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                object_count=int(object_count),
                object_count_min=int(_GEN_DEFAULTS["object_count_min"]),
                object_count_max=int(_GEN_DEFAULTS["object_count_max"]),
                target_count=int(target_count),
                task_kind="triangle",
            ),
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
