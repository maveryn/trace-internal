"""Select the coordinate panel whose points form a requested quadrilateral."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.geometry.shared.noise_defaults import load_geometry_noise_defaults
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import geometry_probability_map, select_geometry_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants

from .shared.defaults import resolve_label_pool
from .shared.rendering import render_panel_scene
from .shared.state import PanelScene

DOMAIN = "geometry"
SCENE_ID = "coordinate_panels"
TASK_ID = "task_geometry__coordinate_panels__quadrilateral_shape_match_label"
PROMPT_BUNDLE_ID = "geometry_coordinate_quadrilateral_v0"

QUERY_ID_SQUARE = "square_shape_match_label"
QUERY_ID_RECTANGLE = "rectangle_shape_match_label"
QUERY_ID_RHOMBUS = "rhombus_shape_match_label"
QUERY_ID_PARALLELOGRAM = "parallelogram_shape_match_label"
QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_SQUARE,
    QUERY_ID_RECTANGLE,
    QUERY_ID_RHOMBUS,
    QUERY_ID_PARALLELOGRAM,
)
QUERY_TARGET_KIND: Dict[str, str] = {
    QUERY_ID_SQUARE: "square",
    QUERY_ID_RECTANGLE: "rectangle_non_square",
    QUERY_ID_RHOMBUS: "rhombus_non_square",
    QUERY_ID_PARALLELOGRAM: "parallelogram_only",
}
TARGET_SHAPE_NAME: Dict[str, str] = {
    "parallelogram_only": "parallelogram",
    "rectangle_non_square": "rectangle",
    "square": "square",
    "rhombus_non_square": "rhombus",
    "other": "other",
}
DEFAULT_PANEL_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
FIXED_PANEL_COUNT = 6

SHAPE_MATCH_TASK_ID = TASK_ID
SHAPE_MATCH_QUERY_IDS = QUERY_IDS
PANEL_SCENE_ID = SCENE_ID

_SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id="coordinate")


@dataclass(frozen=True)
class _ResolvedQuery:
    """Task-owned query and answer-label binding."""

    query_id: str
    target_kind: str
    target_shape_name: str
    query_probabilities: Dict[str, float]
    winner_label: str
    winner_label_probabilities: Dict[str, float]
    label_pool: Tuple[str, ...]
    panel_count: int
    panel_count_probabilities: Dict[str, float]


def _split_defaults_for_task() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )


def _select_winner_label(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    label_pool: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    labels = tuple(str(label) for label in label_pool)
    explicit = params.get("winner_label", params.get("answer_label"))
    if explicit is not None:
        label = str(explicit)
        if label not in set(labels):
            raise ValueError(f"winner_label={label!r} is not in label pool {labels!r}")
        return label, {label: 1.0}
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.winner_label",
    )
    return str(labels[int(selection_index) % len(labels)]), geometry_probability_map(labels)


def _resolve_query(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedQuery:
    """Resolve the public query, visible answer label, and panel count."""

    query_id, query_probabilities = select_geometry_query_id(
        params,
        query_ids=QUERY_IDS,
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
    )
    label_pool = resolve_label_pool(params, generation_defaults, "panel_labels", DEFAULT_PANEL_LABEL_POOL)
    winner_label, winner_probabilities = _select_winner_label(
        params=params,
        instance_seed=int(instance_seed),
        label_pool=label_pool,
    )
    target_kind = str(QUERY_TARGET_KIND[str(query_id)])
    return _ResolvedQuery(
        query_id=str(query_id),
        target_kind=str(target_kind),
        target_shape_name=str(TARGET_SHAPE_NAME[str(target_kind)]),
        query_probabilities=dict(query_probabilities),
        winner_label=str(winner_label),
        winner_label_probabilities=dict(winner_probabilities),
        label_pool=tuple(str(label) for label in label_pool),
        panel_count=FIXED_PANEL_COUNT,
        panel_count_probabilities={str(FIXED_PANEL_COUNT): 1.0},
    )


def _prompt_artifacts(
    *,
    prompt_defaults_all: Mapping[str, Any],
    query: _ResolvedQuery,
    annotation_value: Sequence[Sequence[float]],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Any:
    """Render prompt variants from the external prompt bundle."""

    prompt_defaults = required_group_defaults(
        prompt_defaults_all,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "annotation_hint_selected_panel_point_set",
            "answer_hint_option_letter",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    json_example, json_example_answer_only = resolve_prompt_json_examples(
        prompt_defaults_all,
        annotation_value=list(annotation_value),
        answer_type="option_letter",
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_selected_panel_point_set"]),
            "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
        preferred_mode=str(params.get("prompt_mode", "answer_and_annotation")),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def _panel_trace_payload(
    *,
    query: _ResolvedQuery,
    rendered: PanelScene,
    prompt_artifacts: Any,
    annotation_value: Sequence[Sequence[float]],
) -> Dict[str, Any]:
    """Build verifier payload from the same rendered scene used for answer binding."""

    panels_trace = {
        str(label): {
            "label": str(label),
            "points_graph": [[int(value) for value in point] for point in spec.points],
            "points_px": [[float(value) for value in point] for point in spec.points_px],
            "classified_kind": str(spec.classified_kind),
            "panel_bbox": list(spec.panel_bbox),
            "plot_bbox": list(spec.plot_bbox),
            "is_answer": str(label) == str(query.winner_label),
        }
        for label, spec in rendered.panels_by_label.items()
    }
    annotation_points = [[float(point[0]), float(point[1])] for point in annotation_value]
    return {
        "scene_id": SCENE_ID,
        "query_id": str(query.query_id),
        "scene_ir": {
            "scene_kind": "geometry_coordinate_panels",
            "entities": [dict(panels_trace[str(label)]) for label in sorted(panels_trace)],
            "relations": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "target_kind": str(query.target_kind),
                "target_shape_name": str(query.target_shape_name),
                "winner_label": str(query.winner_label),
            },
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": PROMPT_BUNDLE_ID,
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "target_kind": str(query.target_kind),
                "target_shape_name": str(query.target_shape_name),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(rendered.panels_by_label.keys()),
                "panel_count": int(query.panel_count),
                "panel_count_probabilities": dict(query.panel_count_probabilities),
            },
        },
        "render_spec": {
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "panel_count": int(len(rendered.panels_by_label)),
            "panel_count_probabilities": dict(rendered.option_count_probabilities),
            "panel_style": dict(rendered.panel_style_meta),
            "marker_style": dict(rendered.marker_meta),
            "background_style": dict(rendered.background_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "coord_space": "pixel",
            "panel_bboxes": {str(label): list(spec.panel_bbox) for label, spec in rendered.panels_by_label.items()},
            "plot_bboxes": {str(label): list(spec.plot_bbox) for label, spec in rendered.panels_by_label.items()},
            "points_graph_by_label": {
                str(label): [[int(value) for value in point] for point in spec.points]
                for label, spec in rendered.panels_by_label.items()
            },
            "points_px_by_label": {
                str(label): [[float(value) for value in point] for point in spec.points_px]
                for label, spec in rendered.panels_by_label.items()
            },
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "target_kind": str(query.target_kind),
            "target_shape_name": str(query.target_shape_name),
            "panels_by_label": dict(panels_trace),
            "query_id_probabilities": dict(query.query_probabilities),
            "panel_count_probabilities": dict(rendered.option_count_probabilities),
        },
        "witness_symbolic": {
            "type": "coordinate_quadrilateral_shape_panel_match",
            "answer_label": str(query.winner_label),
            "target_kind": str(query.target_kind),
            "panels_by_label": dict(panels_trace),
        },
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in annotation_points],
            "pixel_point_set": [list(point) for point in annotation_points],
            "points_px_by_label": {
                str(label): [[float(value) for value in point] for point in spec.points_px]
                for label, spec in rendered.panels_by_label.items()
            },
            "panel_bbox_by_label": {str(label): list(spec.panel_bbox) for label, spec in rendered.panels_by_label.items()},
        },
        "prompt": {
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        },
    }


@register_task
class GeometryCoordinateQuadrilateralShapeMatchLabelTask:
    """Choose the coordinate panel whose four points form the requested quadrilateral."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one panel-match instance with task-owned answer and annotation binding."""

        _ = int(max_attempts)
        generation_defaults, rendering_defaults, prompt_defaults_all = _split_defaults_for_task()
        query = _resolve_query(
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
        )
        rendered = render_panel_scene(
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
            rendering_defaults=rendering_defaults,
            target_kind=str(query.target_kind),
            winner_label=str(query.winner_label),
            label_pool=query.label_pool,
            panel_count=int(query.panel_count),
            option_count_probabilities=query.panel_count_probabilities,
            noise_defaults=_NOISE_DEFAULTS,
        )
        annotation_value = [
            [float(point[0]), float(point[1])]
            for point in rendered.panels_by_label[str(query.winner_label)].points_px
        ]
        prompt_artifacts = _prompt_artifacts(
            prompt_defaults_all=prompt_defaults_all,
            query=query,
            annotation_value=annotation_value,
            params=params,
            instance_seed=int(instance_seed),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(query.winner_label)),
            annotation_gt=TypedValue(type="point_set", value=[list(point) for point in annotation_value]),
            image=rendered.image,
            image_id=f"{TASK_ID}:{int(instance_seed)}",
            trace_payload=_panel_trace_payload(
                query=query,
                rendered=rendered,
                prompt_artifacts=prompt_artifacts,
                annotation_value=annotation_value,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryCoordinateQuadrilateralShapeMatchLabelTask",
    "PANEL_SCENE_ID",
    "QUERY_IDS",
    "SCENE_ID",
    "SHAPE_MATCH_QUERY_IDS",
    "SHAPE_MATCH_TASK_ID",
    "TASK_ID",
]
