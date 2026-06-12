"""Runtime assembly for function-graph count objectives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import build_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.text_rendering import resolve_scene_label_font_size_px
from trace.tasks.geometry.shared.graph_rendering import graph_paper_grid_from_frame
from trace.tasks.geometry.shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from trace.tasks.geometry.shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)

from .count_common import (
    LOCAL_EXTREMUM_COUNT,
    REFERENCE_LINE_CROSSING_COUNT,
    TURNING_POINT_COUNT,
    _DEFAULTS,
    _PROMPT_DEFAULTS,
    _RENDER_DEFAULTS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _RenderedGraphScene,
    _ResolvedQuery,
    _SampledGraphScene,
)
from .count_rendering import (
    _build_object_description,
    _execution_trace_for_trace,
    _extremum_prompt_slots,
    _query_params_for_trace,
    _reference_line_prompt_description,
    _render_scene,
    _scene_relations_for_trace,
)
from .count_sampling import _resolve_axes, _sample_scene

SCENE_ID = "function_graph"


@dataclass(frozen=True)
class CountArtifacts:
    """Rendered graph-count artifacts before public task output binding."""

    query: _ResolvedQuery
    sampled_scene: _SampledGraphScene
    rendered_scene: _RenderedGraphScene
    prompt_artifacts: Any
    image: Any
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, str]


def count_query(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedQuery:
    """Resolve scene axes for one public count objective."""

    forced_params = dict(params)
    forced_params["query_id"] = str(query_id)
    query = _resolve_axes(int(instance_seed), params=forced_params)
    return replace(
        query,
        query_id=str(query_id),
        query_id_probabilities={str(key): float(value) for key, value in query_id_probabilities.items()},
    )


def _prompt_defaults() -> Dict[str, Any]:
    return required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_integer",
            "annotation_hint_pixel_point_set",
            "annotation_hint_reference_line_crossing_count",
            "annotation_hint_turning_point_count",
            "annotation_hint_local_extremum_count",
            "json_example_reference_line_crossing_count",
            "json_example_turning_point_count",
            "json_example_local_extremum_count",
            "json_example_answer_only_reference_line_crossing_count",
            "json_example_answer_only_turning_point_count",
            "json_example_answer_only_local_extremum_count",
        ),
        context="prompt defaults for function_graph count objectives",
    )


def build_count_artifacts(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query: _ResolvedQuery,
) -> CountArtifacts:
    """Render one function-graph count scene and assemble prompt/trace fragments."""

    rng = spawn_rng(int(instance_seed), "function_graph.count.scene")
    prompt_defaults = _prompt_defaults()

    scene_context = resolve_graph_scene_context(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
        fallback_canvas_min=_DEFAULTS.canvas_size_min,
        fallback_canvas_max=_DEFAULTS.canvas_size_max,
        fallback_cells_min=_DEFAULTS.graph_cells_min,
        fallback_cells_max=_DEFAULTS.graph_cells_max,
        require_graph_paper_background=True,
        graph_style_overrides={
            "origin_fraction_x": 0.5,
            "origin_fraction_y": 0.5,
            "axis_scale_label_max_abs": 8,
            "origin_label_enabled": False,
        },
    )
    image, draw, background_meta = make_graph_scene_canvas(
        instance_seed=int(instance_seed),
        context=scene_context,
        background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
        require_graph_paper=True,
    )

    line_width = int(params.get("line_width", group_default(_RENDER_DEFAULTS, "line_width", _DEFAULTS.line_width)))
    line_width *= int(scene_context.scene_scale)
    guide_line_width = int(
        params.get("guide_line_width", group_default(_RENDER_DEFAULTS, "guide_line_width", _DEFAULTS.guide_line_width))
    )
    guide_line_width *= int(scene_context.scene_scale)
    label_font_size_px = int(
        params.get(
            "label_font_size_px",
            resolve_scene_label_font_size_px(
                canvas_size=int(scene_context.canvas_size),
                graph_spacing=int(scene_context.graph_spacing),
                scene_scale=int(scene_context.scene_scale),
                min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
            ),
        )
    )
    shape_style = sample_geometry_shape_style(
        rng,
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        anchor_colors=extract_background_anchor_colors(background_meta),
    )

    sampled_scene = _sample_scene(
        rng,
        scene_variant=str(query.scene_variant),
        query_id=str(query.query_id),
        reference_line_kind=query.reference_line_kind,
        extremum_kind=query.extremum_kind,
        target_count=int(query.target_count),
    )
    rendered_scene = _render_scene(
        draw,
        context=scene_context,
        sampled_scene=sampled_scene,
        shape_style=shape_style,
        line_width=int(line_width),
        guide_line_width=int(guide_line_width),
        label_font_size_px=int(label_font_size_px),
    )
    image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
        image,
        instance_seed=int(instance_seed),
        context=scene_context,
        background_meta=background_meta,
        noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
    )

    object_description = _build_object_description(
        prompt_defaults=_PROMPT_DEFAULTS,
        scene_variant=str(query.scene_variant),
        query_id=str(query.query_id),
        reference_line_kind=query.reference_line_kind,
    )
    json_example, json_example_answer_only = build_prompt_json_examples(
        annotation_value=rendered_scene.annotation_value,
        answer_type="integer",
    )
    extremum_slots = _extremum_prompt_slots(
        prompt_defaults=_PROMPT_DEFAULTS,
        extremum_kind=query.extremum_kind,
    )
    reference_line_description = _reference_line_prompt_description(
        prompt_defaults=_PROMPT_DEFAULTS,
        reference_line_kind=query.reference_line_kind,
        query_line_y=sampled_scene.query_line_y,
    )
    annotation_hint = str(prompt_defaults["annotation_hint_pixel_point_set"])
    if str(query.query_id) == REFERENCE_LINE_CROSSING_COUNT:
        annotation_hint = str(prompt_defaults["annotation_hint_reference_line_crossing_count"]).format(
            reference_line_description=str(reference_line_description)
        )
        json_example = str(prompt_defaults["json_example_reference_line_crossing_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_reference_line_crossing_count"])
    elif str(query.query_id) == TURNING_POINT_COUNT:
        annotation_hint = str(prompt_defaults["annotation_hint_turning_point_count"])
        json_example = str(prompt_defaults["json_example_turning_point_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_turning_point_count"])
    elif str(query.query_id) == LOCAL_EXTREMUM_COUNT:
        annotation_hint = str(prompt_defaults["annotation_hint_local_extremum_count"]).format(**dict(extremum_slots))
        json_example = str(prompt_defaults["json_example_local_extremum_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_local_extremum_count"])

    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(object_description),
            "reference_line_description": str(reference_line_description),
            **dict(extremum_slots),
            "query_line_equation": (
                "" if sampled_scene.query_line_y is None else f"y = {int(sampled_scene.query_line_y)}"
            ),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(annotation_hint),
            "answer_hint": str(prompt_defaults["answer_hint_integer"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    query_params = _query_params_for_trace(query)
    execution_trace = _execution_trace_for_trace(query, rendered_scene)
    trace_payload = {
        "scene_ir": {
            "scene_kind": "geometry_graphing_count",
            "entities": list(rendered_scene.scene_entities),
            "relations": _scene_relations_for_trace(query),
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": {
            "canvas_size": int(scene_context.canvas_size),
            "coord_space": "pixel",
            "background_style": dict(background_meta_final),
            "post_image_noise": dict(post_noise_meta),
            "shape_style": dict(shape_style.to_trace_dict()),
            "graph_coordinate_frame": dict(scene_context.graph_frame),
            "graph_paper_grid": graph_paper_grid_from_frame(scene_context.graph_frame),
            **dict(scene_context.graph_layout_metadata),
            "scene_variant": str(query.scene_variant),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": dict(execution_trace),
        "witness_symbolic": dict(rendered_scene.witness_symbolic),
        "projected_annotation": dict(rendered_scene.projected_annotation),
    }
    return CountArtifacts(
        query=query,
        sampled_scene=sampled_scene,
        rendered_scene=rendered_scene,
        prompt_artifacts=prompt_artifacts,
        image=image,
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
    )
