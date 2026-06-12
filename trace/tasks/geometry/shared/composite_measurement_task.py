"""Analytical measurement geometry value tasks.

The render helpers in this module are shared by several public scene grammars:
angle relations, parallel sections, Pythagorean length constructions, triangle
special segments, and rectilinear composite shapes. Public annotation is image
level annotation over the minimal visible primitives needed for each scene
contract; visible text annotations stay in render metadata unless the task is
explicitly a readout task.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
    render_scene_prompt_variants,
)
from ...shared.text_rendering import load_font
from .annotation_values import (
    bbox_set_annotation_artifacts,
    keyed_bbox_annotation_artifacts,
    keyed_point_annotation_artifacts,
)
from .diagram_style import (
    geometry_diagram_style_metadata,
    geometry_shape_style_from_diagram_style,
    prepare_geometry_diagram_style_and_background,
)
from trace.tasks.shared.fixed_query import geometry_probability_map as _geometry_probability_map
from .metadata_serialization import geometry_json_ready
from .scene_transform import LazySceneTransform
from .shape_style import extract_background_anchor_colors, sample_geometry_shape_style

from .composite_measurement_cases import (
    SCENE_ID,
    _COMPOSITE_MEASUREMENT_BACKGROUND_DEFAULTS,
    _COMPOSITE_MEASUREMENT_NOISE_DEFAULTS,
    _MeasurementCase,
    _RenderContext,
    _RenderedCompositeScene,
    _SCENE_DEFAULTS,
    _prompt_examples,
)

class _CompositeMeasurementBaseTask:
    """Shared implementation for one public analytical measurement value task."""

    domain = "geometry"
    default_dataset_enabled = True
    public_scene_id = ""
    scene_id = ""
    scene_kind = "geometry_analytical_measurement"
    witness_type = "analytical_measurement_geometry_value"
    cases: Sequence[_MeasurementCase] = ()
    reasoning_kind = "measurement"
    defaults_map: Mapping[str, Any] = _SCENE_DEFAULTS
    defaults_are_scene_aligned = False
    prompts_are_scene_aligned = False

    def _defaults_for_task(self) -> Mapping[str, Any]:
        return self.defaults_map

    def _split_defaults(self) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        defaults = self._defaults_for_task()
        if bool(self.defaults_are_scene_aligned):
            return split_scene_generation_rendering_prompt_defaults(
                defaults,
                task_id=str(self.task_id),
            )
        return split_scene_generation_rendering_prompt_defaults(
            defaults,
            task_id=str(self.task_id),
        )

    def _select_case(self, instance_seed: int, params: Mapping[str, Any]) -> tuple[_MeasurementCase, Dict[str, float]]:
        if not self.cases:
            raise ValueError(f"{self.task_id} defines no composite measurement cases")
        by_query: Dict[str, list[_MeasurementCase]] = {}
        for case in self.cases:
            by_query.setdefault(str(case.query_id), []).append(case)
        supported_queries = tuple(sorted(by_query.keys()))
        explicit_query = params.get("query_id")
        if explicit_query is not None:
            query_id = str(explicit_query)
            if query_id not in by_query:
                raise ValueError(f"unsupported query_id for {self.task_id}: {query_id}")
            query_index = list(supported_queries).index(query_id)
            query_probs = {query_id: 1.0}
        else:
            query_selection_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.query_id",
            )
            query_index = int(query_selection_index) % len(supported_queries)
            query_id = str(supported_queries[query_index])
            query_probs = _geometry_probability_map(supported_queries, sort_unique=True)

        case_values = by_query[query_id]
        explicit_case = params.get("case_index")
        if explicit_case is not None:
            case_index = int(explicit_case) % len(case_values)
        else:
            raw_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.{query_id}.case",
            )
            case_index = int(raw_index) % len(case_values)
        return case_values[case_index], query_probs

    def _make_render_context(self, instance_seed: int, params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 720)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
        scene_id = str(self.scene_id or self.public_scene_id)
        use_technical_diagram_style = scene_id == "angle_relations"
        technical_style_meta: Dict[str, Any] = {}
        technical_style_resolution: Dict[str, Any] = {}
        if bool(use_technical_diagram_style):
            style_scene_id = scene_id if bool(self.defaults_are_scene_aligned) else scene_id
            image, background_meta, diagram_style, diagram_style_resolution = prepare_geometry_diagram_style_and_background(
                instance_seed=int(instance_seed),
                params=params,
                scene_id=scene_id,
                canvas_width=int(width),
                canvas_height=int(height),
                allow_dark=True,
            )
            shape_style = geometry_shape_style_from_diagram_style(diagram_style)
            technical_style_meta = geometry_diagram_style_metadata(diagram_style)
            technical_style_resolution = dict(diagram_style_resolution)
        else:
            image, background_meta = make_background_canvas(
                canvas_width=int(width),
                canvas_height=int(height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=_COMPOSITE_MEASUREMENT_BACKGROUND_DEFAULTS,
                fallback_color=(255, 255, 252),
            )
            anchors = extract_background_anchor_colors(background_meta)
            shape_style = sample_geometry_shape_style(
                rng,
                params=params,
                render_defaults=render_defaults,
                anchor_colors=anchors,
            )
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("point_label_font_size", group_default(render_defaults, "point_label_font_size", 18)))
        label_stroke_width = int(
            params.get("label_stroke_width", group_default(render_defaults, "label_stroke_width", 1))
        )
        if bool(use_technical_diagram_style):
            fill_choices = (
                tuple(int(value) for value in diagram_style.fill_rgb),
                tuple(int(value) for value in diagram_style.muted_fill_rgb),
                tuple(int(value) for value in diagram_style.option_fill_rgb),
                tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
            )
            accent_choices = (
                tuple(int(value) for value in diagram_style.accent_rgb),
                tuple(int(value) for value in diagram_style.secondary_accent_rgb),
                tuple(int(value) for value in diagram_style.highlight_rgb),
                tuple(int(value) for value in diagram_style.guide_rgb),
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=(
                    f"geometry.{scene_id}.font_family"
                    if bool(self.defaults_are_scene_aligned)
                    else f"geometry.{SCENE_ID}.{scene_id}.font_family"
                ),
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            layout_offset = (
                float(rng.randint(-32, 32)),
                float(rng.randint(-20, 22)),
            )
        else:
            fill_choices = ((222, 235, 255), (230, 244, 231), (255, 236, 214), (242, 230, 255))
            accent_choices = ((30, 92, 168), (31, 119, 80), (165, 85, 24), (116, 72, 172))
            font_family = ""
            font_record = None
            layout_offset = (0.0, 0.0)
        color_idx = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.accent")) % len(fill_choices)
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            accent_color=accent_choices[color_idx],
            fill_color=fill_choices[color_idx],
            line_width=max(2, int(line_width)),
            label_stroke_width=max(0, int(label_stroke_width)),
            font=load_font(max(12, int(font_size)), bold=True, font_family=font_family),
            small_font=load_font(max(10, int(small_font_size)), bold=True, font_family=font_family),
            layout_offset=(float(layout_offset[0]), float(layout_offset[1])),
            font_family=str(font_family),
            scene_transform=LazySceneTransform(
                rng,
                params=params,
                render_defaults=render_defaults,
                canvas_width=int(width),
                canvas_height=int(height),
            ),
        )
        render_meta = {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "point_label_font_size": int(small_font_size),
            "label_stroke_width": int(ctx.label_stroke_width),
            "accent_color": list(ctx.accent_color),
            "fill_color": list(ctx.fill_color),
            "layout_jitter": {
                "offset_px": [round(float(ctx.layout_offset[0]), 3), round(float(ctx.layout_offset[1]), 3)],
                "offset_range_px": [-32, 32, -20, 22] if bool(use_technical_diagram_style) else [0, 0, 0, 0],
                "applied_before_annotation_projection": True,
            },
        }
        if bool(use_technical_diagram_style):
            render_meta.update(
                {
                    "technical_diagram_style": dict(technical_style_meta),
                    "technical_diagram_style_resolution": dict(technical_style_resolution),
                    "font_family": font_record.to_trace() if font_record is not None else {},
                    "font_asset_version": font_asset_version(),
                }
            )
        return ctx, render_meta


    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_id = str(self.scene_id or self.public_scene_id)
        if not scene_id:
            raise ValueError(f"{self.task_id} defines no public scene_id")
        gen_defaults, render_defaults, prompt_defaults = self._split_defaults()
        del gen_defaults
        case, query_probs = self._select_case(int(instance_seed), params)
        last_error: Exception | None = None
        rendered: _RenderedCompositeScene | None = None
        render_meta: Dict[str, Any] | None = None
        ctx: _RenderContext | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                attempt_params = dict(params)
                attempt_params["_render_attempt"] = int(attempt)
                ctx, render_meta = self._make_render_context(
                    int(instance_seed) + int(attempt),
                    attempt_params,
                    render_defaults,
                )
                rendered = case.build(ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or render_meta is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error
        if ctx is not None and ctx.scene_transform is not None:
            render_meta["single_object_scene_rotation"] = ctx.scene_transform.metadata()

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_COMPOSITE_MEASUREMENT_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        if rendered.annotation_keyed_points:
            annotation_type = "keyed_point_map"
            annotation_keys = tuple(rendered.annotation_keyed_points.keys())
        elif rendered.annotation_keyed_bboxes:
            annotation_type = "keyed_bbox_map"
            annotation_keys = tuple(rendered.annotation_keyed_bboxes.keys())
        else:
            annotation_type = "bbox_set"
            annotation_keys = tuple()
        json_example, json_example_answer_only = _prompt_examples(
            len(rendered.annotation_bboxes),
            annotation_type=annotation_type,
            annotation_keys=annotation_keys,
        )
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint_template = str(prompt_defaults["annotation_hint"])
        annotation_hint = (
            annotation_hint_template.format(annotation_keys=annotation_key_list)
            if "{annotation_keys}" in annotation_hint_template
            else annotation_hint_template
        )
        prompt_slots = {
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(annotation_hint),
            "answer_hint": str(prompt_defaults["answer_hint_integer"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
        if bool(self.prompts_are_scene_aligned):
            prompt_selection = render_scene_prompt_variants(
                domain=self.domain,
                scene_id=scene_id,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(rendered.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots=prompt_slots,
                instance_seed=int(instance_seed),
            )
        else:
            prompt_selection = render_scene_prompt_variants(
                domain=self.domain,
                scene_id=str(getattr(self, "scene_id", "") or getattr(self, "public_scene_id", "") or globals().get("SCENE_ID", "")),
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(rendered.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots=prompt_slots,
                instance_seed=int(instance_seed),
            )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        if annotation_type == "keyed_point_map":
            annotation_artifacts = keyed_point_annotation_artifacts(rendered.annotation_keyed_points or {})
            original_annotation_value: Any = dict(annotation_artifacts.value)
        elif annotation_type == "keyed_bbox_map":
            annotation_artifacts = keyed_bbox_annotation_artifacts(rendered.annotation_keyed_bboxes or {})
            original_annotation_value = dict(annotation_artifacts.value)
        else:
            annotation_artifacts = bbox_set_annotation_artifacts(rendered.annotation_bboxes)
            original_annotation_value = list(rendered.annotation_roles)
        annotation_value: Any = annotation_artifacts.value
        projected_annotation: Dict[str, Any] = dict(annotation_artifacts.projected_annotation)
        rendered_entities = geometry_json_ready(rendered.scene_entities, round_floats=False)
        rendered_map = geometry_json_ready(rendered.render_map, round_floats=False)
        rendered_witness = geometry_json_ready(rendered.witness, round_floats=False)
        answer_gt = TypedValue(type="integer", value=int(rendered.answer))
        annotation_gt = TypedValue(type=annotation_type, value=annotation_value)
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": str(self.scene_kind),
                "scene_id": scene_id,
                "entities": rendered_entities,
                "relations": {
                    "query_id": str(rendered.query_id),
                    "answer_value": int(rendered.answer),
                    "annotation_roles": list(rendered.annotation_roles),
                },
            },
            "query_spec": {
                "scene_id": scene_id,
                "query_id": str(rendered.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": scene_id,
                    "query_id": str(rendered.query_id),
                    "query_id_probabilities": dict(query_probs),
                    "case_answer": int(rendered.answer),
                },
            },
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": {
                "coord_space": "pixel",
                **dict(rendered_map),
            },
            "execution_trace": {
                "scene_id": scene_id,
                "query_id": str(rendered.query_id),
                "query_id_probabilities": dict(query_probs),
                "answer_type": "integer",
                "answer_value": int(rendered.answer),
                "annotation_roles": list(rendered.annotation_roles),
                "reasoning_steps": int(rendered.reasoning_steps),
                **dict(rendered_witness),
            },
            "witness_symbolic": {
                "type": str(self.witness_type),
                "scene_id": scene_id,
                "query_id": str(rendered.query_id),
                "answer_value": int(rendered.answer),
                "annotation_roles": list(rendered.annotation_roles),
                "source_witness_type": str(annotation_type),
                "original_annotation_value": original_annotation_value,
                **dict(rendered_witness),
            },
            "projected_annotation": projected_annotation,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=scene_id,
            query_id=str(rendered.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
