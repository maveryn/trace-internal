"""Consolidated geometry counting task with scene/query id axes."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.consolidated_source import (
    normalize_source_geometry_output,
    strip_consolidated_params,
    unregister_source_tasks,
)
from ..shared.consolidated_sampling import resolve_compatible_scene_query_ids
from ..shared.fixed_query_task import FixedGeometryQueryTaskMixin
from .angle import GeometryCountingAngleTask
from .convexity import GeometryCountingConvexityTask
from .quadrilateral import GeometryCountingQuadrilateralTask
from .shape_type import GeometryCountingShapeTypeTask
from .triangle import GeometryCountingTriangleTask

SOURCE_TASK_IDS: Tuple[str, ...] = (
    "source_geometry_counting_angle",
    "source_geometry_counting_convexity",
    "source_geometry_counting_quadrilateral",
    "source_geometry_counting_shape_type",
    "source_geometry_counting_triangle",
)
unregister_source_tasks(SOURCE_TASK_IDS)

TASK_ID = "geometry_counting_value_base"
ANGLE_TYPE_COUNT = "angle_type_count"
TRIANGLE_TYPE_COUNT = "triangle_type_count"
QUADRILATERAL_TYPE_COUNT = "quadrilateral_type_count"
SHAPE_TYPE_COUNT = "shape_type_count"
POLYGON_CONVEXITY_COUNT = "polygon_convexity_count"

_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "angle",
    "triangle",
    "quadrilateral",
    "mixed_shape",
    "polygon",
)
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    ANGLE_TYPE_COUNT,
    TRIANGLE_TYPE_COUNT,
    QUADRILATERAL_TYPE_COUNT,
    SHAPE_TYPE_COUNT,
    POLYGON_CONVEXITY_COUNT,
)
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": (ANGLE_TYPE_COUNT,),
    "triangle": (TRIANGLE_TYPE_COUNT,),
    "quadrilateral": (QUADRILATERAL_TYPE_COUNT,),
    "mixed_shape": (SHAPE_TYPE_COUNT,),
    "polygon": (POLYGON_CONVEXITY_COUNT,),
}
_CLASS_PARAM_BY_QUERY: Dict[str, str] = {
    ANGLE_TYPE_COUNT: "angle_type",
    TRIANGLE_TYPE_COUNT: "triangle_type",
    QUADRILATERAL_TYPE_COUNT: "quadrilateral_type",
    SHAPE_TYPE_COUNT: "shape_type",
    POLYGON_CONVEXITY_COUNT: "convexity_kind",
}
_CLASS_VALUES_BY_QUERY: Dict[str, Tuple[str, ...]] = {
    ANGLE_TYPE_COUNT: ("acute", "right", "obtuse"),
    TRIANGLE_TYPE_COUNT: ("equilateral", "isosceles", "scalene", "right", "acute", "obtuse"),
    QUADRILATERAL_TYPE_COUNT: ("square", "rectangle_non_square", "rhombus_non_square", "parallelogram_only"),
    SHAPE_TYPE_COUNT: ("triangle", "quadrilateral", "pentagon", "hexagon", "circle", "ellipse"),
    POLYGON_CONVEXITY_COUNT: ("convex", "concave"),
}
_SOURCE_QUERY_BY_CLASS_VALUE: Dict[str, Dict[str, str]] = {
    ANGLE_TYPE_COUNT: {
        "acute": "acute_angle",
        "right": "right_angle",
        "obtuse": "obtuse_angle",
    },
    TRIANGLE_TYPE_COUNT: {
        "equilateral": "equilateral_triangle",
        "isosceles": "isosceles_triangle",
        "scalene": "scalene_triangle",
        "right": "right_triangle",
        "acute": "acute_triangle",
        "obtuse": "obtuse_triangle",
    },
    QUADRILATERAL_TYPE_COUNT: {
        "square": "square",
        "rectangle_non_square": "rectangle_non_square",
        "rhombus_non_square": "rhombus_non_square",
        "parallelogram_only": "parallelogram_only",
    },
    SHAPE_TYPE_COUNT: {
        "triangle": "triangle",
        "quadrilateral": "quadrilateral",
        "pentagon": "pentagon",
        "hexagon": "hexagon",
        "circle": "circle",
        "ellipse": "ellipse",
    },
    POLYGON_CONVEXITY_COUNT: {
        "convex": "convex_polygon",
        "concave": "concave_polygon",
    },
}
_COUNTING_CLASS_PARAM_KEYS = frozenset(_CLASS_PARAM_BY_QUERY.values())
_SOURCE_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "acute_angle"): (GeometryCountingAngleTask, {"query_id": "acute_angle"}),
    ("angle", "right_angle"): (GeometryCountingAngleTask, {"query_id": "right_angle"}),
    ("angle", "obtuse_angle"): (GeometryCountingAngleTask, {"query_id": "obtuse_angle"}),
    ("triangle", "equilateral_triangle"): (GeometryCountingTriangleTask, {"query_id": "equilateral_triangle"}),
    ("triangle", "isosceles_triangle"): (GeometryCountingTriangleTask, {"query_id": "isosceles_triangle"}),
    ("triangle", "scalene_triangle"): (GeometryCountingTriangleTask, {"query_id": "scalene_triangle"}),
    ("triangle", "right_triangle"): (GeometryCountingTriangleTask, {"query_id": "right_triangle"}),
    ("triangle", "acute_triangle"): (GeometryCountingTriangleTask, {"query_id": "acute_triangle"}),
    ("triangle", "obtuse_triangle"): (GeometryCountingTriangleTask, {"query_id": "obtuse_triangle"}),
    ("quadrilateral", "square"): (GeometryCountingQuadrilateralTask, {"query_id": "square"}),
    ("quadrilateral", "rectangle_non_square"): (
        GeometryCountingQuadrilateralTask,
        {"query_id": "rectangle_non_square"},
    ),
    ("quadrilateral", "rhombus_non_square"): (GeometryCountingQuadrilateralTask, {"query_id": "rhombus_non_square"}),
    ("quadrilateral", "parallelogram_only"): (GeometryCountingQuadrilateralTask, {"query_id": "parallelogram_only"}),
    ("mixed_shape", "triangle"): (GeometryCountingShapeTypeTask, {"query_id": "triangle"}),
    ("mixed_shape", "quadrilateral"): (GeometryCountingShapeTypeTask, {"query_id": "quadrilateral"}),
    ("mixed_shape", "pentagon"): (GeometryCountingShapeTypeTask, {"query_id": "pentagon"}),
    ("mixed_shape", "hexagon"): (GeometryCountingShapeTypeTask, {"query_id": "hexagon"}),
    ("mixed_shape", "circle"): (GeometryCountingShapeTypeTask, {"query_id": "circle"}),
    ("mixed_shape", "ellipse"): (GeometryCountingShapeTypeTask, {"query_id": "ellipse"}),
    ("polygon", "convex_polygon"): (GeometryCountingConvexityTask, {"query_id": "convex_polygon"}),
    ("polygon", "concave_polygon"): (GeometryCountingConvexityTask, {"query_id": "concave_polygon"}),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_DELEGATED_GENERATION_KEYS: Tuple[str, ...] = (
    "object_count_min",
    "object_count_max",
    "object_count_weights",
    "target_count_min",
    "target_count_max",
    "target_count_weights",
)
_DELEGATED_RENDERING_KEYS: Tuple[str, ...] = (
    "graph_cells_min",
    "graph_cells_max",
    "object_label_offset_px",
)


def _delegated_count_seed(
    *,
    instance_seed: int,
    query_id: str,
    class_value: str,
) -> int:
    """Return a count-specific deterministic seed."""

    return abs(int(hash64(int(instance_seed), f"{TASK_ID}.{query_id}.{class_value}.counts", 0)))


def _resolve_counting_class_parameter(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, str, Dict[str, float], str]:
    """Resolve the counted class parameter for one family-level query id."""

    normalized_query = str(query_id)
    if normalized_query not in _CLASS_PARAM_BY_QUERY:
        raise ValueError(f"unsupported query_id: {query_id}")
    class_param_key = str(_CLASS_PARAM_BY_QUERY[normalized_query])
    unsupported = [
        str(key)
        for key in sorted(_COUNTING_CLASS_PARAM_KEYS)
        if str(key) != class_param_key and params.get(str(key)) is not None
    ]
    if unsupported:
        raise ValueError(f"{', '.join(unsupported)} is not supported for {normalized_query}")

    supported_values = tuple(_CLASS_VALUES_BY_QUERY[normalized_query])
    selected_class, class_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_values,
        explicit_key=class_param_key,
        weights_key=f"{class_param_key}_weights",
    )
    selected_class = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_class),
        variant_probabilities=class_probabilities,
        supported_variants=supported_values,
        balance_flag_key=f"balanced_{class_param_key}_sampling",
        explicit_key=class_param_key,
        weights_key=f"{class_param_key}_weights",
        sampling_namespace=f"{TASK_ID}.{class_param_key}",
    )
    source_query_id = _SOURCE_QUERY_BY_CLASS_VALUE[normalized_query][str(selected_class)]
    return (
        class_param_key,
        str(selected_class),
        {str(key): float(value) for key, value in sorted(class_probabilities.items())},
        str(source_query_id),
    )


def _apply_delegated_defaults(source_params: Dict[str, Any]) -> None:
    """Inject consolidated counting-value defaults into one delegated source task."""

    for key in _DELEGATED_GENERATION_KEYS:
        if key in _GEN_DEFAULTS and key not in source_params:
            source_params[str(key)] = _GEN_DEFAULTS[str(key)]
    for key in _DELEGATED_RENDERING_KEYS:
        if key in _RENDER_DEFAULTS and key not in source_params:
            source_params[str(key)] = _RENDER_DEFAULTS[str(key)]


def _canvas_dimensions(trace_payload: Mapping[str, Any]) -> Tuple[float, float]:
    render_spec = dict(trace_payload.get("render_spec") or {})
    canvas_size = render_spec.get("canvas_size", 720)
    if isinstance(canvas_size, (list, tuple)) and len(canvas_size) >= 2:
        return float(canvas_size[0]), float(canvas_size[1])
    return float(canvas_size), float(canvas_size)


def _clamp_bbox(
    bbox: Sequence[float],
    *,
    width: float,
    height: float,
) -> list[float]:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    left = max(0.0, min(float(width), min(x1, x2)))
    top = max(0.0, min(float(height), min(y1, y2)))
    right = max(0.0, min(float(width), max(x1, x2)))
    bottom = max(0.0, min(float(height), max(y1, y2)))
    return [round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)]


def _bbox_from_points(
    points: Sequence[Sequence[float]],
    *,
    width: float,
    height: float,
    padding: float = 10.0,
) -> list[float] | None:
    valid_points = [
        (float(point[0]), float(point[1]))
        for point in points
        if isinstance(point, (list, tuple)) and len(point) == 2
    ]
    if not valid_points:
        return None
    return _clamp_bbox(
        (
            min(point[0] for point in valid_points) - float(padding),
            min(point[1] for point in valid_points) - float(padding),
            max(point[0] for point in valid_points) + float(padding),
            max(point[1] for point in valid_points) + float(padding),
        ),
        width=float(width),
        height=float(height),
    )


def _entity_bbox(entity: Mapping[str, Any], *, width: float, height: float) -> Tuple[str, list[float] | None]:
    attrs = dict(entity.get("attrs") or {})
    label = str(attrs.get("label", entity.get("label", "")))
    if not label:
        return "", None

    vertices = attrs.get("vertices")
    if isinstance(vertices, list) and vertices:
        return label, _bbox_from_points(vertices, width=float(width), height=float(height))

    polygon_vertices = attrs.get("polygon_vertices")
    if isinstance(polygon_vertices, list) and polygon_vertices:
        return label, _bbox_from_points(polygon_vertices, width=float(width), height=float(height))

    points = attrs.get("points")
    if isinstance(points, Mapping):
        return label, _bbox_from_points(list(points.values()), width=float(width), height=float(height), padding=12.0)

    center = attrs.get("center")
    if isinstance(center, (list, tuple)) and len(center) == 2:
        radius = attrs.get("circle_radius_px")
        if isinstance(radius, (int, float)):
            return label, _clamp_bbox(
                (
                    float(center[0]) - float(radius) - 4.0,
                    float(center[1]) - float(radius) - 4.0,
                    float(center[0]) + float(radius) + 4.0,
                    float(center[1]) + float(radius) + 4.0,
                ),
                width=float(width),
                height=float(height),
            )
        radius_x = attrs.get("ellipse_radius_x_px")
        radius_y = attrs.get("ellipse_radius_y_px")
        if isinstance(radius_x, (int, float)) and isinstance(radius_y, (int, float)):
            return label, _clamp_bbox(
                (
                    float(center[0]) - float(radius_x) - 4.0,
                    float(center[1]) - float(radius_y) - 4.0,
                    float(center[0]) + float(radius_x) + 4.0,
                    float(center[1]) + float(radius_y) + 4.0,
                ),
                width=float(width),
                height=float(height),
            )

    return label, None


def _bbox_centers(bboxes: Sequence[Sequence[float]]) -> list[list[float]]:
    return [
        [
            round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
            round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
        ]
        for bbox in bboxes
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4
    ]


def _convert_counting_label_annotation_to_bboxes(output: TaskOutput) -> TaskOutput:
    """Convert consolidated counting label annotation to pixel object boxes."""

    if str(output.annotation_gt.type) != "label_set":
        return output

    labels = [str(label) for label in output.annotation_gt.value]
    trace_payload = dict(output.trace_payload)
    width, height = _canvas_dimensions(trace_payload)
    scene_ir = dict(trace_payload.get("scene_ir") or {})
    bbox_by_label: Dict[str, list[float]] = {}
    for entity in scene_ir.get("entities") or []:
        if not isinstance(entity, Mapping):
            continue
        label, bbox = _entity_bbox(entity, width=float(width), height=float(height))
        if label and bbox is not None:
            bbox_by_label[str(label)] = list(bbox)

    bboxes = [bbox_by_label[str(label)] for label in labels if str(label) in bbox_by_label]
    if len(bboxes) != len(labels):
        missing = [str(label) for label in labels if str(label) not in bbox_by_label]
        raise RuntimeError(f"counting bbox annotation missing labels: {missing}")

    witness_symbolic = {
        "type": "bbox_set",
        "count": len(bboxes),
    }
    trace_payload["witness_symbolic"] = witness_symbolic
    trace_payload["projected_annotation"] = {
        "type": "bbox_set",
        "bbox_set": [list(bbox) for bbox in bboxes],
        "pixel_bbox_set": [list(bbox) for bbox in bboxes],
        "pixel_point_set": _bbox_centers(bboxes),
    }
    return replace(output, annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in bboxes]), trace_payload=trace_payload)


class GeometryCountingValueTask:
    """Unified geometry counting task spanning angle, polygon, and mixed-shape scenes."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rng = spawn_rng(instance_seed, f"{self.task_id}.axes")
        scene_variant, scene_probs, query_id, query_probs = resolve_compatible_scene_query_ids(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_scene_variants=_SUPPORTED_SCENE_VARIANTS,
            supported_query_ids=_SUPPORTED_QUERY_IDS,
            compatibility=_COMPATIBILITY,
            scene_sampling_namespace=f"{self.task_id}.scene_variant",
            query_sampling_namespace=f"{self.task_id}.query_id",
        )
        class_param_key, class_value, class_probabilities, source_query_id = _resolve_counting_class_parameter(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            query_id=str(query_id),
        )
        source_task_cls, source_overrides = _SOURCE_BUILDERS[(str(scene_variant), str(source_query_id))]
        source_task = source_task_cls()
        source_params = strip_consolidated_params(params)
        for key in _COUNTING_CLASS_PARAM_KEYS:
            source_params.pop(str(key), None)
            source_params.pop(f"{key}_weights", None)
            source_params.pop(f"balanced_{key}_sampling", None)
        _apply_delegated_defaults(source_params)
        source_params["draw_object_labels"] = False
        source_params.update(dict(source_overrides))
        output = source_task.generate(int(instance_seed), params=source_params, max_attempts=int(max_attempts))
        source_trace = dict(output.trace_payload.get("execution_trace") or {})
        extra_query_params = {
            "counted_class_parameter": str(class_param_key),
            "counted_class": str(class_value),
            str(class_param_key): str(class_value),
            f"{class_param_key}_probabilities": dict(class_probabilities),
        }
        normalized_output = normalize_source_geometry_output(
            output,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
            source_task_id=str(source_task.task_id),
            scene_variant_probabilities=scene_probs,
            query_id_probabilities=query_probs,
            source_scene_variant=str(source_trace.get("scene_variant", scene_variant)),
            source_query_id=str(output.query_id),
            extra_query_params=extra_query_params,
        )
        return _convert_counting_label_annotation_to_bboxes(normalized_output)


@register_task
class GeometryCountingAngleTypeCountTask(FixedGeometryQueryTaskMixin, GeometryCountingValueTask):
    """Public angle-type counting task."""

    task_id = "task_geometry__graph_paper__angle_type_count"
    fixed_query_id = ANGLE_TYPE_COUNT
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("angle",)


@register_task
class GeometryCountingTriangleTypeCountTask(FixedGeometryQueryTaskMixin, GeometryCountingValueTask):
    """Public triangle-type counting task."""

    task_id = "task_geometry__graph_paper__triangle_type_count"
    fixed_query_id = TRIANGLE_TYPE_COUNT
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("triangle",)


@register_task
class GeometryCountingQuadrilateralTypeCountTask(FixedGeometryQueryTaskMixin, GeometryCountingValueTask):
    """Public quadrilateral-type counting task."""

    task_id = "task_geometry__graph_paper__quadrilateral_type_count"
    fixed_query_id = QUADRILATERAL_TYPE_COUNT
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("quadrilateral",)


@register_task
class GeometryCountingShapeTypeCountTask(FixedGeometryQueryTaskMixin, GeometryCountingValueTask):
    """Public mixed-shape type counting task."""

    task_id = "task_geometry__graph_paper__shape_type_count"
    fixed_query_id = SHAPE_TYPE_COUNT
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("mixed_shape",)


@register_task
class GeometryCountingPolygonConvexityCountTask(FixedGeometryQueryTaskMixin, GeometryCountingValueTask):
    """Public polygon-convexity counting task."""

    task_id = "task_geometry__graph_paper__polygon_convexity_count"
    fixed_query_id = POLYGON_CONVEXITY_COUNT
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("polygon",)
