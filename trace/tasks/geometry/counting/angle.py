"""Non-grid geometry counting task over multiple labeled angles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

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
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.angle_geometry import primitive_angle_pair_catalog
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_counting_complexity
from ..shared.graph_rendering import graph_units_to_pixel
from ..shared.multi_angle_scene import (
    AngleSceneObject,
    draw_angle_objects,
    sample_angle_objects_for_targets,
)
from ..shared.noise_defaults import load_geometry_noise_defaults
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
    resolve_counting_object_count,
    resolve_counting_target_count,
)

_SUPPORTED_VARIANTS: Tuple[str, ...] = ("acute_angle", "right_angle", "obtuse_angle")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for angle-counting generation."""

    canvas_size_min: int = COUNTING_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COUNTING_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = COUNTING_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = COUNTING_SHARED_DEFAULTS.graph_cells_max
    line_width: int = COUNTING_SHARED_DEFAULTS.line_width
    label_font_size_min: int = COUNTING_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COUNTING_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COUNTING_SHARED_DEFAULTS.label_stroke_width
    object_label_offset_px: float = COUNTING_SHARED_DEFAULTS.object_label_offset_px
    object_count_min: int = COUNTING_SHARED_DEFAULTS.object_count_min
    object_count_max: int = COUNTING_SHARED_DEFAULTS.object_count_max
    min_angle: int = 25
    max_angle: int = 155
    angle_step: int = 1
    max_catalog_quantization_error_degrees: float = 2.0
    max_abs_vector_component: int = 8
    min_ray_length_units: float = 2.0
    boundary_margin_degrees: float = 10.0


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one multi-angle counting instance."""

    task_variant: str
    object_count: int
    target_count: int
    objects: Tuple[AngleSceneObject, ...]
    matching_labels: Tuple[str, ...]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_counting_angle",
)
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="counting")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="counting")


def _angle_slots_graph_units(*, object_count: int, graph_cells: int, rng) -> List[Tuple[int, int]]:
    """Return a roomier hidden-grid slot bank for 6-10 angle objects."""

    half_span = max(10, int(graph_cells // 2))
    outer_x = max(5, min(int(round(float(half_span) * 0.72)), int(half_span - 3)))
    inner_x = max(2, min(int(round(float(half_span) * 0.36)), max(2, int(outer_x - 2))))
    row_y = max(4, min(int(round(float(half_span) * 0.45)), int(half_span - 3)))
    base_slots = [
        (-int(outer_x), int(row_y)),
        (-int(inner_x), int(row_y)),
        (0, int(row_y)),
        (int(inner_x), int(row_y)),
        (int(outer_x), int(row_y)),
        (-int(outer_x), -int(row_y)),
        (-int(inner_x), -int(row_y)),
        (0, -int(row_y)),
        (int(inner_x), -int(row_y)),
        (int(outer_x), -int(row_y)),
    ]
    rng.shuffle(base_slots)
    return list(base_slots[: int(object_count)])


def _variant_candidate_angles(
    *,
    candidate_angles: Sequence[int],
    task_variant: str,
    boundary_margin_degrees: float,
) -> Tuple[List[int], List[int]]:
    """Return positive and negative angle targets for one queried class."""

    margin = float(boundary_margin_degrees)
    acute = [int(value) for value in candidate_angles if float(value) <= 90.0 - float(margin)]
    right = [int(value) for value in candidate_angles if int(value) == 90]
    obtuse = [int(value) for value in candidate_angles if float(value) >= 90.0 + float(margin)]
    if str(task_variant) == "acute_angle":
        return acute, [*right, *obtuse]
    if str(task_variant) == "right_angle":
        return right, [*acute, *obtuse]
    if str(task_variant) == "obtuse_angle":
        return obtuse, [*acute, *right]
    raise ValueError(f"unsupported task_variant: {task_variant}")


def _sample_angle_targets(rng, *, candidates: Sequence[int], count: int) -> List[int]:
    """Sample one deterministic multiset of angle targets."""

    if int(count) < 0:
        raise ValueError("count must be >= 0")
    values = [int(value) for value in candidates]
    if int(count) == 0:
        return []
    if not values:
        raise ValueError("cannot sample from an empty candidate set")
    if int(count) <= len(values):
        return [int(value) for value in rng.sample(values, int(count))]
    return [int(rng.choice(values)) for _ in range(int(count))]


def _variant_class_label(task_variant: str) -> str:
    """Return one normalized human-readable class label."""

    mapping = {
        "acute_angle": "acute",
        "right_angle": "right",
        "obtuse_angle": "obtuse",
    }
    return str(mapping[str(task_variant)])


def _sample_scene(
    rng,
    *,
    task_variant: str,
    target_count: int,
    object_count: int,
    context: GraphSceneContext,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_catalog_quantization_error_degrees: float,
    max_abs_vector_component: int,
    min_ray_length_units: float,
    boundary_margin_degrees: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw,
    shape_style,
) -> _ScenePayload:
    """Sample and draw one multi-angle counting scene."""

    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(max_catalog_quantization_error_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    candidate_angles = [int(value) for value in sorted(catalog.keys())]
    positive_angles, negative_angles = _variant_candidate_angles(
        candidate_angles=candidate_angles,
        task_variant=str(task_variant),
        boundary_margin_degrees=float(boundary_margin_degrees),
    )
    if not positive_angles:
        raise ValueError(f"no positive angle targets available for {task_variant}")
    if not negative_angles:
        raise ValueError(f"no negative angle targets available for {task_variant}")

    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    last_error: Exception | None = None
    for _ in range(700):
        labels = list(assign_counting_labels(rng, object_count=int(object_count)))
        slots = _angle_slots_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        positives = set(rng.sample(labels, int(target_count)))
        target_angles: List[int] = []
        matching_labels: List[str] = []
        positive_targets = _sample_angle_targets(rng, candidates=positive_angles, count=int(target_count))
        negative_targets = _sample_angle_targets(
            rng,
            candidates=negative_angles,
            count=int(object_count) - int(target_count),
        )
        for label in labels:
            if str(label) in positives:
                matching_labels.append(str(label))
                target_angles.append(int(positive_targets.pop()))
            else:
                target_angles.append(int(negative_targets.pop()))
        try:
            objects = sample_angle_objects_for_targets(
                rng,
                labels=labels,
                target_angles=target_angles,
                slot_units=slots,
                context=context,
                angle_catalog=catalog,
            )
        except Exception as exc:
            last_error = exc
            continue

        label_centers = draw_angle_objects(
            draw,
            objects=objects,
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
            objects=objects,
            matching_labels=matching_labels_sorted,
            object_label_centers=label_centers,
            render_anchor={
                "matching_labels": list(matching_labels_sorted),
                "task_variant": str(task_variant),
            },
        )

    raise RuntimeError("failed to sample angle-counting scene") from last_error


@register_task
class GeometryCountingAngleTask:
    """Count how many labeled angles belong to one requested class."""

    task_id = "task_geometry_counting_angle"
    domain = "geometry"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic multi-angle counting instance."""

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
        object_count, object_count_probabilities = resolve_counting_object_count(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_min=_DEFAULTS.object_count_min,
            fallback_max=_DEFAULTS.object_count_max,
        )
        target_count, target_count_probabilities = resolve_counting_target_count(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            object_count=int(object_count),
        )

        min_angle = int(params.get("min_angle", group_default(_GEN_DEFAULTS, "min_angle", _DEFAULTS.min_angle)))
        max_angle = int(params.get("max_angle", group_default(_GEN_DEFAULTS, "max_angle", _DEFAULTS.max_angle)))
        angle_step = int(params.get("angle_step", group_default(_GEN_DEFAULTS, "angle_step", _DEFAULTS.angle_step)))
        max_catalog_quantization_error = float(
            params.get(
                "max_catalog_quantization_error_degrees",
                group_default(
                    _GEN_DEFAULTS,
                    "max_catalog_quantization_error_degrees",
                    _DEFAULTS.max_catalog_quantization_error_degrees,
                ),
            )
        )
        max_abs_vector_component = int(
            params.get(
                "max_abs_vector_component",
                group_default(_GEN_DEFAULTS, "max_abs_vector_component", _DEFAULTS.max_abs_vector_component),
            )
        )
        min_ray_length_units = float(
            params.get(
                "min_ray_length_units",
                group_default(_GEN_DEFAULTS, "min_ray_length_units", _DEFAULTS.min_ray_length_units),
            )
        )
        boundary_margin_degrees = float(
            params.get(
                "boundary_margin_degrees",
                group_default(_GEN_DEFAULTS, "boundary_margin_degrees", _DEFAULTS.boundary_margin_degrees),
            )
        )
        if int(min_angle) >= int(max_angle):
            raise ValueError("min_angle must be < max_angle for counting angle task")
        if int(angle_step) <= 0:
            raise ValueError("angle_step must be > 0")
        if float(min_ray_length_units) <= 0.0:
            raise ValueError("min_ray_length_units must be > 0")
        if float(boundary_margin_degrees) < 0.0:
            raise ValueError("boundary_margin_degrees must be >= 0")

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
                        min_px=int(
                            group_default(
                                _RENDER_DEFAULTS,
                                "label_font_size_min",
                                _DEFAULTS.label_font_size_min,
                            )
                        ),
                        max_px=int(
                            group_default(
                                _RENDER_DEFAULTS,
                                "label_font_size_max",
                                _DEFAULTS.label_font_size_max,
                            )
                        ),
                    ),
                )
            )
            if int(label_font_size_px_attempt) < 6:
                raise ValueError("label_font_size_px must be >= 6")
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
                    task_variant=str(task_variant),
                    target_count=int(target_count),
                    object_count=int(object_count),
                    context=context_attempt,
                    min_angle=int(min_angle),
                    max_angle=int(max_angle),
                    angle_step=int(angle_step),
                    max_catalog_quantization_error_degrees=float(max_catalog_quantization_error),
                    max_abs_vector_component=int(max_abs_vector_component),
                    min_ray_length_units=float(min_ray_length_units),
                    boundary_margin_degrees=float(boundary_margin_degrees),
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
            raise RuntimeError("failed to generate task_geometry_counting_angle instance") from last_error

        evidence_value = list(scene_payload.matching_labels)
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
                "question_text_acute_angle",
                "question_text_right_angle",
                "question_text_obtuse_angle",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(prompt_defaults[f"question_text_{str(task_variant)}"])
        json_example = str(prompt_defaults["json_example"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only"])
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
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(scene_payload.target_count)
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_value))

        angle_class = _variant_class_label(str(task_variant))
        class_by_label = {
            str(obj.label): (
                "right"
                if int(obj.target_angle_degrees) == 90
                else "acute"
                if int(obj.target_angle_degrees) < 90
                else "obtuse"
            )
            for obj in scene_payload.objects
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_angle_counting",
                "entities": [
                    {
                        "entity_id": f"angle_{str(obj.label)}",
                        "entity_type": "angle",
                        "attrs": {
                            "label": str(obj.label),
                            "angle_class": str(class_by_label[str(obj.label)]),
                            "target_angle_degrees": int(obj.target_angle_degrees),
                            "raw_angle_degrees": float(obj.raw_angle_degrees),
                            "points": {
                                "arm_a": [float(obj.point_a[0]), float(obj.point_a[1])],
                                "vertex": [float(obj.vertex[0]), float(obj.vertex[1])],
                                "arm_b": [float(obj.point_b[0]), float(obj.point_b[1])],
                            },
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "counting_target": "angle_class",
                    "task_variant": str(task_variant),
                    "matching_labels": list(scene_payload.matching_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "layout_graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
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
                    "min_angle": int(min_angle),
                    "max_angle": int(max_angle),
                    "angle_step": int(angle_step),
                    "boundary_margin_degrees": float(boundary_margin_degrees),
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
                "counting_class": str(angle_class),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "object_labels": [str(obj.label) for obj in scene_payload.objects],
                "matching_labels": list(scene_payload.matching_labels),
                "class_by_label": dict(class_by_label),
                "question_format": "count_matching_labeled_objects",
            },
            "witness_symbolic": {
                "counting_class": str(angle_class),
                "matching_labels": list(scene_payload.matching_labels),
            },
            "projected_evidence": {
                "label_set": list(scene_payload.matching_labels),
            },
        }

        complexity = build_geometry_counting_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(object_count),
            object_count_min=int(_GEN_DEFAULTS["object_count_min"]),
            object_count_max=int(_GEN_DEFAULTS["object_count_max"]),
            target_count=int(target_count),
            task_kind="angle",
            task_variant=str(task_variant),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
