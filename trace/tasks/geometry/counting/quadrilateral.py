"""Non-grid geometry counting task over multiple labeled quadrilaterals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

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
from ..shared.multi_polygon_scene import PolygonSceneObject, draw_polygon_objects
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.quadrilateral_prototypes import (
    QuadrilateralPrototype,
    sample_parallelogram_only_prototype,
    sample_rectangle_non_square_prototype,
    sample_rhombus_non_square_prototype,
    sample_square_prototype,
)
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
    counting_complexity_score,
    resolve_counting_cardinality_pair,
)

_SUPPORTED_VARIANTS: Tuple[str, ...] = (
    "square",
    "rectangle_non_square",
    "rhombus_non_square",
    "parallelogram_only",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for quadrilateral-counting generation."""

    canvas_size_min: int = COUNTING_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COUNTING_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = 26
    graph_cells_max: int = 34
    line_width: int = COUNTING_SHARED_DEFAULTS.line_width
    label_font_size_min: int = COUNTING_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COUNTING_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COUNTING_SHARED_DEFAULTS.label_stroke_width
    object_label_offset_px: float = 18.0
    object_count_min: int = 5
    object_count_max: int = 7
    min_extent_units: float = 3.0
    max_extent_units: float = 5.8
    min_side_gap_units: float = 0.8
    min_slant_units: float = 1.0


@dataclass(frozen=True)
class _QuadrilateralSceneObject:
    """One placed quadrilateral object in the counting scene."""

    polygon: PolygonSceneObject
    quadrilateral_kind: str
    side_lengths: Tuple[float, float, float, float]
    angles_degrees: Tuple[float, float, float, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one multi-quadrilateral counting instance."""

    task_variant: str
    object_count: int
    target_count: int
    objects: Tuple[_QuadrilateralSceneObject, ...]
    matching_labels: Tuple[str, ...]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_counting_quadrilateral",
)
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="counting")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="counting")


def _quadrilateral_slots_graph_units(*, object_count: int, graph_cells: int, rng) -> List[Tuple[int, int]]:
    """Return a roomy hidden-grid slot bank for 5-7 quadrilateral objects."""

    half_span = max(13, int(graph_cells // 2))
    outer_x = max(7, min(int(round(float(half_span) * 0.76)), int(half_span - 3)))
    inner_x = max(2, min(int(round(float(half_span) * 0.24)), max(2, int(outer_x - 3))))
    row_y = max(5, min(int(round(float(half_span) * 0.40)), int(half_span - 3)))
    base_slots = [
        (-int(outer_x), int(row_y)),
        (-int(inner_x), int(row_y)),
        (int(inner_x), int(row_y)),
        (int(outer_x), int(row_y)),
        (-int(outer_x), -int(row_y)),
        (0, -int(row_y)),
        (int(outer_x), -int(row_y)),
    ]
    rng.shuffle(base_slots)
    return list(base_slots[: int(object_count)])


def _variant_class_label(task_variant: str) -> str:
    """Return a normalized human-readable quadrilateral class label."""

    return str(task_variant)


def _matches_variant(kind: str, task_variant: str) -> bool:
    """Return whether one quadrilateral kind matches the requested class."""

    return str(kind) == str(task_variant)


def _positive_sampler_names(task_variant: str) -> Tuple[str, ...]:
    """Return likely-positive prototype sampler names for one variant."""

    mapping = {
        "square": ("square",),
        "rectangle_non_square": ("rectangle_non_square",),
        "rhombus_non_square": ("rhombus_non_square",),
        "parallelogram_only": ("parallelogram_only",),
    }
    return tuple(mapping[str(task_variant)])


def _negative_sampler_names(task_variant: str) -> Tuple[str, ...]:
    """Return likely-negative sampler names for one variant."""

    mapping = {
        "square": ("rectangle_non_square", "rhombus_non_square", "parallelogram_only"),
        "rectangle_non_square": ("square", "rhombus_non_square", "parallelogram_only"),
        "rhombus_non_square": ("square", "rectangle_non_square", "parallelogram_only"),
        "parallelogram_only": ("square", "rectangle_non_square", "rhombus_non_square"),
    }
    return tuple(mapping[str(task_variant)])


def _sample_prototype_by_name(
    rng,
    *,
    sampler_name: str,
    min_extent_units: float,
    max_extent_units: float,
    min_side_gap_units: float,
    min_slant_units: float,
) -> QuadrilateralPrototype:
    """Dispatch one named quadrilateral prototype sampler."""

    if str(sampler_name) == "square":
        return sample_square_prototype(
            rng,
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
        )
    if str(sampler_name) == "rectangle_non_square":
        return sample_rectangle_non_square_prototype(
            rng,
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
            min_side_gap_units=float(min_side_gap_units),
        )
    if str(sampler_name) == "rhombus_non_square":
        return sample_rhombus_non_square_prototype(
            rng,
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
            min_side_gap_units=float(min_side_gap_units),
        )
    if str(sampler_name) == "parallelogram_only":
        return sample_parallelogram_only_prototype(
            rng,
            min_extent_units=float(min_extent_units),
            max_extent_units=float(max_extent_units),
            min_side_gap_units=float(min_side_gap_units),
            min_slant_units=float(min_slant_units),
        )
    raise ValueError(f"unsupported quadrilateral sampler: {sampler_name}")


def _sample_quadrilateral_for_match(
    rng,
    *,
    task_variant: str,
    positive: bool,
    min_extent_units: float,
    max_extent_units: float,
    min_side_gap_units: float,
    min_slant_units: float,
) -> QuadrilateralPrototype:
    """Sample one quadrilateral prototype that either matches or rejects the query class."""

    preferred = (
        _positive_sampler_names(str(task_variant))
        if bool(positive)
        else _negative_sampler_names(str(task_variant))
    )
    fallback = tuple(_SUPPORTED_VARIANTS)
    last_error: Exception | None = None
    for sampler_names in (preferred, fallback):
        for _ in range(500):
            sampler_name = str(rng.choice(list(sampler_names)))
            try:
                prototype = _sample_prototype_by_name(
                    rng,
                    sampler_name=str(sampler_name),
                    min_extent_units=float(min_extent_units),
                    max_extent_units=float(max_extent_units),
                    min_side_gap_units=float(min_side_gap_units),
                    min_slant_units=float(min_slant_units),
                )
            except Exception as exc:
                last_error = exc
                continue
            if bool(_matches_variant(str(prototype.quadrilateral_kind), str(task_variant))) == bool(positive):
                return prototype
    raise RuntimeError("failed to sample quadrilateral prototype for counting scene") from last_error


def _place_quadrilateral_object(
    prototype: QuadrilateralPrototype,
    *,
    label: str,
    slot_units: Tuple[int, int],
    context: GraphSceneContext,
) -> _QuadrilateralSceneObject:
    """Project one centered quadrilateral prototype into pixel space at the requested slot."""

    pixel_vertices = tuple(
        graph_units_to_pixel(
            (float(slot_units[0]) + float(x), float(slot_units[1]) + float(y)),
            origin=context.graph_origin,
            spacing=int(context.graph_spacing),
        )
        for x, y in prototype.local_vertices
    )
    center = graph_units_to_pixel(
        (float(slot_units[0]), float(slot_units[1])),
        origin=context.graph_origin,
        spacing=int(context.graph_spacing),
    )
    return _QuadrilateralSceneObject(
        polygon=PolygonSceneObject(
            label=str(label),
            vertices=tuple((float(point[0]), float(point[1])) for point in pixel_vertices),
            center=(float(center[0]), float(center[1])),
        ),
        quadrilateral_kind=str(prototype.quadrilateral_kind),
        side_lengths=tuple(float(value) for value in prototype.side_lengths),
        angles_degrees=tuple(float(value) for value in prototype.angles_degrees),
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
    min_side_gap_units: float,
    min_slant_units: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw,
    shape_style,
) -> _ScenePayload:
    """Sample and draw one multi-quadrilateral counting scene."""

    from ...shared.geometry_primitives import point_inside_square_canvas

    last_error: Exception | None = None
    for _ in range(600):
        labels = list(assign_counting_labels(rng, object_count=int(object_count)))
        slots = _quadrilateral_slots_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        positives = set(rng.sample(labels, int(target_count)))
        matching_labels: List[str] = []
        objects: List[_QuadrilateralSceneObject] = []
        try:
            for label, slot in zip(labels, slots):
                prototype = _sample_quadrilateral_for_match(
                    rng,
                    task_variant=str(task_variant),
                    positive=str(label) in positives,
                    min_extent_units=float(min_extent_units),
                    max_extent_units=float(max_extent_units),
                    min_side_gap_units=float(min_side_gap_units),
                    min_slant_units=float(min_slant_units),
                )
                if str(label) in positives:
                    matching_labels.append(str(label))
                objects.append(
                    _place_quadrilateral_object(
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
        vertex_padding_px = max(4.0, 0.7 * float(context.graph_spacing) * float(context.scene_scale))
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
    raise RuntimeError("failed to sample quadrilateral-counting scene") from last_error


@register_task
class GeometryCountingQuadrilateralTask:
    """Count how many labeled quadrilaterals belong to one requested class."""

    task_id = "task_geometry_counting_quadrilateral"
    domain = "geometry"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic multi-quadrilateral counting instance."""

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
                    task_variant=str(task_variant),
                    target_count=int(target_count),
                    object_count=int(object_count),
                    context=context_attempt,
                    min_extent_units=float(min_extent_units),
                    max_extent_units=float(max_extent_units),
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
            raise RuntimeError("failed to generate task_geometry_counting_quadrilateral instance") from last_error

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
                "question_text_square",
                "question_text_rectangle_non_square",
                "question_text_rhombus_non_square",
                "question_text_parallelogram_only",
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
            str(obj.polygon.label): {
                "quadrilateral_kind": str(obj.quadrilateral_kind),
            }
            for obj in scene_payload.objects
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_quadrilateral_counting",
                "entities": [
                    {
                        "entity_id": f"quadrilateral_{str(obj.polygon.label)}",
                        "entity_type": "quadrilateral",
                        "attrs": {
                            "label": str(obj.polygon.label),
                            "quadrilateral_kind": str(obj.quadrilateral_kind),
                            "side_lengths": [float(value) for value in obj.side_lengths],
                            "angles_degrees": [float(value) for value in obj.angles_degrees],
                            "vertices": [[float(point[0]), float(point[1])] for point in obj.polygon.vertices],
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "counting_target": "quadrilateral_class",
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
                "counting_class": str(_variant_class_label(str(task_variant))),
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
                "counting_class": str(_variant_class_label(str(task_variant))),
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
