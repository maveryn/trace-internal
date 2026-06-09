"""Task-output assembly for mixed-dashboard chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import font_asset_version
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.visual_style.context_layer import context_text_layer_metadata
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from .cross_panel_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _TASK_GROUP_DEFAULTS,
    _Category,
    _Dataset,
    _Panel,
    _Rendered,
    _join_labels,
    _join_quoted_labels,
    _resolve_context_text_params,
    _resolve_render_params,
)
from .cross_panel_rendering import (
    _bbox_map_to_json,
    _nested_bbox_map_to_json,
    _nested_point_map_to_json,
    _point_map_to_json,
    _render_dashboard,
)
from .cross_panel_sampling import _build_dataset


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    answer_type = str(dataset.query.answer_type)
    query_id = str(dataset.query.query_id)
    if answer_type == "option_letter":
        answer_hint = str(prompt_defaults["answer_hint_option_letter"])
        annotation_hint = str(prompt_defaults["annotation_hint_statement_option"])
        json_example = str(prompt_defaults["json_example_statement_option"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_option_letter"])
    elif answer_type == "string":
        answer_hint = str(prompt_defaults["answer_hint_label"])
        if query_id == "shared_label_rank_gap_extremum":
            annotation_hint = str(prompt_defaults["annotation_hint_shared_label_pair"])
        else:
            annotation_hint = str(prompt_defaults["annotation_hint_label"])
        json_example = str(prompt_defaults["json_example_label"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_label"])
    elif query_id in {"dual_condition_count", "top_k_overlap_count", "category_panel_condition_count"}:
        answer_hint = str(prompt_defaults["answer_hint_count"])
        annotation_hint = str(prompt_defaults["annotation_hint_count"])
        json_example = str(prompt_defaults["json_example_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_count"])
    elif query_id == "dual_source_target_sum_value":
        answer_hint = str(prompt_defaults["answer_hint_value"])
        annotation_hint = str(prompt_defaults["annotation_hint_dual_source_target_sum"])
        json_example = str(prompt_defaults["json_example_dual_source_target_sum"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_value"])
    else:
        answer_hint = str(prompt_defaults["answer_hint_value"])
        annotation_hint = str(prompt_defaults["annotation_hint_source_rank_metric"])
        json_example = str(prompt_defaults["json_example_source_rank_metric"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_value"])
    object_description_template = str(prompt_defaults["object_description_mixed_dashboard"])
    object_description = object_description_template.format(
        panel_count=int(len(dataset.panels)),
        category_count=int(len(dataset.categories)),
        panel_name_list=_join_quoted_labels([str(panel.name) for panel in dataset.panels]),
        panel_kind_list=_join_labels([str(panel.kind) for panel in dataset.panels]),
    )
    slots: Dict[str, str] = {
        "object_description": str(object_description),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(answer_hint),
        "annotation_hint": str(annotation_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "unanswerable_instruction": str(prompt_defaults.get("unanswerable_instruction", "")),
    }
    for key, value in dataset.query.params.items():
        if isinstance(value, (str, int, float)):
            slots[str(key)] = str(value)
    return slots


def _annotation_records(
    *,
    annotation_refs: Sequence[Tuple[str, str]],
    rendered: _Rendered,
    panels_by_id: Mapping[str, _Panel],
    categories_by_id: Mapping[str, _Category],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for panel_id, category_id in annotation_refs:
        records.append(
            {
                "panel_id": str(panel_id),
                "panel_name": str(panels_by_id[str(panel_id)].name),
                "category_id": str(category_id),
                "category_label": str(categories_by_id[str(category_id)].label),
                "point_xy": list(rendered.support_points_px[str(panel_id)][str(category_id)]),
                "bbox_xyxy": list(rendered.support_bboxes_px[str(panel_id)][str(category_id)]),
            }
        )
    return records


def _build_annotation_payload(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    panels_by_id: Mapping[str, _Panel],
    categories_by_id: Mapping[str, _Category],
) -> Tuple[TypedValue, Dict[str, Any], List[Tuple[str, str]]]:
    annotation_refs = [(str(panel_id), str(category_id)) for panel_id, category_id in dataset.query.annotation_refs]
    annotation_records = _annotation_records(
        annotation_refs=annotation_refs,
        rendered=rendered,
        panels_by_id=panels_by_id,
        categories_by_id=categories_by_id,
    )
    query_id = str(dataset.query.query_id)

    if query_id in {"source_rank_target_value", "source_rank_difference_value"}:
        keyed_points = {
            "source_panel": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
            "target_panel": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
        }
        return (
            TypedValue(type="keyed_point_map", value=dict(keyed_points)),
            {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_points),
                "pixel_keyed_point_map": dict(keyed_points),
                "annotation_refs": annotation_records,
            },
            annotation_refs,
        )

    if query_id == "dual_source_target_sum_value":
        keyed_points = {
            "first_source_panel": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
            "second_source_panel": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
            "target_first_category": list(rendered.support_points_px[annotation_refs[2][0]][annotation_refs[2][1]]),
            "target_second_category": list(rendered.support_points_px[annotation_refs[3][0]][annotation_refs[3][1]]),
        }
        return (
            TypedValue(type="keyed_point_map", value=dict(keyed_points)),
            {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_points),
                "pixel_keyed_point_map": dict(keyed_points),
                "annotation_refs": annotation_records,
            },
            annotation_refs,
        )

    if query_id in {"panel_gap_extremum_category_label", "shared_label_rank_gap_extremum"}:
        keyed_points = (
            {
                "first_panel": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
                "second_panel": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
            }
            if len(annotation_refs) == 2
            else {}
        )
        return (
            TypedValue(type="keyed_point_map", value=dict(keyed_points)),
            {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_points),
                "pixel_keyed_point_map": dict(keyed_points),
                "annotation_refs": annotation_records,
            },
            annotation_refs,
        )

    if query_id == "statement_option_selection_label":
        keyed_points = {
            "first_mark": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
            "second_mark": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
        }
        return (
            TypedValue(type="keyed_point_map", value=dict(keyed_points)),
            {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_points),
                "pixel_keyed_point_map": dict(keyed_points),
                "annotation_refs": annotation_records,
            },
            annotation_refs,
        )

    point_set = [
        list(rendered.support_points_px[str(panel_id)][str(category_id)])
        for panel_id, category_id in annotation_refs
    ]
    return (
        TypedValue(type="point_set", value=list(point_set)),
        {
            "type": "point_set",
            "point_set": list(point_set),
            "pixel_point_set": list(point_set),
            "annotation_refs": annotation_records,
        },
        annotation_refs,
    )


class ChartsDashboardCrossPanelQueryTask:
    """Generate mixed-dashboard cross-panel chart questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "dashboard"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        shared_gen_defaults, _, _ = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        )
        task_gen_defaults, _, _ = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            task_id=str(self.task_id),
        )
        task_override_params = {
            str(key): value
            for key, value in task_gen_defaults.items()
            if shared_gen_defaults.get(str(key)) != value
        }
        effective_params = dict(task_override_params)
        effective_params.update(dict(params))
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=dict(effective_params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}") from last_error

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        params = {**dict(params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        dataset = _build_dataset(params, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_dashboard(
            background,
            dataset=dataset,
            render_params=render_params,
            params=params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_value",
                "answer_hint_count",
                "answer_hint_label",
                "answer_hint_option_letter",
                "annotation_hint_source_rank_metric",
                "annotation_hint_dual_source_target_sum",
                "annotation_hint_count",
                "annotation_hint_label",
                "annotation_hint_shared_label_pair",
                "annotation_hint_statement_option",
                "json_example_source_rank_metric",
                "json_example_dual_source_target_sum",
                "json_example_count",
                "json_example_label",
                "json_example_statement_option",
                "json_example_answer_only_value",
                "json_example_answer_only_count",
                "json_example_answer_only_label",
                "json_example_answer_only_option_letter",
                "object_description_mixed_dashboard",
                "unanswerable_instruction",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        panels_by_id = {str(panel.panel_id): panel for panel in dataset.panels}
        categories_by_id = {str(category.category_id): category for category in dataset.categories}
        annotation_gt, projected_annotation, annotation_refs = _build_annotation_payload(
            dataset=dataset,
            rendered=rendered,
            panels_by_id=panels_by_id,
            categories_by_id=categories_by_id,
        )
        values_by_panel = {
            str(panel.panel_id): {
                "panel_name": str(panel.name),
                "panel_kind": str(panel.kind),
                "values_by_category_id": {
                    str(category_id): int(value)
                    for category_id, value in panel.values_by_category_id.items()
                },
                "values_by_category_label": {
                    str(categories_by_id[str(category_id)].label): int(value)
                    for category_id, value in panel.values_by_category_id.items()
                },
            }
            for panel in dataset.panels
        }
        category_records = [
            {
                "category_id": str(category.category_id),
                "label": str(category.label),
                "color_rgb": list(category.color_rgb),
            }
            for category in dataset.categories
        ]
        panel_records = [
            {
                "panel_id": str(panel.panel_id),
                "panel_kind": str(panel.kind),
                "panel_name": str(panel.name),
            }
            for panel in dataset.panels
        ]
        context_params = _resolve_context_text_params(params)
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.categories) * len(dataset.panels), [15, 64]),
                "reasoning_load": clamp_unit_interval(_REASONING_LOAD_BY_VARIANT[str(dataset.query.query_id)]),
                "scene_variant_load": clamp_unit_interval(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_mixed_dashboard",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "annotation_refs": [list(ref) for ref in annotation_refs],
                    "answerability": str(dataset.query.params.get("answerability", "answerable")),
                    **(
                        {"absence_proof": dict(dataset.query.params["absence_proof"])}
                        if str(dataset.query.params.get("answerability")) == "unanswerable"
                        else {}
                    ),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(dataset.query.params),
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "panel_count": int(len(dataset.panels)),
                "category_count": int(len(dataset.categories)),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(render_params.font_family),
                },
                "context_text_layer": context_text_layer_metadata(
                    [],
                    enabled=bool(rendered.context_text_layout.get("enabled", True)),
                    layout_mode=f"{rendered.context_text_layout.get('layout_mode', 'reserved_context')}:{rendered.context_text_layout.get('placement', 'none')}",
                    layout_spec=dict(rendered.context_text_layout),
                )
                | {
                    "element_count": int(len(rendered.context_text_elements)),
                    "elements": [dict(element) for element in rendered.context_text_elements],
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bboxes_px": _bbox_map_to_json(rendered.panel_bboxes_px),
                "support_bboxes_px": _nested_bbox_map_to_json(rendered.support_bboxes_px),
                "support_points_px": _nested_point_map_to_json(rendered.support_points_px),
                "value_label_bboxes_px": _nested_bbox_map_to_json(rendered.value_label_bboxes_px),
                "option_statement_bboxes_px": _bbox_map_to_json(rendered.option_statement_bboxes_px),
                "context_text_bboxes_px": {
                    str(element["context_id"]): [int(value) for value in element["bbox_xyxy"]]
                    for element in rendered.context_text_elements
                },
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "dashboard_cross_panel_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "category_count": int(len(dataset.categories)),
                "panel_count": int(len(dataset.panels)),
                "categories": list(category_records),
                "panels": list(panel_records),
                "panel_order": [str(panel.panel_id) for panel in dataset.panels],
                "panel_kinds": [str(panel.kind) for panel in dataset.panels],
                "values_by_panel": dict(values_by_panel),
                "annotation_refs": [list(ref) for ref in annotation_refs],
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "dashboard_cross_panel_witness",
                "annotation_refs": [list(ref) for ref in annotation_refs],
                "answer": answer_value,
                "answerability": str(dataset.query.params.get("answerability", "answerable")),
                **(
                    {"absence_proof": dict(dataset.query.params["absence_proof"])}
                    if str(dataset.query.params.get("answerability")) == "unanswerable"
                    else {}
                ),
            },
            "projected_annotation": dict(projected_annotation),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
