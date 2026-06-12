"""Consolidated runtime helpers for graph-paper public objectives."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import hash64, spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.geometry.shared.consolidated_source import (
    normalize_source_geometry_output,
    strip_consolidated_params,
    unregister_source_tasks,
)
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .comparison.angle import GeometryComparisonAngleTask
from .comparison.area import GeometryComparisonAreaTask
from .comparison.length import GeometryComparisonLengthTask
from .comparison.perimeter import GeometryComparisonPerimeterTask
from .comparison.shared import COMPARISON_ANSWER_LABEL_POOL
from .counting.angle import GeometryCountingAngleTask
from .counting.convexity import GeometryCountingConvexityTask
from .counting.quadrilateral import GeometryCountingQuadrilateralTask
from .counting.shape_type import GeometryCountingShapeTypeTask
from .counting.triangle import GeometryCountingTriangleTask
from .measurement.angle import GeometryAngleMeasure2DTask
from .measurement.area import GeometryAreaMeasure2DTask
from .measurement.perimeter import GeometryPerimeterMeasure2DTask
from .measurement.slope import GeometrySlopeMeasureTask

SCENE_ID = "graph_paper"

unregister_source_tasks(
    (
        "source_geometry_measurement_angle",
        "source_geometry_measurement_area",
        "source_geometry_measurement_length",
        "source_geometry_measurement_perimeter",
        "source_geometry_measurement_slope",
        "source_geometry_comparison_angle",
        "source_geometry_comparison_area",
        "source_geometry_comparison_length",
        "source_geometry_comparison_perimeter",
        "source_geometry_counting_angle",
        "source_geometry_counting_convexity",
        "source_geometry_counting_quadrilateral",
        "source_geometry_counting_shape_type",
        "source_geometry_counting_triangle",
    )
)

_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)

_MEASUREMENT_TASK_KEY = "geometry_measurement_value_base"
_MEASUREMENT_SCENE_VARIANTS: Tuple[str, ...] = ("angle", "triangle", "quadrilateral", "circle", "ellipse", "line")
_MEASUREMENT_QUERY_IDS: Tuple[str, ...] = ("angle", "area", "perimeter", "slope")
_MEASUREMENT_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": ("angle",),
    "triangle": ("area", "perimeter"),
    "quadrilateral": ("area", "perimeter"),
    "circle": ("perimeter",),
    "ellipse": ("area",),
    "line": ("slope",),
}
_MEASUREMENT_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "angle"): (GeometryAngleMeasure2DTask, {}),
    ("triangle", "area"): (GeometryAreaMeasure2DTask, {"shape_variant": "triangle"}),
    ("quadrilateral", "area"): (GeometryAreaMeasure2DTask, {"shape_variant": "quadrilateral"}),
    ("ellipse", "area"): (GeometryAreaMeasure2DTask, {"shape_variant": "ellipse"}),
    ("triangle", "perimeter"): (GeometryPerimeterMeasure2DTask, {"shape_variant": "triangle"}),
    ("quadrilateral", "perimeter"): (GeometryPerimeterMeasure2DTask, {"shape_variant": "quadrilateral"}),
    ("circle", "perimeter"): (GeometryPerimeterMeasure2DTask, {"shape_variant": "circle"}),
    ("line", "slope"): (GeometrySlopeMeasureTask, {}),
}
_MEASUREMENT_GEN_DEFAULTS, _, _ = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=_MEASUREMENT_TASK_KEY,
)

_COMPARISON_TASK_KEY = "geometry_comparison_value_base"
_COMPARISON_SCENE_VARIANTS: Tuple[str, ...] = ("angle", "segment", "rectangle", "triangle")
_COMPARISON_QUERY_IDS: Tuple[str, ...] = ("angle_extremum", "length_extremum", "area_extremum", "perimeter_extremum")
_COMPARISON_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
_COMPARISON_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": ("angle_extremum",),
    "segment": ("length_extremum",),
    "rectangle": ("area_extremum", "perimeter_extremum"),
    "triangle": ("area_extremum", "perimeter_extremum"),
}
_COMPARISON_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "angle_extremum"): (GeometryComparisonAngleTask, {}),
    ("segment", "length_extremum"): (GeometryComparisonLengthTask, {}),
    ("rectangle", "area_extremum"): (GeometryComparisonAreaTask, {}),
    ("rectangle", "perimeter_extremum"): (GeometryComparisonPerimeterTask, {}),
    ("triangle", "area_extremum"): (GeometryComparisonAreaTask, {"shape_family": "triangle"}),
    ("triangle", "perimeter_extremum"): (GeometryComparisonPerimeterTask, {"shape_family": "triangle"}),
}
_COMPARISON_GEN_DEFAULTS, _, _ = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=_COMPARISON_TASK_KEY,
)

ANGLE_TYPE_COUNT = "angle_type_count"
TRIANGLE_TYPE_COUNT = "triangle_type_count"
QUADRILATERAL_TYPE_COUNT = "quadrilateral_type_count"
SHAPE_TYPE_COUNT = "shape_type_count"
POLYGON_CONVEXITY_COUNT = "polygon_convexity_count"

_COUNTING_TASK_KEY = "geometry_counting_value_base"
_COUNTING_SCENE_VARIANTS: Tuple[str, ...] = ("angle", "triangle", "quadrilateral", "mixed_shape", "polygon")
_COUNTING_QUERY_IDS: Tuple[str, ...] = (
    ANGLE_TYPE_COUNT,
    TRIANGLE_TYPE_COUNT,
    QUADRILATERAL_TYPE_COUNT,
    SHAPE_TYPE_COUNT,
    POLYGON_CONVEXITY_COUNT,
)
_COUNTING_COMPATIBILITY: Dict[str, Sequence[str]] = {
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
    ANGLE_TYPE_COUNT: {"acute": "acute_angle", "right": "right_angle", "obtuse": "obtuse_angle"},
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
    POLYGON_CONVEXITY_COUNT: {"convex": "convex_polygon", "concave": "concave_polygon"},
}
_COUNTING_CLASS_PARAM_KEYS = frozenset(_CLASS_PARAM_BY_QUERY.values())
_COUNTING_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
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
    ("quadrilateral", "rectangle_non_square"): (GeometryCountingQuadrilateralTask, {"query_id": "rectangle_non_square"}),
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
_COUNTING_GEN_DEFAULTS, _, _ = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=_COUNTING_TASK_KEY,
)
_DELEGATED_GENERATION_KEYS: Tuple[str, ...] = (
    "object_count_min",
    "object_count_max",
    "object_count_weights",
    "target_count_min",
    "target_count_max",
    "target_count_weights",
)
_DELEGATED_RENDERING_KEYS: Tuple[str, ...] = ("graph_cells_min", "graph_cells_max", "object_label_offset_px")


def _instantiate_source_task(source_task_cls: object) -> Any:
    source_task = source_task_cls()
    setattr(source_task, "scene_id", SCENE_ID)
    setattr(source_task, "public_scene_id", SCENE_ID)
    return source_task


def _full_probability_map(supported: Sequence[str], probabilities: Mapping[str, float]) -> Dict[str, float]:
    positive = {str(key): float(value) for key, value in probabilities.items()}
    return {str(key): float(positive.get(str(key), 0.0)) for key in supported}


def _resolve_scene_variant(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_scene_variants: Sequence[str],
    query_id: str,
    compatibility: Mapping[str, Sequence[str]],
    namespace: str,
) -> tuple[str, Dict[str, float], Dict[str, float]]:
    supported_scenes = tuple(str(value) for value in supported_scene_variants)
    allowed_scenes = tuple(
        scene
        for scene in supported_scenes
        if str(query_id) in {str(value) for value in compatibility.get(str(scene), ())}
    )
    if not allowed_scenes:
        raise ValueError(f"no compatible graph-paper scene variant for {query_id}")
    scene_variant, restricted_scene_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=allowed_scenes,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    scene_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(scene_variant),
        variant_probabilities=restricted_scene_probs,
        supported_variants=allowed_scenes,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=str(namespace),
    )
    return str(scene_variant), _full_probability_map(supported_scenes, restricted_scene_probs), {str(query_id): 1.0}


def build_measurement_output(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    allowed_scene_variants: Sequence[str],
    max_attempts: int,
) -> Any:
    rng = spawn_rng(int(instance_seed), "graph_paper.measurement.axes")
    scene_variant, scene_probs, query_probs = _resolve_scene_variant(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_MEASUREMENT_GEN_DEFAULTS,
        supported_scene_variants=tuple(allowed_scene_variants),
        query_id=str(query_id),
        compatibility=_MEASUREMENT_COMPATIBILITY,
        namespace="graph_paper.measurement.scene_variant",
    )
    source_task_cls, source_overrides = _MEASUREMENT_BUILDERS[(str(scene_variant), str(query_id))]
    source_task = _instantiate_source_task(source_task_cls)
    source_params = strip_consolidated_params(params)
    source_params.update(dict(source_overrides))
    output = source_task.generate(int(instance_seed), params=source_params, max_attempts=int(max_attempts))
    source_trace = dict(output.trace_payload.get("execution_trace") or {})
    return normalize_source_geometry_output(
        output,
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        source_task_id=str(source_task.task_id),
        scene_variant_probabilities=scene_probs,
        query_id_probabilities=query_probs,
        source_scene_variant=str(source_trace.get("scene_variant", scene_variant)),
        source_query_id=str(output.query_id),
    )


def _resolve_extremum_direction(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), "graph_paper.comparison.extremum_direction")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_COMPARISON_GEN_DEFAULTS,
        supported_variants=_COMPARISON_DIRECTIONS,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_COMPARISON_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_COMPARISON_DIRECTIONS,
        balance_flag_key="balanced_extremum_direction_sampling",
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        sampling_namespace=f"graph_paper.comparison.extremum_direction.{query_id}",
    )
    return str(selected), dict(probabilities)


def _inject_balanced_winner_label(
    params: Mapping[str, Any],
    source_params: Dict[str, Any],
    query_id: str,
    *,
    instance_seed: int,
) -> None:
    if "winner_label" in source_params or "winner_label_weights" in source_params:
        return
    sampling_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"graph_paper.comparison.winner_label.{query_id}",
    )
    label_index = int(sampling_index) % len(COMPARISON_ANSWER_LABEL_POOL)
    source_params["winner_label"] = str(COMPARISON_ANSWER_LABEL_POOL[int(label_index)])


def build_comparison_output(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    allowed_scene_variants: Sequence[str],
    max_attempts: int,
) -> Any:
    rng = spawn_rng(int(instance_seed), "graph_paper.comparison.axes")
    scene_variant, scene_probs, query_probs = _resolve_scene_variant(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_COMPARISON_GEN_DEFAULTS,
        supported_scene_variants=tuple(allowed_scene_variants),
        query_id=str(query_id),
        compatibility=_COMPARISON_COMPATIBILITY,
        namespace="graph_paper.comparison.scene_variant",
    )
    extremum_direction, extremum_probs = _resolve_extremum_direction(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    source_task_cls, source_overrides = _COMPARISON_BUILDERS[(str(scene_variant), str(query_id))]
    source_task = _instantiate_source_task(source_task_cls)
    source_params = strip_consolidated_params(params)
    source_params.update(dict(source_overrides))
    source_params["query_type"] = str(extremum_direction)
    _inject_balanced_winner_label(params, source_params, str(query_id), instance_seed=int(instance_seed))
    output = source_task.generate(int(instance_seed), params=source_params, max_attempts=int(max_attempts))
    source_trace = dict(output.trace_payload.get("execution_trace") or {})
    return normalize_source_geometry_output(
        output,
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        source_task_id=str(source_task.task_id),
        scene_variant_probabilities=scene_probs,
        query_id_probabilities=query_probs,
        source_scene_variant=str(source_trace.get("scene_variant", scene_variant)),
        source_query_id=str(output.query_id),
        extra_query_params={
            "extremum_direction": str(extremum_direction),
            "extremum_direction_probabilities": {
                str(key): float(value) for key, value in sorted(extremum_probs.items())
            },
        },
    )


def _delegated_count_seed(*, instance_seed: int, query_id: str, class_value: str) -> int:
    return abs(int(hash64(int(instance_seed), f"graph_paper.counting.{query_id}.{class_value}.counts", 0)))


def _resolve_counting_class_parameter(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, str, Dict[str, float], str]:
    class_param_key = str(_CLASS_PARAM_BY_QUERY[str(query_id)])
    unsupported = [
        str(key)
        for key in sorted(_COUNTING_CLASS_PARAM_KEYS)
        if str(key) != class_param_key and params.get(str(key)) is not None
    ]
    if unsupported:
        raise ValueError(f"{', '.join(unsupported)} is not supported for {query_id}")
    supported_values = tuple(_CLASS_VALUES_BY_QUERY[str(query_id)])
    selected_class, class_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_COUNTING_GEN_DEFAULTS,
        supported_variants=supported_values,
        explicit_key=class_param_key,
        weights_key=f"{class_param_key}_weights",
    )
    selected_class = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_COUNTING_GEN_DEFAULTS,
        selected_variant=str(selected_class),
        variant_probabilities=class_probabilities,
        supported_variants=supported_values,
        balance_flag_key=f"balanced_{class_param_key}_sampling",
        explicit_key=class_param_key,
        weights_key=f"{class_param_key}_weights",
        sampling_namespace=f"graph_paper.counting.{class_param_key}",
    )
    source_query_id = _SOURCE_QUERY_BY_CLASS_VALUE[str(query_id)][str(selected_class)]
    return class_param_key, str(selected_class), dict(class_probabilities), str(source_query_id)


def _apply_delegated_defaults(source_params: Dict[str, Any]) -> None:
    for key in _DELEGATED_GENERATION_KEYS:
        if key in _COUNTING_GEN_DEFAULTS and key not in source_params:
            source_params[str(key)] = _COUNTING_GEN_DEFAULTS[str(key)]
    for key in _DELEGATED_RENDERING_KEYS:
        if key in _COUNTING_GEN_DEFAULTS and key not in source_params:
            source_params[str(key)] = _COUNTING_GEN_DEFAULTS[str(key)]


def _bbox_centers(bboxes: Sequence[Sequence[float]]) -> list[list[float]]:
    return [
        [round((float(bbox[0]) + float(bbox[2])) / 2.0, 3), round((float(bbox[1]) + float(bbox[3])) / 2.0, 3)]
        for bbox in bboxes
    ]


def _convert_counting_label_annotation_to_bboxes(output: Any) -> Any:
    trace_payload = dict(output.trace_payload)
    required_labels = list((trace_payload.get("execution_trace") or {}).get("required_annotation_labels") or [])
    render_map = dict(trace_payload.get("render_map") or {})
    bboxes_by_label = dict(render_map.get("object_bboxes") or {})
    bboxes = [list(bboxes_by_label[str(label)]) for label in required_labels if str(label) in bboxes_by_label]
    if not bboxes:
        return output
    trace_payload["projected_annotation"] = {
        "type": "bbox_set",
        "bbox_set": [list(bbox) for bbox in bboxes],
        "pixel_point_set": _bbox_centers(bboxes),
    }
    return output.__class__(
        prompt=output.prompt,
        answer_gt=output.answer_gt,
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in bboxes]),
        image=output.image,
        image_id=output.image_id,
        trace_payload=trace_payload,
        task_versions=output.task_versions,
        query_id=output.query_id,
        prompt_variants=output.prompt_variants,
    )


def build_counting_output(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    allowed_scene_variants: Sequence[str],
    max_attempts: int,
) -> Any:
    rng = spawn_rng(int(instance_seed), "graph_paper.counting.axes")
    scene_variant, scene_probs, query_probs = _resolve_scene_variant(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_COUNTING_GEN_DEFAULTS,
        supported_scene_variants=tuple(allowed_scene_variants),
        query_id=str(query_id),
        compatibility=_COUNTING_COMPATIBILITY,
        namespace="graph_paper.counting.scene_variant",
    )
    class_param_key, class_value, class_probabilities, source_query_id = _resolve_counting_class_parameter(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    source_task_cls, source_overrides = _COUNTING_BUILDERS[(str(scene_variant), str(source_query_id))]
    source_task = _instantiate_source_task(source_task_cls)
    source_params = strip_consolidated_params(params)
    for key in _COUNTING_CLASS_PARAM_KEYS:
        source_params.pop(str(key), None)
        source_params.pop(f"{key}_weights", None)
        source_params.pop(f"balanced_{key}_sampling", None)
    _apply_delegated_defaults(source_params)
    source_params["draw_object_labels"] = False
    source_params.update(dict(source_overrides))
    output = source_task.generate(
        _delegated_count_seed(instance_seed=int(instance_seed), query_id=str(query_id), class_value=str(class_value)),
        params=source_params,
        max_attempts=int(max_attempts),
    )
    source_trace = dict(output.trace_payload.get("execution_trace") or {})
    normalized_output = normalize_source_geometry_output(
        output,
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        source_task_id=str(source_task.task_id),
        scene_variant_probabilities=scene_probs,
        query_id_probabilities=query_probs,
        source_scene_variant=str(source_trace.get("scene_variant", scene_variant)),
        source_query_id=str(output.query_id),
        extra_query_params={
            "counted_class_parameter": str(class_param_key),
            "counted_class": str(class_value),
            str(class_param_key): str(class_value),
            f"{class_param_key}_probabilities": dict(class_probabilities),
        },
    )
    return _convert_counting_label_annotation_to_bboxes(normalized_output)
