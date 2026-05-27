"""Graph-paper geometry comparison task over multiple labeled angles."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from PIL import ImageDraw
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.comparison_sampling import (
    ComparisonGapMetrics,
    comparison_gap_is_valid,
    compute_comparison_gap_metrics,
)
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.geometry_primitives import Point
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.angle_geometry import primitive_angle_pair_catalog
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.complexity import build_geometry_comparison_complexity
from ..shared.graph_rendering import graph_paper_grid_from_frame
from ..shared.labeled_point_evidence import graph_point_set_evidence_artifacts
from ..shared.multi_angle_scene import (
    AngleSceneObject,
    draw_angle_objects,
    sample_angle_objects_for_targets,
)
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import (
    GeometryShapeStyle,
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import COMPARISON_SHARED_DEFAULTS
from .shared import (
    COMPARISON_ANSWER_LABEL_POOL,
    COMPARISON_QUERY_TYPES,
    apply_balanced_comparison_axes,
    resolve_comparison_object_count,
    resolve_comparison_query_type,
    resolve_comparison_winner_label,
    slot_centers_graph_units,
)

@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for angle-comparison generation."""
    canvas_size_min: int = COMPARISON_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COMPARISON_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = COMPARISON_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = COMPARISON_SHARED_DEFAULTS.graph_cells_max
    line_width: int = COMPARISON_SHARED_DEFAULTS.line_width
    label_offset_px: float = COMPARISON_SHARED_DEFAULTS.label_offset_px
    label_font_size_min: int = COMPARISON_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COMPARISON_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COMPARISON_SHARED_DEFAULTS.label_stroke_width
    object_count_min: int = COMPARISON_SHARED_DEFAULTS.object_count_min
    object_count_max: int = COMPARISON_SHARED_DEFAULTS.object_count_max
    min_angle: int = 30
    max_angle: int = 150
    angle_step: int = 1
    max_catalog_quantization_error_degrees: float = 2.0
    max_abs_vector_component: int = 8
    min_ray_length_units: float = 2.0
    min_normalized_gap: float = COMPARISON_SHARED_DEFAULTS.min_normalized_gap
    min_absolute_gap_degrees: float = 10.0
    object_label_offset_px: float = COMPARISON_SHARED_DEFAULTS.object_label_offset_px

@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one multi-angle comparison instance."""
    query_type: str
    object_count: int
    objects: Tuple[AngleSceneObject, ...]
    winner_metrics: ComparisonGapMetrics
    winner_label: str
    evidence_points_by_label: Dict[str, Point]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]

_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "comparison")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="source_geometry_comparison_angle",
)

def _sample_target_angles(
    rng,
    *,
    candidate_angles: Sequence[int],
    object_count: int,
    query_type: str,
    min_normalized_gap: float,
    min_absolute_gap_degrees: float,
) -> List[int]:
    """Sample distinct target angles whose winner gap is visually meaningful."""
    candidates = [int(value) for value in candidate_angles]
    if len(candidates) < int(object_count):
        raise ValueError("not enough feasible angle candidates for requested object_count")
    for _ in range(800):
        selected = [int(value) for value in rng.sample(candidates, int(object_count))]
        if comparison_gap_is_valid(
            [float(value) for value in selected],
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap_degrees),
        ):
            return selected
    raise ValueError("failed to sample comparison angles with the configured gap rule")
def _sample_scene(
    rng,
    *,
    winner_label: str,
    context: GraphSceneContext,
    query_type: str,
    object_count: int,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_catalog_quantization_error_degrees: float,
    max_abs_vector_component: int,
    min_ray_length_units: float,
    min_normalized_gap: float,
    min_absolute_gap_degrees: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw: ImageDraw.ImageDraw,
    shape_style: GeometryShapeStyle,
) -> _ScenePayload:
    """Sample and draw one multi-angle comparison scene."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(max_catalog_quantization_error_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    candidate_angles = [int(value) for value in sorted(catalog.keys())]
    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    last_error: Exception | None = None
    for _ in range(700):
        labels = [str(label) for label in COMPARISON_ANSWER_LABEL_POOL if str(label) != str(winner_label)]
        rng.shuffle(labels)
        selected_labels = [str(winner_label), *labels[: max(0, int(object_count) - 1)]]
        rng.shuffle(selected_labels)
        slots = slot_centers_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        sampled_target_angles = _sample_target_angles(
            rng,
            candidate_angles=candidate_angles,
            object_count=int(object_count),
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap_degrees=float(min_absolute_gap_degrees),
        )
        winner_target_angle = (
            int(max(sampled_target_angles))
            if str(query_type) == "largest"
            else int(min(sampled_target_angles))
        )
        other_target_angles = [
            int(value)
            for value in sampled_target_angles
            if int(value) != int(winner_target_angle)
        ]
        rng.shuffle(other_target_angles)
        objects: Tuple[AngleSceneObject, ...] | None = None
        try:
            target_angles = [
                (
                    int(winner_target_angle)
                    if str(label) == str(winner_label)
                    else int(other_target_angles.pop())
                )
                for label in selected_labels
            ]
            objects = sample_angle_objects_for_targets(
                rng,
                labels=selected_labels,
                target_angles=target_angles,
                slot_units=slots,
                context=context,
                angle_catalog=catalog,
            )
        except Exception as exc:
            last_error = exc
            continue
        raw_values = [float(obj.raw_angle_degrees) for obj in objects]
        metrics = compute_comparison_gap_metrics(raw_values, query_type=str(query_type))
        if str(objects[int(metrics.winner_index)].label) != str(winner_label):
            continue
        if not comparison_gap_is_valid(
            raw_values,
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap_degrees),
        ):
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
        winner = objects[int(metrics.winner_index)]
        return _ScenePayload(
            query_type=str(query_type),
            object_count=int(object_count),
            objects=objects,
            winner_metrics=metrics,
            winner_label=str(winner.label),
            evidence_points_by_label={
                "ray_a": (float(winner.point_a[0]), float(winner.point_a[1])),
                "vertex": (float(winner.vertex[0]), float(winner.vertex[1])),
                "ray_b": (float(winner.point_b[0]), float(winner.point_b[1])),
            },
            object_label_centers=label_centers,
            render_anchor={
                "winner_label": str(winner.label),
                "winner_vertex": [float(winner.vertex[0]), float(winner.vertex[1])],
            },
        )
    raise RuntimeError("failed to sample angle-comparison scene") from last_error

class GeometryComparisonAngleTask:
    """Compare multiple labeled angles and choose the largest/smallest one."""
    task_id = "source_geometry_comparison_angle"
    domain = "geometry"
    task_group = "comparison"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic multi-angle comparison instance."""
        scene_rng = spawn_rng(int(instance_seed), "scene")
        query_type, query_type_probabilities = resolve_comparison_query_type(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
        )
        object_count, object_count_probabilities = resolve_comparison_object_count(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_min=_DEFAULTS.object_count_min,
            fallback_max=_DEFAULTS.object_count_max,
        )
        winner_label, winner_label_probabilities = resolve_comparison_winner_label(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            label_pool=COMPARISON_ANSWER_LABEL_POOL,
        )
        query_type, query_type_probabilities, object_count, object_count_probabilities = apply_balanced_comparison_axes(
            instance_seed=int(instance_seed),
            params=params,
            query_type=str(query_type),
            query_type_probabilities=query_type_probabilities,
            object_count=int(object_count),
            object_count_probabilities=object_count_probabilities,
            query_types=COMPARISON_QUERY_TYPES,
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
        min_normalized_gap = float(
            params.get(
                "min_normalized_gap",
                group_default(_GEN_DEFAULTS, "min_normalized_gap", _DEFAULTS.min_normalized_gap),
            )
        )
        min_absolute_gap_degrees = float(
            params.get(
                "min_absolute_gap_degrees",
                group_default(_GEN_DEFAULTS, "min_absolute_gap_degrees", _DEFAULTS.min_absolute_gap_degrees),
            )
        )
        if int(min_angle) >= int(max_angle):
            raise ValueError("min_angle must be < max_angle for comparison angle task")
        if int(angle_step) <= 0:
            raise ValueError("angle_step must be > 0")
        if float(min_ray_length_units) <= 0.0:
            raise ValueError("min_ray_length_units must be > 0")
        if float(min_normalized_gap) < 0.0:
            raise ValueError("min_normalized_gap must be >= 0")
        if float(min_absolute_gap_degrees) < 0.0:
            raise ValueError("min_absolute_gap_degrees must be >= 0")
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
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                fallback_canvas_min=_DEFAULTS.canvas_size_min,
                fallback_canvas_max=_DEFAULTS.canvas_size_max,
                fallback_cells_min=_DEFAULTS.graph_cells_min,
                fallback_cells_max=_DEFAULTS.graph_cells_max,
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
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
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
                    winner_label=str(winner_label),
                    context=context_attempt,
                    query_type=str(query_type),
                    object_count=int(object_count),
                    min_angle=int(min_angle),
                    max_angle=int(max_angle),
                    angle_step=int(angle_step),
                    max_catalog_quantization_error_degrees=float(max_catalog_quantization_error),
                    max_abs_vector_component=int(max_abs_vector_component),
                    min_ray_length_units=float(min_ray_length_units),
                    min_normalized_gap=float(min_normalized_gap),
                    min_absolute_gap_degrees=float(min_absolute_gap_degrees),
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
            raise RuntimeError("failed to generate source_geometry_comparison_angle instance") from last_error
        evidence = graph_point_set_evidence_artifacts(
            points_by_label=scene_payload.evidence_points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="winning_angle_triplet",
            ordered_labels=("ray_a", "vertex", "ray_b"),
        )
        evidence_value = evidence.get("evidence_value", [])
        if (
            not isinstance(evidence_value, list)
            or len(evidence_value) != 3
            or any(not isinstance(point, list) or len(point) != 2 for point in evidence_value)
            or any(not isinstance(coord, (int, float)) for point in evidence_value for coord in point)
        ):
            raise RuntimeError("comparison-angle evidence must include three pixel points")
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_largest",
                "question_text_smallest",
                "evidence_hint",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text_key = "question_text_largest" if str(query_type) == "largest" else "question_text_smallest"
        question_text = str(prompt_defaults[str(question_text_key)])
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=evidence_value,
            answer_type="option_letter",
        )
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
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        winner_label = str(scene_payload.winner_label)
        answer_gt = TypedValue(type="option_letter", value=str(winner_label))
        evidence_gt = TypedValue(type=str(evidence["evidence_type"]), value=list(evidence_value))
        values_by_label = {
            str(obj.label): round(float(obj.raw_angle_degrees), 6)
            for obj in scene_payload.objects
        }
        query_params = {
            "query_type": str(query_type),
            "query_type_probabilities": dict(query_type_probabilities),
            "object_count": int(object_count),
            "object_count_probabilities": dict(object_count_probabilities),
            "winner_label": str(winner_label),
            "winner_label_probabilities": dict(winner_label_probabilities),
            "min_angle": int(min_angle),
            "max_angle": int(max_angle),
            "angle_step": int(angle_step),
            "min_normalized_gap": float(min_normalized_gap),
            "min_absolute_gap_degrees": float(min_absolute_gap_degrees),
            "max_abs_vector_component": int(max_abs_vector_component),
            "min_ray_length_units": float(min_ray_length_units),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_angle_comparison",
                "entities": [
                    {
                        "entity_id": f"angle_{str(obj.label)}",
                        "entity_type": "angle",
                        "attrs": {
                            "label": str(obj.label),
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
                    "comparison_target": "angle_measure",
                    "query_type": str(query_type),
                    "winner_label": str(winner_label),
                },
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
                "query_id": "primitive_angle_set",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
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
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
                **dict(context.graph_layout_metadata),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {"winner": dict(scene_payload.render_anchor)},
                "object_label_centers": dict(scene_payload.object_label_centers),
            },
            "execution_trace": {
                "scene_variant": "primitive_angle_set",
                "query_type": str(query_type),
                "query_type_probabilities": dict(query_type_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "winner_label_target": str(winner_label),
                "winner_label_probabilities": dict(winner_label_probabilities),
                "object_labels": [str(obj.label) for obj in scene_payload.objects],
                "values_by_label": dict(values_by_label),
                "winner_label": str(winner_label),
                "winner_value": float(scene_payload.winner_metrics.winner_value),
                "runner_up_value": float(scene_payload.winner_metrics.runner_up_value),
                "winner_gap_abs": float(scene_payload.winner_metrics.gap_abs),
                "winner_gap_normalized": float(scene_payload.winner_metrics.gap_normalized),
                "required_evidence_labels": ["ray_a", "vertex", "ray_b"],
                "question_format": "label_choice_no_text_options",
            },
            "witness_symbolic": {
                **dict(evidence["witness_symbolic"]),
                "winner_label": str(winner_label),
            },
            "projected_evidence": dict(evidence["projected_evidence"]),
        }
        complexity = build_geometry_comparison_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(object_count),
            object_count_min=int(_GEN_DEFAULTS["object_count_min"]),
            object_count_max=int(_GEN_DEFAULTS["object_count_max"]),
            gap_normalized=float(scene_payload.winner_metrics.gap_normalized),
            min_normalized_gap=float(_GEN_DEFAULTS["min_normalized_gap"]),
            comparison_kind="angle",
            evidence_point_count=3,
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
            query_id="primitive_angle_set",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
