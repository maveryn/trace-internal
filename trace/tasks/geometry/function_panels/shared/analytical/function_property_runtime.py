"""Runtime assembly for analytical function-property panel objectives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping

from trace.tasks.geometry.shared.annotation_values import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .function_property_common import (
    _GRID_MAX,
    _GRID_MIN,
    _PROMPT_DEFAULTS,
    _RenderedScene,
    _ResolvedQuery,
)
from .function_property_scene import (
    _relation_trace_payload,
    _render_scene,
    _resolve_query,
)

SCENE_ID = "function_panels"


@dataclass(frozen=True)
class FunctionPropertyArtifacts:
    """Rendered function-property artifacts before public task output binding."""

    query: _ResolvedQuery
    rendered_scene: _RenderedScene
    prompt_artifacts: Any
    annotation_value: list[list[float]]
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, str]


def function_property_query(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedQuery:
    """Resolve one public function-property query branch."""

    forced_params = dict(params)
    forced_params["query_id"] = str(query_id)
    query = _resolve_query(int(instance_seed), params=forced_params)
    return replace(
        query,
        query_id=str(query_id),
        query_id_probabilities={str(key): float(value) for key, value in query_id_probabilities.items()},
    )


def build_function_property_artifacts(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query: _ResolvedQuery,
) -> FunctionPropertyArtifacts:
    """Render and assemble shared artifacts for a function-property panel task."""

    rendered_scene = _render_scene(query, instance_seed=int(instance_seed), params=params)
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "annotation_hint_selected_panel_bbox",
            "answer_hint_option_letter",
        ),
        context="prompt defaults for function_panels function-property objectives",
    )
    annotation_artifacts = bbox_set_annotation_artifacts([rendered_scene.panel_bboxes[str(query.winner_label)]])
    annotation_value = annotation_artifacts.value
    json_example, json_example_answer_only = resolve_prompt_json_examples(
        _PROMPT_DEFAULTS,
        annotation_value=annotation_value,
        answer_type="option_letter",
    )
    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "target_domain": str(rendered_scene.target_domain),
            "target_range": str(rendered_scene.target_range),
            "target_interval": str(rendered_scene.target_interval),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_selected_panel_bbox"]),
            "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    winner_relation = rendered_scene.relations_by_label[str(query.winner_label)]
    relations_trace = {
        str(label): _relation_trace_payload(rendered_scene.relations_by_label[str(label)])
        for label in query.label_pool
    }
    trace_payload: Dict[str, Any] = {
        "scene_ir": {
            "scene_kind": "geometry_analytical_function_property_grid",
            "entities": [
                {
                    "label": str(label),
                    "panel_bbox": list(rendered_scene.panel_bboxes[str(label)]),
                    "plot_bbox": list(rendered_scene.plot_bboxes[str(label)]),
                    "relation": dict(relations_trace[str(label)]),
                }
                for label in query.label_pool
            ],
            "relations": {
                "query_id": str(query.query_id),
                "winner_label": str(query.winner_label),
                "target_domain": str(rendered_scene.target_domain),
                "target_range": str(rendered_scene.target_range),
                "target_interval": str(rendered_scene.target_interval),
            },
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(query.label_pool),
                "panel_count_probabilities": dict(query.panel_count_probabilities),
                "target_domain": str(rendered_scene.target_domain),
                "target_range": str(rendered_scene.target_range),
                "target_interval": str(rendered_scene.target_interval),
            },
        },
        "render_spec": {
            "canvas_width": int(rendered_scene.image.size[0]),
            "canvas_height": int(rendered_scene.image.size[1]),
            "coord_space": "pixel",
            "technical_diagram_style": dict(rendered_scene.diagram_style_meta),
            "background_style": dict(rendered_scene.background_meta),
            "post_image_noise": dict(rendered_scene.post_noise_meta),
            "panel_style": dict(rendered_scene.panel_style_meta),
            "line_colors": [list(color) for color in rendered_scene.line_colors],
            "line_color_selection": dict(rendered_scene.line_color_meta),
            "panel_count": int(len(query.label_pool)),
            "panel_count_probabilities": dict(rendered_scene.panel_count_probabilities),
            "panel_columns": int(rendered_scene.panel_columns),
            "panel_rows": int(rendered_scene.panel_rows),
            "graph_unit_bounds": {"x": [int(_GRID_MIN), int(_GRID_MAX)], "y": [int(_GRID_MIN), int(_GRID_MAX)]},
        },
        "render_map": {
            "panel_bboxes": dict(rendered_scene.panel_bboxes),
            "plot_bboxes": dict(rendered_scene.plot_bboxes),
            "technical_diagram_frame_mode": str(rendered_scene.diagram_style_meta.get("frame_mode", "none")),
            "coord_space": "pixel",
        },
        "execution_trace": {
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "winner_label": str(query.winner_label),
            "winner_relation": dict(_relation_trace_payload(winner_relation)),
            "relations_by_label": dict(relations_trace),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "winner_label_probabilities": dict(query.winner_label_probabilities),
            "panel_count_probabilities": dict(query.panel_count_probabilities),
            "target_interval": str(rendered_scene.target_interval),
        },
        "witness_symbolic": {
            "type": "function_property_panel_selection",
            "query_id": str(query.query_id),
            "answer_label": str(query.winner_label),
            "target_domain": str(rendered_scene.target_domain),
            "target_range": str(rendered_scene.target_range),
            "target_interval": str(rendered_scene.target_interval),
            "relations_by_label": dict(relations_trace),
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(annotation_value),
            "panel_bbox_by_label": dict(rendered_scene.panel_bboxes),
            "plot_bbox_by_label": dict(rendered_scene.plot_bboxes),
        },
    }
    return FunctionPropertyArtifacts(
        query=query,
        rendered_scene=rendered_scene,
        prompt_artifacts=prompt_artifacts,
        annotation_value=annotation_value,
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
    )
