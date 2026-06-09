"""Non-grid geometry counting task over labeled convex and concave polygons."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ..shared.polygon_geometry import classify_polygon_convexity, transform_unit_vertices
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .defaults import COUNTING_SHARED_DEFAULTS
from .shared import (
    assign_counting_labels,
    bounds_from_points,
    bounds_have_clearance,
    bulky_counting_slot_centers_graph_units,
    resolve_counting_cardinality_pair,
)
_SUPPORTED_VARIANTS: Tuple[str, ...] = ("convex_polygon", "concave_polygon")
_SUPPORTED_SIDE_COUNTS: Tuple[int, ...] = (4, 5, 6)

@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for polygon-convexity counting generation."""
    canvas_size_min: int = COUNTING_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COUNTING_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = 28
    graph_cells_max: int = 36
    line_width: int = COUNTING_SHARED_DEFAULTS.line_width
    label_font_size_min: int = COUNTING_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COUNTING_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COUNTING_SHARED_DEFAULTS.label_stroke_width
    object_label_offset_px: float = 18.0
    object_count_min: int = 6
    object_count_max: int = 9

@dataclass(frozen=True)
class _PolygonPrototype:
    """One centered polygon prototype used by the convexity counting task."""
    prototype_id: str
    polygon_sides: int
    convexity_kind: str
    unit_vertices: Tuple[Tuple[int, int], ...]

@dataclass(frozen=True)
class _PolygonSceneObject:
    """One placed polygon object in the convexity counting scene."""
    polygon: PolygonSceneObject
    polygon_sides: int
    convexity_kind: str
    prototype_id: str

@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one polygon-convexity counting instance."""
    query_id: str
    object_count: int
    target_count: int
    objects: Tuple[_PolygonSceneObject, ...]
    matching_labels: Tuple[str, ...]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]

_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="source_geometry_counting_convexity",
)
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="counting")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="counting")

def _polygon_centroid(vertices: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Return one lightweight polygon centroid approximation for label placement."""
    total = max(1, len(vertices))
    return (
        sum(float(point[0]) for point in vertices) / float(total),
        sum(float(point[1]) for point in vertices) / float(total),
    )

def _validate_prototype(
    prototype_id: str,
    *,
    convexity_kind: str,
    unit_vertices: Sequence[Tuple[int, int]],
) -> _PolygonPrototype:
    """Validate one integer prototype against the shared convexity classifier."""
    classification = str(classify_polygon_convexity(unit_vertices))
    if classification != str(convexity_kind):
        raise ValueError(
            f"prototype {prototype_id} expected {convexity_kind} but classified as {classification}"
        )
    return _PolygonPrototype(
        prototype_id=str(prototype_id),
        polygon_sides=int(len(unit_vertices)),
        convexity_kind=str(convexity_kind),
        unit_vertices=tuple((int(x_value), int(y_value)) for x_value, y_value in unit_vertices),
    )

_PROTOTYPES_BY_KEY: Dict[Tuple[str, int], Tuple[_PolygonPrototype, ...]] = {
    ("convex", 4): (
        _validate_prototype(
            "convex_quad_rectangle",
            convexity_kind="convex",
            unit_vertices=((-3, -2), (3, -2), (3, 2), (-3, 2)),
        ),
        _validate_prototype(
            "convex_quad_parallelogram",
            convexity_kind="convex",
            unit_vertices=((-3, -2), (1, -2), (3, 2), (-1, 2)),
        ),
        _validate_prototype(
            "convex_quad_rhombus",
            convexity_kind="convex",
            unit_vertices=((0, -3), (3, 0), (0, 3), (-3, 0)),
        ),
    ),
    ("convex", 5): (
        _validate_prototype(
            "convex_pentagon_a",
            convexity_kind="convex",
            unit_vertices=((-2, -1), (0, -2), (3, -1), (2, 2), (-1, 2)),
        ),
        _validate_prototype(
            "convex_pentagon_b",
            convexity_kind="convex",
            unit_vertices=((-3, 0), (-1, -2), (2, -2), (3, 1), (0, 3)),
        ),
        _validate_prototype(
            "convex_pentagon_c",
            convexity_kind="convex",
            unit_vertices=((-3, -1), (0, -2), (3, -1), (2, 2), (-2, 2)),
        ),
    ),
    ("convex", 6): (
        _validate_prototype(
            "convex_hexagon_a",
            convexity_kind="convex",
            unit_vertices=((-3, 0), (-2, -2), (1, -2), (3, 0), (2, 2), (-1, 2)),
        ),
        _validate_prototype(
            "convex_hexagon_b",
            convexity_kind="convex",
            unit_vertices=((-3, -1), (-1, -2), (2, -2), (3, 0), (1, 2), (-2, 2)),
        ),
        _validate_prototype(
            "convex_hexagon_c",
            convexity_kind="convex",
            unit_vertices=((-2, -2), (1, -2), (3, 0), (2, 2), (-1, 2), (-3, 0)),
        ),
    ),
    ("concave", 4): (
        _validate_prototype(
            "concave_quad_a",
            convexity_kind="concave",
            unit_vertices=((-3, -2), (3, -2), (0, 0), (-2, 2)),
        ),
        _validate_prototype(
            "concave_quad_b",
            convexity_kind="concave",
            unit_vertices=((-3, -2), (3, -1), (0, 0), (-2, 2)),
        ),
    ),
    ("concave", 5): (
        _validate_prototype(
            "concave_pentagon_a",
            convexity_kind="concave",
            unit_vertices=((-3, -2), (3, -2), (1, 0), (3, 2), (-3, 2)),
        ),
        _validate_prototype(
            "concave_pentagon_b",
            convexity_kind="concave",
            unit_vertices=((-3, -2), (3, -2), (0, -1), (2, 2), (-3, 2)),
        ),
        _validate_prototype(
            "concave_pentagon_c",
            convexity_kind="concave",
            unit_vertices=((-3, -2), (2, -2), (0, 0), (3, 2), (-3, 2)),
        ),
    ),
    ("concave", 6): (
        _validate_prototype(
            "concave_hexagon_a",
            convexity_kind="concave",
            unit_vertices=((-4, -2), (0, -2), (1, -1), (4, -2), (4, 2), (-4, 2)),
        ),
        _validate_prototype(
            "concave_hexagon_b",
            convexity_kind="concave",
            unit_vertices=((-4, -2), (0, -2), (2, 0), (4, -2), (4, 2), (-4, 2)),
        ),
        _validate_prototype(
            "concave_hexagon_c",
            convexity_kind="concave",
            unit_vertices=((-4, -2), (-1, -2), (0, -1), (4, -2), (4, 2), (-4, 2)),
        ),
    ),
}

def _variant_class_label(query_id: str) -> str:
    """Return one normalized convexity class label for prompts and trace."""
    mapping = {
        "convex_polygon": "convex",
        "concave_polygon": "concave",
    }
    return str(mapping[str(query_id)])

def _resolve_side_count_weights(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Dict[str, float]:
    """Return normalized side-count weights for convexity scenes."""
    raw_weights = params.get(
        "side_count_weights",
        gen_defaults.get("side_count_weights", {str(value): 1.0 for value in _SUPPORTED_SIDE_COUNTS}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("side_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in {str(value) for value in _SUPPORTED_SIDE_COUNTS}
    }
    probabilities = normalize_positive_weights(
        weights,
        default_keys=[str(value) for value in _SUPPORTED_SIDE_COUNTS],
    )
    return {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))}

def _sample_prototype(
    rng,
    *,
    convexity_kind: str,
    side_count_probabilities: Mapping[str, float],
) -> _PolygonPrototype:
    """Sample one prototype with the requested convexity class."""
    side_count = int(weighted_choice(rng, side_count_probabilities, sort_keys=True))
    candidates = list(_PROTOTYPES_BY_KEY[(str(convexity_kind), int(side_count))])
    prototype = rng.choice(candidates)
    transform_index = int(rng.randrange(8))
    transformed_vertices = transform_unit_vertices(
        prototype.unit_vertices,
        transform_index=int(transform_index),
    )
    return _validate_prototype(
        f"{prototype.prototype_id}_t{int(transform_index)}",
        convexity_kind=str(convexity_kind),
        unit_vertices=transformed_vertices,
    )

def _place_polygon_object(
    prototype: _PolygonPrototype,
    *,
    label: str,
    slot_units: Tuple[int, int],
    context: GraphSceneContext,
) -> _PolygonSceneObject:
    """Project one local polygon prototype into pixel space at one slot."""
    pixel_vertices = tuple(
        graph_units_to_pixel(
            (float(slot_units[0]) + float(x_value), float(slot_units[1]) + float(y_value)),
            origin=context.graph_origin,
            spacing=int(context.graph_spacing),
        )
        for x_value, y_value in prototype.unit_vertices
    )
    center = _polygon_centroid(pixel_vertices)
    polygon = PolygonSceneObject(
        label=str(label),
        vertices=tuple((float(point[0]), float(point[1])) for point in pixel_vertices),
        center=(float(center[0]), float(center[1])),
    )
    return _PolygonSceneObject(
        polygon=polygon,
        polygon_sides=int(prototype.polygon_sides),
        convexity_kind=str(prototype.convexity_kind),
        prototype_id=str(prototype.prototype_id),
    )

def _object_fits_canvas(obj: _PolygonSceneObject, *, context: GraphSceneContext) -> bool:
    """Return whether one placed polygon stays inside the render canvas."""
    from ...shared.geometry_primitives import point_inside_square_canvas
    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    padding_px = max(4.0, 0.7 * float(context.graph_spacing) * float(context.scene_scale))
    return all(
        point_inside_square_canvas(
            (float(point[0]) * float(context.scene_scale), float(point[1]) * float(context.scene_scale)),
            canvas_size=int(render_canvas_size),
            padding=float(padding_px),
        )
        for point in obj.polygon.vertices
    )

def _sample_scene(
    rng,
    *,
    query_id: str,
    target_count: int,
    object_count: int,
    context: GraphSceneContext,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    side_count_probabilities: Mapping[str, float],
    draw,
    shape_style,
    draw_object_labels: bool = True,
) -> _ScenePayload:
    """Sample and draw one polygon-convexity counting scene."""
    target_class = str(_variant_class_label(str(query_id)))
    opposite_class = "concave" if str(target_class) == "convex" else "convex"
    last_error: Exception | None = None
    for _ in range(700):
        labels = list(assign_counting_labels(rng, object_count=int(object_count)))
        slots = bulky_counting_slot_centers_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        positives = set(rng.sample(labels, int(target_count)))
        matching_labels: List[str] = []
        objects: List[_PolygonSceneObject] = []
        try:
            for label, slot in zip(labels, slots):
                convexity_kind = str(target_class) if str(label) in positives else str(opposite_class)
                prototype = _sample_prototype(
                    rng,
                    convexity_kind=str(convexity_kind),
                    side_count_probabilities=side_count_probabilities,
                )
                if str(label) in positives:
                    matching_labels.append(str(label))
                objects.append(
                    _place_polygon_object(
                        prototype,
                        label=str(label),
                        slot_units=tuple(slot),
                        context=context,
                    )
                )
        except Exception as exc:
            last_error = exc
            continue
        if not all(_object_fits_canvas(obj, context=context) for obj in objects):
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
            render_canvas_size=int(context.canvas_size) * int(context.scene_scale),
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
    raise RuntimeError("failed to sample polygon-convexity counting scene") from last_error

class GeometryCountingConvexityTask:
    """Count how many labeled polygons are convex or concave."""
    task_id = "source_geometry_counting_convexity"
    domain = "geometry"
    task_group = "counting"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic polygon-convexity counting instance."""
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
        side_count_probabilities = _resolve_side_count_weights(params=params, gen_defaults=_GEN_DEFAULTS)
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
                params=params,
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
                params=params,
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
                params=params,
                render_defaults=_RENDER_DEFAULTS,
                key="label_stroke_width",
                fallback=_DEFAULTS.label_stroke_width,
                minimum_value=1,
            )
            label_stroke_width_scene_attempt = int(
                max(1, int(label_stroke_width_attempt) * int(context_attempt.scene_scale))
            )
            object_label_offset_px = float(
                params.get(
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
                params=params,
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
                    line_width=int(line_width_attempt),
                    label_font_size_px=int(label_font_size_px_attempt),
                    label_stroke_width=int(label_stroke_width_scene_attempt),
                    object_label_offset_px=float(object_label_offset_px),
                    side_count_probabilities=side_count_probabilities,
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
                    draw_object_labels=bool(params.get("draw_object_labels", True)),
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
            raise RuntimeError("failed to generate source_geometry_counting_convexity instance") from last_error
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
                "question_text_convex_polygon",
                "question_text_concave_polygon",
                "annotation_hint",
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
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        annotation_gt = TypedValue(type="label_set", value=list(scene_payload.matching_labels))
        class_by_label = {
            str(obj.polygon.label): {
                "convexity_kind": str(obj.convexity_kind),
                "polygon_sides": int(obj.polygon_sides),
                "prototype_id": str(obj.prototype_id),
            }
            for obj in scene_payload.objects
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_polygon_convexity_counting",
                "entities": [
                    {
                        "entity_id": f"polygon_{str(obj.polygon.label)}",
                        "entity_type": "polygon",
                        "attrs": {
                            "label": str(obj.polygon.label),
                            "convexity_kind": str(obj.convexity_kind),
                            "polygon_sides": int(obj.polygon_sides),
                            "prototype_id": str(obj.prototype_id),
                            "vertices": [[float(point[0]), float(point[1])] for point in obj.polygon.vertices],
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "counting_target": "polygon_convexity",
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
                    "query_id_probabilities": dict(variant_probabilities),
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "side_count_probabilities": dict(side_count_probabilities),
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
                    "draw_object_labels": bool(params.get("draw_object_labels", True)),
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
            "projected_annotation": {
                "labels": list(scene_payload.matching_labels),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
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
                task_kind="convexity",
                query_id=str(query_id),
            ),
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
