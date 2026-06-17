"""Identify the numbered cell that breaks a color or size icon-grid pattern."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.scene_config import get_scene_defaults
from ....core.seed import spawn_rng
from ....core.taxonomy import resolve_task_taxonomy
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import violating_cell_bbox_annotation
from .shared.defaults import DOMAIN, SCENE_ID, PatternGridDefaults
from .shared.output import (
    pattern_grid_render_style,
    pattern_rule_for_axis,
    question_format_for_axis,
    scene_kind_for_axis,
)
from .shared.prompts import render_pattern_grid_prompt_artifacts
from .shared.rendering import render_pattern_grid_scene
from .shared.sampling import resolve_pattern_grid_spec
from .shared.styles import resolve_pattern_grid_render_params


TASK_ID = "task_icons__pattern_grid__attribute_pattern_violation_index"
QUERY_GRID_COLOR_VIOLATION = "grid_color_violation"
QUERY_GRID_SIZE_VIOLATION = "grid_size_violation"
SUPPORTED_QUERY_IDS: Tuple[str, str] = (
    QUERY_GRID_COLOR_VIOLATION,
    QUERY_GRID_SIZE_VIOLATION,
)
QUERY_IDS = SUPPORTED_QUERY_IDS
_QUERY_TO_ATTRIBUTE_AXIS = {
    QUERY_GRID_COLOR_VIOLATION: "color",
    QUERY_GRID_SIZE_VIOLATION: "size",
}
_QUERY_TO_PROMPT_KEY = {
    QUERY_GRID_COLOR_VIOLATION: "question_text_grid_color_violation",
    QUERY_GRID_SIZE_VIOLATION: "question_text_grid_size_violation",
}

_DEFAULTS = PatternGridDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select one semantic pattern-grid query branch."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=QUERY_GRID_COLOR_VIOLATION,
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _question_text_for_query(query_id: str, prompt_defaults: Mapping[str, Any]) -> str:
    """Return the externally configured prompt question for a public query."""

    key = _QUERY_TO_PROMPT_KEY[str(query_id)]
    text = str(prompt_defaults.get(key, "")).strip()
    if not text:
        raise ValueError(f"missing prompt default {key!r} for {TASK_ID}")
    return text


def _axis_relation_payload(axis: str, spec, rendered_scene) -> Dict[str, Any]:
    """Build the axis-specific relation trace payload."""

    relations: Dict[str, Any] = {
        "attribute_axis": str(axis),
        "pattern_rule": pattern_rule_for_axis(str(axis)),
        "pattern_icon_id": str(rendered_scene.pattern_icon_id),
        "level_support": [int(value) for value in spec.level_support],
        "base_level": int(spec.base_level),
        "row_step_levels": int(spec.row_step_levels),
        "col_step_levels": int(spec.col_step_levels),
        "expected_levels": [int(value) for value in spec.expected_levels],
        "observed_levels": [int(value) for value in spec.observed_levels],
        "shared_rotation_degrees": int(spec.shared_rotation_degrees),
        "violation_cell_index": int(spec.violation_cell_index),
    }
    if str(axis) == "color":
        relations.update(
            {
                "pattern_rule": "row_col_color_level_offsets",
                "color_levels": [int(value) for value in spec.level_support],
                "color_level_names": [str(value) for value in spec.level_names],
                "color_ladder_rgb": [list(color) for color in spec.color_ladder_rgb],
                "base_color_level": int(spec.base_level),
                "row_step_color_levels": int(spec.row_step_levels),
                "col_step_color_levels": int(spec.col_step_levels),
                "expected_grid_color_levels": [int(value) for value in spec.expected_levels],
                "observed_grid_color_levels": [int(value) for value in spec.observed_levels],
            }
        )
    else:
        size_map = {
            str(level): int(size_px)
            for level, size_px in dict(rendered_scene.size_level_nominal_sizes_px or {}).items()
        }
        relations.update(
            {
                "pattern_rule": "row_col_size_level_offsets",
                "size_levels": [int(value) for value in spec.level_support],
                "size_level_nominal_sizes_px": size_map,
                "base_size_level": int(spec.base_level),
                "row_step_levels": int(spec.row_step_levels),
                "col_step_levels": int(spec.col_step_levels),
                "expected_grid_size_levels": [int(value) for value in spec.expected_levels],
                "observed_grid_size_levels": [int(value) for value in spec.observed_levels],
            }
        )
    return relations


def _axis_execution_payload(axis: str, spec, rendered_scene) -> Dict[str, Any]:
    """Build verifier-facing execution fields while preserving legacy axis keys.

    The public task has one answer and annotation schema, but color and size
    branches expose different diagnostic metadata names for downstream tests,
    review pages, and older analysis scripts.
    """

    payload: Dict[str, Any] = {
        "attribute_axis": str(axis),
        "pattern_rule": pattern_rule_for_axis(str(axis)),
        "level_support": [int(value) for value in spec.level_support],
        "base_level": int(spec.base_level),
        "row_step_levels": int(spec.row_step_levels),
        "col_step_levels": int(spec.col_step_levels),
        "violation_level": int(spec.violation_level),
        "expected_levels": [int(value) for value in spec.expected_levels],
        "observed_levels": [int(value) for value in spec.observed_levels],
    }
    if str(axis) == "color":
        expected_rgbs = [list(spec.color_ladder_rgb[int(level)]) for level in spec.expected_levels]
        observed_rgbs = [list(spec.color_ladder_rgb[int(level)]) for level in spec.observed_levels]
        payload.update(
            {
                "color_levels": [int(value) for value in spec.level_support],
                "color_level_names": [str(value) for value in spec.level_names],
                "color_ladder_rgb": [list(color) for color in spec.color_ladder_rgb],
                "base_color_level": int(spec.base_level),
                "row_step_color_levels": int(spec.row_step_levels),
                "col_step_color_levels": int(spec.col_step_levels),
                "violation_color_level": int(spec.violation_level),
                "expected_grid_color_levels": [int(value) for value in spec.expected_levels],
                "observed_grid_color_levels": [int(value) for value in spec.observed_levels],
                "expected_grid_color_rgb": expected_rgbs,
                "observed_grid_color_rgb": observed_rgbs,
                "nominal_size_px": int(rendered_scene.nominal_size_px or 0),
            }
        )
    else:
        size_map = {
            str(level): int(size_px)
            for level, size_px in dict(rendered_scene.size_level_nominal_sizes_px or {}).items()
        }
        expected_sizes = [int((rendered_scene.size_level_nominal_sizes_px or {})[int(level)]) for level in spec.expected_levels]
        observed_sizes = [int((rendered_scene.size_level_nominal_sizes_px or {})[int(level)]) for level in spec.observed_levels]
        payload.update(
            {
                "size_levels": [int(value) for value in spec.level_support],
                "size_level_nominal_sizes_px": size_map,
                "base_size_level": int(spec.base_level),
                "violation_size_level": int(spec.violation_level),
                "expected_grid_size_levels": [int(value) for value in spec.expected_levels],
                "observed_grid_size_levels": [int(value) for value in spec.observed_levels],
                "expected_grid_nominal_sizes_px": expected_sizes,
                "observed_grid_nominal_sizes_px": observed_sizes,
            }
        )
    return payload


@register_task
class IconsPatternGridAttributePatternViolationTask:
    """Identify the numbered cell breaking a visible color or size pattern."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic numbered pattern-grid instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        attribute_axis = str(_QUERY_TO_ATTRIBUTE_AXIS[str(query_id)])
        spec = resolve_pattern_grid_spec(
            attribute_axis=str(attribute_axis),
            instance_seed=int(instance_seed),
            params=task_params,
            generation_defaults=_GEN_DEFAULTS,
            namespace=TASK_ID,
        )
        render_params = resolve_pattern_grid_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        if int(render_params["cell_box_width_min_px"]) > int(render_params["cell_box_width_max_px"]):
            raise ValueError("cell_box_width_min_px must be <= cell_box_width_max_px")
        if int(render_params["cell_box_height_min_px"]) > int(render_params["cell_box_height_max_px"]):
            raise ValueError("cell_box_height_min_px must be <= cell_box_height_max_px")
        pool_manifest = str(
            task_params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest))
        )

        scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.scene")
        rendered_scene = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                rendered_scene = render_pattern_grid_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    spec=spec,
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                    noise_namespace=f"{TASK_ID}.{attribute_axis}",
                )
                break
            except Exception as exc:  # pragma: no cover - exercised by retry smoke tests
                last_error = exc
                continue
        if rendered_scene is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        prompt_defaults, prompt_artifacts = render_pattern_grid_prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=_PROMPT_DEFAULTS,
            question_text=_question_text_for_query(str(query_id), _PROMPT_DEFAULTS),
        )
        annotation_artifacts = violating_cell_bbox_annotation(rendered_scene.violating_cell_bbox)
        answer_gt = TypedValue(type="integer", value=int(spec.answer_index))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        )
        taxonomy = resolve_task_taxonomy(TASK_ID)
        common_ids = {
            "domain": taxonomy.domain,
            "scene_id": taxonomy.scene_id,
            "task_id": TASK_ID,
            "query_id": str(query_id),
        }
        axis_relations = _axis_relation_payload(attribute_axis, spec, rendered_scene)
        axis_execution = _axis_execution_payload(attribute_axis, spec, rendered_scene)
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": TASK_ID,
                "source_domain": taxonomy.source_domain,
                "source_scene_id": taxonomy.source_scene_id,
                "query_id": str(query_id),
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": scene_kind_for_axis(attribute_axis),
                "entities": [
                    *[dict(cell) for cell in rendered_scene.scene_cells],
                    *[dict(instance) for instance in rendered_scene.scene_icon_instances],
                ],
                "relations": axis_relations,
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                **build_prompt_query_spec(
                    prompt_artifacts=prompt_artifacts,
                    query_id=str(query_id),
                    params={
                        "scene_id": taxonomy.scene_id,
                        "query_id_probabilities": dict(query_probabilities),
                        "attribute_axis": str(attribute_axis),
                        "grid_rows": int(spec.grid_rows),
                        "grid_cols": int(spec.grid_cols),
                        "answer_index": int(spec.answer_index),
                        "answer_index_probabilities": dict(spec.answer_index_probabilities),
                        "violation_cell_index": int(spec.violation_cell_index),
                        "pool_manifest": str(pool_manifest),
                        "cell_box_width_px": int(rendered_scene.cell_box_width_px),
                        "cell_box_height_px": int(rendered_scene.cell_box_height_px),
                    },
                ),
            },
            "render_spec": {
                **common_ids,
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": pattern_grid_render_style(
                    render_params=render_params,
                    rendered_scene=rendered_scene,
                    spec=spec,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "violating_cell_bbox": list(rendered_scene.violating_cell_bbox),
                },
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "numbered_grid",
                "query_id_probabilities": dict(query_probabilities),
                "grid_rows": int(spec.grid_rows),
                "grid_cols": int(spec.grid_cols),
                "answer_index": int(spec.answer_index),
                "violation_cell_index": int(spec.violation_cell_index),
                "shared_rotation_degrees": int(spec.shared_rotation_degrees),
                "pattern_icon_id": str(rendered_scene.pattern_icon_id),
                "plausible_rule_count": int(spec.plausible_rule_count),
                "total_rule_support": int(spec.total_rule_support),
                "cell_box_width_px": int(rendered_scene.cell_box_width_px),
                "cell_box_height_px": int(rendered_scene.cell_box_height_px),
                "question_format": question_format_for_axis(attribute_axis),
                **axis_execution,
            },
            "witness_symbolic": {
                "attribute_axis": str(attribute_axis),
                "pattern_rule": pattern_rule_for_axis(attribute_axis),
                "expected_levels": [int(value) for value in spec.expected_levels],
                "observed_levels": [int(value) for value in spec.observed_levels],
                "violation_cell_index": int(spec.violation_cell_index),
                "plausible_rule_count": int(spec.plausible_rule_count),
                **axis_execution,
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered_scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsPatternGridAttributePatternViolationTask", "QUERY_IDS", "SUPPORTED_QUERY_IDS"]
