"""Graph-paper geometry comparison task over multiple labeled polygons."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Mapping
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
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.complexity import build_geometry_comparison_complexity
from ..shared.graph_rendering import graph_paper_grid_from_frame
from ..shared.labeled_point_annotation import graph_point_set_annotation_artifacts
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import COMPARISON_SHARED_DEFAULTS
from .rectangle_scene import RectangleComparisonScenePayload, sample_rectangle_comparison_scene
from .shared import (
    COMPARISON_ANSWER_LABEL_POOL,
    COMPARISON_QUERY_TYPES,
    apply_balanced_comparison_axes,
    resolve_comparison_object_count,
    resolve_comparison_query_type,
    resolve_comparison_winner_label,
    resolve_region_shape_family,
    trace_numeric_value,
)
from .triangle_scene import TriangleComparisonScenePayload, sample_triangle_comparison_scene

@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for perimeter-comparison generation."""
    canvas_size_min: int = COMPARISON_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COMPARISON_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = COMPARISON_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = COMPARISON_SHARED_DEFAULTS.graph_cells_max
    line_width: int = COMPARISON_SHARED_DEFAULTS.line_width
    label_font_size_min: int = COMPARISON_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COMPARISON_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COMPARISON_SHARED_DEFAULTS.label_stroke_width
    object_count_min: int = COMPARISON_SHARED_DEFAULTS.object_count_min
    object_count_max: int = COMPARISON_SHARED_DEFAULTS.object_count_max
    min_normalized_gap: float = COMPARISON_SHARED_DEFAULTS.min_normalized_gap
    object_label_offset_px: float = COMPARISON_SHARED_DEFAULTS.object_label_offset_px
    min_rectangle_width: int = 2
    max_rectangle_width: int = 6
    min_rectangle_height: int = 2
    max_rectangle_height: int = 6
    min_absolute_gap_units: float = 4.0
    min_triangle_base: int = 2
    max_triangle_base: int = 6
    min_triangle_height: int = 2
    max_triangle_height: int = 6
    min_absolute_triangle_perimeter_gap_units: float = 3.0

_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "comparison")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="source_geometry_comparison_perimeter",
)

class GeometryComparisonPerimeterTask:
    """Compare multiple labeled polygons and choose the largest/smallest perimeter."""
    task_id = "source_geometry_comparison_perimeter"
    domain = "geometry"
    task_group = "comparison"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic multi-polygon comparison instance."""
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
        shape_family = resolve_region_shape_family(params)
        min_rectangle_width = int(
            params.get(
                "min_rectangle_width",
                group_default(_GEN_DEFAULTS, "min_rectangle_width", _DEFAULTS.min_rectangle_width),
            )
        )
        max_rectangle_width = int(
            params.get(
                "max_rectangle_width",
                group_default(_GEN_DEFAULTS, "max_rectangle_width", _DEFAULTS.max_rectangle_width),
            )
        )
        min_rectangle_height = int(
            params.get(
                "min_rectangle_height",
                group_default(_GEN_DEFAULTS, "min_rectangle_height", _DEFAULTS.min_rectangle_height),
            )
        )
        max_rectangle_height = int(
            params.get(
                "max_rectangle_height",
                group_default(_GEN_DEFAULTS, "max_rectangle_height", _DEFAULTS.max_rectangle_height),
            )
        )
        min_normalized_gap = float(
            params.get(
                "min_normalized_gap",
                group_default(_GEN_DEFAULTS, "min_normalized_gap", _DEFAULTS.min_normalized_gap),
            )
        )
        min_absolute_gap_units = float(
            params.get(
                "min_absolute_gap_units",
                group_default(_GEN_DEFAULTS, "min_absolute_gap_units", _DEFAULTS.min_absolute_gap_units),
            )
        )
        min_triangle_base = int(
            params.get(
                "min_triangle_base",
                group_default(_GEN_DEFAULTS, "min_triangle_base", _DEFAULTS.min_triangle_base),
            )
        )
        max_triangle_base = int(
            params.get(
                "max_triangle_base",
                group_default(_GEN_DEFAULTS, "max_triangle_base", _DEFAULTS.max_triangle_base),
            )
        )
        min_triangle_height = int(
            params.get(
                "min_triangle_height",
                group_default(_GEN_DEFAULTS, "min_triangle_height", _DEFAULTS.min_triangle_height),
            )
        )
        max_triangle_height = int(
            params.get(
                "max_triangle_height",
                group_default(_GEN_DEFAULTS, "max_triangle_height", _DEFAULTS.max_triangle_height),
            )
        )
        min_absolute_triangle_perimeter_gap_units = float(
            params.get(
                "min_absolute_triangle_perimeter_gap_units",
                group_default(
                    _GEN_DEFAULTS,
                    "min_absolute_triangle_perimeter_gap_units",
                    _DEFAULTS.min_absolute_triangle_perimeter_gap_units,
                ),
            )
        )
        if int(min_rectangle_width) >= int(max_rectangle_width):
            raise ValueError("min_rectangle_width must be < max_rectangle_width for comparison perimeter task")
        if int(min_rectangle_height) >= int(max_rectangle_height):
            raise ValueError("min_rectangle_height must be < max_rectangle_height for comparison perimeter task")
        if int(min_triangle_base) >= int(max_triangle_base):
            raise ValueError("min_triangle_base must be < max_triangle_base for comparison perimeter task")
        if int(min_triangle_height) >= int(max_triangle_height):
            raise ValueError("min_triangle_height must be < max_triangle_height for comparison perimeter task")
        if float(min_normalized_gap) < 0.0:
            raise ValueError("min_normalized_gap must be >= 0")
        if float(min_absolute_gap_units) < 0.0:
            raise ValueError("min_absolute_gap_units must be >= 0")
        if float(min_absolute_triangle_perimeter_gap_units) < 0.0:
            raise ValueError("min_absolute_triangle_perimeter_gap_units must be >= 0")
        context_params = dict(params)
        context = None
        image = None
        background_meta = None
        shape_style = None
        label_font_size_px = None
        label_stroke_width_scene = None
        line_width = None
        scene_payload: RectangleComparisonScenePayload | TriangleComparisonScenePayload | None = None
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
                        min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                        max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
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
                if str(shape_family) == "triangle":
                    scene_payload_attempt = sample_triangle_comparison_scene(
                        scene_rng,
                        winner_label=str(winner_label),
                        context=context_attempt,
                        query_type=str(query_type),
                        object_count=int(object_count),
                        metric_kind="perimeter_units",
                        min_triangle_base=int(min_triangle_base),
                        max_triangle_base=int(max_triangle_base),
                        min_triangle_height=int(min_triangle_height),
                        max_triangle_height=int(max_triangle_height),
                        min_normalized_gap=float(min_normalized_gap),
                        min_absolute_gap=float(min_absolute_triangle_perimeter_gap_units),
                        line_width=int(line_width_attempt),
                        label_font_size_px=int(label_font_size_px_attempt),
                        label_stroke_width=int(label_stroke_width_scene_attempt),
                        object_label_offset_px=float(object_label_offset_px),
                        draw=draw_attempt,
                        shape_style=shape_style_attempt,
                    )
                else:
                    scene_payload_attempt = sample_rectangle_comparison_scene(
                        scene_rng,
                        winner_label=str(winner_label),
                        context=context_attempt,
                        query_type=str(query_type),
                        object_count=int(object_count),
                        metric_kind="perimeter_units",
                        min_rectangle_width=int(min_rectangle_width),
                        max_rectangle_width=int(max_rectangle_width),
                        min_rectangle_height=int(min_rectangle_height),
                        max_rectangle_height=int(max_rectangle_height),
                        min_normalized_gap=float(min_normalized_gap),
                        min_absolute_gap=float(min_absolute_gap_units),
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
            raise RuntimeError("failed to generate source_geometry_comparison_perimeter instance") from last_error
        ordered_annotation_labels = (
            ("vertex_1", "vertex_2", "vertex_3")
            if str(shape_family) == "triangle"
            else ("vertex_1", "vertex_2", "vertex_3", "vertex_4")
        )
        annotation_point_count = len(ordered_annotation_labels)
        annotation = graph_point_set_annotation_artifacts(
            points_by_label=scene_payload.annotation_points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type=f"winning_{shape_family}_vertices",
            ordered_labels=ordered_annotation_labels,
        )
        annotation_value = annotation.get("annotation_value", [])
        if (
            not isinstance(annotation_value, list)
            or len(annotation_value) != int(annotation_point_count)
            or any(not isinstance(point, list) or len(point) != 2 for point in annotation_value)
            or any(not isinstance(coord, (int, float)) for point in annotation_value for coord in point)
        ):
            raise RuntimeError("comparison-perimeter annotation must include pixel polygon vertices")
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
                "object_description_triangle",
                "question_text_largest_triangle",
                "question_text_smallest_triangle",
                "annotation_hint",
                "annotation_hint_triangle",
                "answer_hint",
                "answer_hint_triangle",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text_key = "question_text_largest" if str(query_type) == "largest" else "question_text_smallest"
        shape_question_text_key = f"{question_text_key}_{shape_family}"
        question_text = str(prompt_defaults.get(str(shape_question_text_key), prompt_defaults[str(question_text_key)]))
        object_description = str(
            prompt_defaults.get(f"object_description_{shape_family}", prompt_defaults["object_description"])
        )
        annotation_hint = str(prompt_defaults.get(f"annotation_hint_{shape_family}", prompt_defaults["annotation_hint"]))
        answer_hint = str(prompt_defaults.get(f"answer_hint_{shape_family}", prompt_defaults["answer_hint"]))
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=annotation_value,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        winner_label = str(scene_payload.winner_label)
        answer_gt = TypedValue(type="option_letter", value=str(winner_label))
        annotation_gt = TypedValue(type=str(annotation["annotation_type"]), value=list(annotation_value))
        scene_variant_name = f"{shape_family}_set"
        values_by_label = {
            str(obj.label): trace_numeric_value(float(obj.perimeter_units)) for obj in scene_payload.objects
        }
        query_params = {
            "shape_family": str(shape_family),
            "query_type": str(query_type),
            "query_type_probabilities": dict(query_type_probabilities),
            "object_count": int(object_count),
            "object_count_probabilities": dict(object_count_probabilities),
            "winner_label": str(winner_label),
            "winner_label_probabilities": dict(winner_label_probabilities),
            "min_normalized_gap": float(min_normalized_gap),
        }
        if str(shape_family) == "triangle":
            query_params.update(
                {
                    "min_triangle_base": int(min_triangle_base),
                    "max_triangle_base": int(max_triangle_base),
                    "min_triangle_height": int(min_triangle_height),
                    "max_triangle_height": int(max_triangle_height),
                    "min_absolute_gap_units": float(min_absolute_triangle_perimeter_gap_units),
                }
            )
        else:
            query_params.update(
                {
                    "min_rectangle_width": int(min_rectangle_width),
                    "max_rectangle_width": int(max_rectangle_width),
                    "min_rectangle_height": int(min_rectangle_height),
                    "max_rectangle_height": int(max_rectangle_height),
                    "min_absolute_gap_units": float(min_absolute_gap_units),
                }
            )
        entities = []
        for obj in scene_payload.objects:
            attrs = {
                "label": str(obj.label),
                "shape_family": str(shape_family),
                "area_square_units": trace_numeric_value(float(obj.area_square_units)),
                "perimeter_units": trace_numeric_value(float(obj.perimeter_units)),
                "vertices": [[float(point[0]), float(point[1])] for point in obj.vertices],
            }
            if str(shape_family) == "triangle":
                attrs.update(
                    {
                        "base_units": int(obj.base_units),
                        "height_units": int(obj.height_units),
                        "hypotenuse_units": trace_numeric_value(float(obj.hypotenuse_units)),
                    }
                )
            else:
                attrs.update(
                    {
                        "width_units": int(obj.width_units),
                        "height_units": int(obj.height_units),
                    }
                )
            entities.append(
                {
                    "entity_id": f"{shape_family}_{str(obj.label)}",
                    "entity_type": "polygon",
                    "attrs": attrs,
                }
            )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_perimeter_comparison",
                "entities": list(entities),
                "relations": {
                    "comparison_target": "perimeter_units",
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
                "query_id": str(scene_variant_name),
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
                "scene_variant": str(scene_variant_name),
                "shape_family": str(shape_family),
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
                "required_annotation_labels": list(ordered_annotation_labels),
                "question_format": "label_choice_no_text_options",
            },
            "witness_symbolic": {
                **dict(annotation["witness_symbolic"]),
                "winner_label": str(winner_label),
            },
            "projected_annotation": dict(annotation["projected_annotation"]),
        }
        complexity = build_geometry_comparison_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(object_count),
            object_count_min=int(_GEN_DEFAULTS["object_count_min"]),
            object_count_max=int(_GEN_DEFAULTS["object_count_max"]),
            gap_normalized=float(scene_payload.winner_metrics.gap_normalized),
            min_normalized_gap=float(_GEN_DEFAULTS["min_normalized_gap"]),
            comparison_kind="perimeter",
            annotation_point_count=int(annotation_point_count),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(scene_variant_name),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
