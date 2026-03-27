"""Non-grid geometry counting task over mixed labeled shape types."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
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
from ..shared.graph_rendering import graph_units_to_pixel
from ..shared.multi_shape_scene import MixedShapeSceneObject, draw_mixed_shape_objects
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.quadrilateral_prototypes import sample_parallelogram_only_prototype, sample_rectangle_non_square_prototype
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
    bulky_counting_slot_centers_graph_units,
    counting_complexity_score,
    resolve_counting_cardinality_pair,
)

_SUPPORTED_VARIANTS: Tuple[str, ...] = (
    "triangle",
    "quadrilateral",
    "pentagon",
    "hexagon",
    "circle",
    "ellipse",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for mixed shape-type counting generation."""

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
    min_extent_units: float = 2.6
    max_extent_units: float = 4.8
    ellipse_axis_ratio_min: float = 1.35
    min_side_gap_units: float = 0.8
    min_slant_units: float = 1.0


@dataclass(frozen=True)
class _ShapePrototype:
    """One centered local-shape prototype for mixed counting scenes."""

    shape_type: str
    polygon_vertices: Tuple[Tuple[float, float], ...] = ()
    circle_radius_units: float | None = None
    ellipse_radius_x_units: float | None = None
    ellipse_radius_y_units: float | None = None


@dataclass(frozen=True)
class _MixedShapeObject:
    """One placed mixed-shape object in the counting scene."""

    shape: MixedShapeSceneObject
    shape_type: str


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one mixed shape-type counting instance."""

    task_variant: str
    object_count: int
    target_count: int
    objects: Tuple[_MixedShapeObject, ...]
    matching_labels: Tuple[str, ...]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_counting_shape_type",
)
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="counting")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="counting")


def _regular_polygon_vertices(side_count: int, *, radius_units: float, rotation_radians: float) -> Tuple[Tuple[float, float], ...]:
    """Return centered regular-polygon vertices."""

    return tuple(
        (
            float(radius_units) * math.cos(float(rotation_radians) + (2.0 * math.pi * float(index) / float(side_count))),
            float(radius_units) * math.sin(float(rotation_radians) + (2.0 * math.pi * float(index) / float(side_count))),
        )
        for index in range(int(side_count))
    )


def _sample_triangle_prototype(rng, *, min_extent_units: float, max_extent_units: float, **_kwargs: Any) -> _ShapePrototype:
    """Return one centered triangle prototype for mixed shape scenes."""

    radius = float(rng.uniform(float(min_extent_units), float(max_extent_units)))
    rotation = float(rng.uniform(-0.3, 0.3))
    return _ShapePrototype(
        shape_type="triangle",
        polygon_vertices=_regular_polygon_vertices(3, radius_units=float(radius), rotation_radians=float(rotation)),
    )


def _sample_quadrilateral_prototype(
    rng,
    *,
    min_extent_units: float,
    max_extent_units: float,
    min_side_gap_units: float,
    min_slant_units: float,
    **_kwargs: Any,
) -> _ShapePrototype:
    """Return one centered quadrilateral prototype for mixed shape scenes."""

    if bool(rng.randint(0, 1)):
        prototype = sample_rectangle_non_square_prototype(
            rng,
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
            min_side_gap_units=float(min_side_gap_units),
        )
    else:
        prototype = sample_parallelogram_only_prototype(
            rng,
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
            min_side_gap_units=float(min_side_gap_units),
            min_slant_units=float(min_slant_units),
        )
    return _ShapePrototype(shape_type="quadrilateral", polygon_vertices=tuple(prototype.local_vertices))


def _sample_pentagon_prototype(rng, *, min_extent_units: float, max_extent_units: float, **_kwargs: Any) -> _ShapePrototype:
    """Return one centered pentagon prototype."""

    radius = float(rng.uniform(float(min_extent_units), float(max_extent_units)))
    rotation = float(rng.uniform(-0.25, 0.25))
    return _ShapePrototype(
        shape_type="pentagon",
        polygon_vertices=_regular_polygon_vertices(5, radius_units=float(radius), rotation_radians=float(rotation)),
    )


def _sample_hexagon_prototype(rng, *, min_extent_units: float, max_extent_units: float, **_kwargs: Any) -> _ShapePrototype:
    """Return one centered hexagon prototype."""

    radius = float(rng.uniform(float(min_extent_units), float(max_extent_units)))
    rotation = float(rng.uniform(-0.2, 0.2))
    return _ShapePrototype(
        shape_type="hexagon",
        polygon_vertices=_regular_polygon_vertices(6, radius_units=float(radius), rotation_radians=float(rotation)),
    )


def _sample_circle_prototype(rng, *, min_extent_units: float, max_extent_units: float, **_kwargs: Any) -> _ShapePrototype:
    """Return one centered circle prototype."""

    radius = float(rng.uniform(float(min_extent_units), float(max_extent_units)))
    return _ShapePrototype(shape_type="circle", circle_radius_units=float(radius))


def _sample_ellipse_prototype(
    rng,
    *,
    min_extent_units: float,
    max_extent_units: float,
    ellipse_axis_ratio_min: float,
    **_kwargs: Any,
) -> _ShapePrototype:
    """Return one centered ellipse prototype that is visibly non-circular."""

    for _ in range(300):
        radius_x = float(rng.uniform(float(min_extent_units), float(max_extent_units)))
        radius_y = float(rng.uniform(float(min_extent_units), float(max_extent_units)))
        ratio = max(float(radius_x), float(radius_y)) / max(1e-9, min(float(radius_x), float(radius_y)))
        if float(ratio) < float(ellipse_axis_ratio_min):
            continue
        return _ShapePrototype(
            shape_type="ellipse",
            ellipse_radius_x_units=float(radius_x),
            ellipse_radius_y_units=float(radius_y),
        )
    raise ValueError("failed to sample non-circular ellipse prototype")


_SAMPLERS = {
    "triangle": _sample_triangle_prototype,
    "quadrilateral": _sample_quadrilateral_prototype,
    "pentagon": _sample_pentagon_prototype,
    "hexagon": _sample_hexagon_prototype,
    "circle": _sample_circle_prototype,
    "ellipse": _sample_ellipse_prototype,
}


def _sample_shape_prototype(
    rng,
    *,
    shape_type: str,
    min_extent_units: float,
    max_extent_units: float,
    ellipse_axis_ratio_min: float,
    min_side_gap_units: float,
    min_slant_units: float,
) -> _ShapePrototype:
    """Dispatch one shape-type prototype sampler."""

    sampler = _SAMPLERS[str(shape_type)]
    return sampler(
        rng,
        min_extent_units=float(min_extent_units),
        max_extent_units=float(max_extent_units),
        ellipse_axis_ratio_min=float(ellipse_axis_ratio_min),
        min_side_gap_units=float(min_side_gap_units),
        min_slant_units=float(min_slant_units),
    )


def _sample_shape_for_match(
    rng,
    *,
    task_variant: str,
    positive: bool,
    min_extent_units: float,
    max_extent_units: float,
    ellipse_axis_ratio_min: float,
    min_side_gap_units: float,
    min_slant_units: float,
) -> _ShapePrototype:
    """Sample one shape prototype that either matches or rejects the query type."""

    if bool(positive):
        return _sample_shape_prototype(
            rng,
            shape_type=str(task_variant),
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
            ellipse_axis_ratio_min=float(ellipse_axis_ratio_min),
            min_side_gap_units=float(min_side_gap_units),
            min_slant_units=float(min_slant_units),
        )
    negative_types = [shape_type for shape_type in _SUPPORTED_VARIANTS if str(shape_type) != str(task_variant)]
    chosen = str(rng.choice(negative_types))
    return _sample_shape_prototype(
        rng,
        shape_type=str(chosen),
        min_extent_units=float(min_extent_units),
        max_extent_units=float(max_extent_units),
        ellipse_axis_ratio_min=float(ellipse_axis_ratio_min),
        min_side_gap_units=float(min_side_gap_units),
        min_slant_units=float(min_slant_units),
    )


def _place_shape_object(
    prototype: _ShapePrototype,
    *,
    label: str,
    slot_units: Tuple[int, int],
    context: GraphSceneContext,
) -> _MixedShapeObject:
    """Project one centered shape prototype into pixel space at the requested slot."""

    center = graph_units_to_pixel(
        (float(slot_units[0]), float(slot_units[1])),
        origin=context.graph_origin,
        spacing=int(context.graph_spacing),
    )
    if prototype.polygon_vertices:
        pixel_vertices = tuple(
            graph_units_to_pixel(
                (float(slot_units[0]) + float(x), float(slot_units[1]) + float(y)),
                origin=context.graph_origin,
                spacing=int(context.graph_spacing),
            )
            for x, y in prototype.polygon_vertices
        )
        shape = MixedShapeSceneObject(
            label=str(label),
            shape_kind=str(prototype.shape_type),
            center=(float(center[0]), float(center[1])),
            polygon_vertices=tuple((float(point[0]), float(point[1])) for point in pixel_vertices),
        )
    elif prototype.circle_radius_units is not None:
        shape = MixedShapeSceneObject(
            label=str(label),
            shape_kind=str(prototype.shape_type),
            center=(float(center[0]), float(center[1])),
            circle_radius_px=float(prototype.circle_radius_units) * float(context.graph_spacing),
        )
    else:
        shape = MixedShapeSceneObject(
            label=str(label),
            shape_kind=str(prototype.shape_type),
            center=(float(center[0]), float(center[1])),
            ellipse_radius_x_px=float(prototype.ellipse_radius_x_units or 0.0) * float(context.graph_spacing),
            ellipse_radius_y_px=float(prototype.ellipse_radius_y_units or 0.0) * float(context.graph_spacing),
        )
    return _MixedShapeObject(shape=shape, shape_type=str(prototype.shape_type))


def _object_fits_canvas(obj: _MixedShapeObject, *, context: GraphSceneContext) -> bool:
    """Return whether one placed object stays inside the render canvas."""

    from ...shared.geometry_primitives import point_inside_square_canvas

    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    padding_px = max(4.0, 0.7 * float(context.graph_spacing) * float(context.scene_scale))
    if obj.shape.polygon_vertices:
        return all(
            point_inside_square_canvas(
                (float(point[0]) * float(context.scene_scale), float(point[1]) * float(context.scene_scale)),
                canvas_size=int(render_canvas_size),
                padding=float(padding_px),
            )
            for point in obj.shape.polygon_vertices
        )
    center_scaled = (
        float(obj.shape.center[0]) * float(context.scene_scale),
        float(obj.shape.center[1]) * float(context.scene_scale),
    )
    if obj.shape.circle_radius_px is not None:
        radius = float(obj.shape.circle_radius_px) * float(context.scene_scale)
        return (
            center_scaled[0] - float(radius) >= float(padding_px)
            and center_scaled[0] + float(radius) <= float(render_canvas_size) - float(padding_px)
            and center_scaled[1] - float(radius) >= float(padding_px)
            and center_scaled[1] + float(radius) <= float(render_canvas_size) - float(padding_px)
        )
    radius_x = float(obj.shape.ellipse_radius_x_px or 0.0) * float(context.scene_scale)
    radius_y = float(obj.shape.ellipse_radius_y_px or 0.0) * float(context.scene_scale)
    return (
        center_scaled[0] - float(radius_x) >= float(padding_px)
        and center_scaled[0] + float(radius_x) <= float(render_canvas_size) - float(padding_px)
        and center_scaled[1] - float(radius_y) >= float(padding_px)
        and center_scaled[1] + float(radius_y) <= float(render_canvas_size) - float(padding_px)
    )


def _sample_scene(
    rng,
    *,
    task_variant: str,
    target_count: int,
    object_count: int,
    context: GraphSceneContext,
    min_extent_units: float,
    max_extent_units: float,
    ellipse_axis_ratio_min: float,
    min_side_gap_units: float,
    min_slant_units: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw,
    shape_style,
) -> _ScenePayload:
    """Sample and draw one mixed shape-type counting scene."""

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
        objects: List[_MixedShapeObject] = []
        try:
            for label, slot in zip(labels, slots):
                prototype = _sample_shape_for_match(
                    rng,
                    task_variant=str(task_variant),
                    positive=str(label) in positives,
                    min_extent_units=float(min_extent_units),
                    max_extent_units=float(max_extent_units),
                    ellipse_axis_ratio_min=float(ellipse_axis_ratio_min),
                    min_side_gap_units=float(min_side_gap_units),
                    min_slant_units=float(min_slant_units),
                )
                if str(label) in positives:
                    matching_labels.append(str(label))
                objects.append(
                    _place_shape_object(
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
        label_centers = draw_mixed_shape_objects(
            draw,
            objects=[obj.shape for obj in objects],
            scene_scale=int(context.scene_scale),
            line_width=int(line_width) * int(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            object_label_offset_px=float(object_label_offset_px),
            render_canvas_size=int(context.canvas_size) * int(context.scene_scale),
            shape_style=shape_style,
        )
        matching_labels_sorted = tuple(sorted(str(label) for label in matching_labels))
        return _ScenePayload(
            task_variant=str(task_variant),
            object_count=int(object_count),
            target_count=int(target_count),
            objects=tuple(objects),
            matching_labels=matching_labels_sorted,
            object_label_centers=label_centers,
            render_anchor={
                "matching_labels": list(matching_labels_sorted),
                "task_variant": str(task_variant),
            },
        )
    raise RuntimeError("failed to sample mixed shape-type counting scene") from last_error


@register_task
class GeometryCountingShapeTypeTask:
    """Count how many labeled shapes match one requested mixed shape type."""

    task_id = "task_geometry_counting_shape_type"
    domain = "geometry"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic mixed shape-type counting instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        selected_variant, variant_probabilities = resolve_variant(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_variants=_SUPPORTED_VARIANTS,
            explicit_key="task_variant",
            weights_key="variant_weights",
        )
        task_variant = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected_variant),
            variant_probabilities=variant_probabilities,
            supported_variants=_SUPPORTED_VARIANTS,
            balance_flag_key="balanced_variant_sampling",
            explicit_key="task_variant",
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

        min_extent_units = float(
            params.get("min_extent_units", group_default(_GEN_DEFAULTS, "min_extent_units", _DEFAULTS.min_extent_units))
        )
        max_extent_units = float(
            params.get("max_extent_units", group_default(_GEN_DEFAULTS, "max_extent_units", _DEFAULTS.max_extent_units))
        )
        ellipse_axis_ratio_min = float(
            params.get(
                "ellipse_axis_ratio_min",
                group_default(_GEN_DEFAULTS, "ellipse_axis_ratio_min", _DEFAULTS.ellipse_axis_ratio_min),
            )
        )
        min_side_gap_units = float(
            params.get(
                "min_side_gap_units",
                group_default(_GEN_DEFAULTS, "min_side_gap_units", _DEFAULTS.min_side_gap_units),
            )
        )
        min_slant_units = float(
            params.get("min_slant_units", group_default(_GEN_DEFAULTS, "min_slant_units", _DEFAULTS.min_slant_units))
        )
        if float(min_extent_units) <= 0.0 or float(min_extent_units) >= float(max_extent_units):
            raise ValueError("min_extent_units must be > 0 and < max_extent_units")

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
            label_stroke_width_scene_attempt = int(max(1, int(label_stroke_width_attempt) * int(context_attempt.scene_scale)))
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
                    task_variant=str(task_variant),
                    target_count=int(target_count),
                    object_count=int(object_count),
                    context=context_attempt,
                    min_extent_units=float(min_extent_units),
                    max_extent_units=float(max_extent_units),
                    ellipse_axis_ratio_min=float(ellipse_axis_ratio_min),
                    min_side_gap_units=float(min_side_gap_units),
                    min_slant_units=float(min_slant_units),
                    line_width=int(line_width_attempt),
                    label_font_size_px=int(label_font_size_px_attempt),
                    label_stroke_width=int(label_stroke_width_scene_attempt),
                    object_label_offset_px=float(object_label_offset_px),
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
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
            raise RuntimeError("failed to generate task_geometry_counting_shape_type instance") from last_error

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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_triangle",
                "question_text_quadrilateral",
                "question_text_pentagon",
                "question_text_hexagon",
                "question_text_circle",
                "question_text_ellipse",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(prompt_defaults[f"question_text_{str(task_variant)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
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
            str(obj.shape.label): {"shape_type": str(obj.shape_type)}
            for obj in scene_payload.objects
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_shape_type_counting",
                "entities": [
                    {
                        "entity_id": f"shape_{str(obj.shape.label)}",
                        "entity_type": str(obj.shape.shape_kind),
                        "attrs": {
                            "label": str(obj.shape.label),
                            "shape_type": str(obj.shape_type),
                            "polygon_vertices": [
                                [float(point[0]), float(point[1])] for point in obj.shape.polygon_vertices
                            ],
                            "circle_radius_px": (
                                None if obj.shape.circle_radius_px is None else float(obj.shape.circle_radius_px)
                            ),
                            "ellipse_radius_x_px": (
                                None if obj.shape.ellipse_radius_x_px is None else float(obj.shape.ellipse_radius_x_px)
                            ),
                            "ellipse_radius_y_px": (
                                None if obj.shape.ellipse_radius_y_px is None else float(obj.shape.ellipse_radius_y_px)
                            ),
                            "center": [float(obj.shape.center[0]), float(obj.shape.center[1])],
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "counting_target": "shape_type",
                    "task_variant": str(task_variant),
                    "matching_labels": list(scene_payload.matching_labels),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
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
                },
                "layout_coordinate_frame": dict(context.graph_frame),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {"matching": dict(scene_payload.render_anchor)},
                "object_label_centers": dict(scene_payload.object_label_centers),
            },
            "execution_trace": {
                "scene_variant": str(task_variant),
                "task_variant": str(task_variant),
                "counting_class": str(task_variant),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "object_labels": [str(obj.shape.label) for obj in scene_payload.objects],
                "matching_labels": list(scene_payload.matching_labels),
                "class_by_label": dict(class_by_label),
                "question_format": "count_matching_labeled_objects",
            },
            "witness_symbolic": {
                "counting_class": str(task_variant),
                "matching_labels": list(scene_payload.matching_labels),
            },
            "projected_evidence": {
                "label_set": list(scene_payload.matching_labels),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=TaskComplexity(
                complexity_score=counting_complexity_score(
                    object_count=int(object_count),
                    target_count=int(target_count),
                ),
                complexity_components={
                    "object_count": int(object_count),
                    "target_count": int(target_count),
                    "task_variant": str(task_variant),
                },
            ),
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
