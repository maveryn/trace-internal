"""Table ranking task that returns the kth highest or lowest row label in one numeric column."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.seed import spawn_rng
from trace.core.task_group_config import get_task_group_defaults
from trace.core.types import TaskComplexity, TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.charts.shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from trace.tasks.charts.shared.label_assets import resolve_chart_entity_labels
from trace.tasks.charts.shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from trace.tasks.shared.text_rendering import temporary_default_font_family
from trace.tasks.charts.table.shared.table_common import (
    SUPPORTED_TABLE_SCENE_VARIANTS,
    TableDefaults,
    build_ranking_label_dataset_for_variant,
    projected_table_region_bbox_annotation,
    resolve_table_axis_variant,
    resolve_table_render_params,
    table_render_style_spec,
)
from trace.tasks.charts.table.shared.table_scene import render_table_scene
from trace.tasks.charts.table.shared.visual_defaults import (
    load_table_background_defaults,
    load_table_noise_defaults,
    sample_table_font_family,
    table_font_asset_metadata,
)


TASK_ID = "task_charts__table__column_rank_label"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("kth_rank_in_column",)
_SOURCE_QUERY_IDS: Tuple[str, ...] = ("kth_highest_in_column", "kth_lowest_in_column")
_SUPPORTED_RANK_DIRECTIONS: Tuple[str, ...] = ("highest", "lowest")

_DEFAULTS = TableDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "table_ranking")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_table_background_defaults(task_group="ranking")
POST_IMAGE_NOISE_DEFAULTS = load_table_noise_defaults(task_group="ranking", apply_prob=0.0)


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic table ranking variant."""

    explicit_variant = params.get("query_id")
    if explicit_variant is not None and str(explicit_variant).strip().lower() in set(_SOURCE_QUERY_IDS):
        return "kth_rank_in_column", {"kth_rank_in_column": 1.0}
    return resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_rank_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve highest-vs-lowest rank direction inside the merged ranking variant."""

    explicit_variant = params.get("query_id")
    source_direction = None
    if explicit_variant is not None:
        normalized_variant = str(explicit_variant).strip().lower()
        if normalized_variant == "kth_highest_in_column":
            source_direction = "highest"
        elif normalized_variant == "kth_lowest_in_column":
            source_direction = "lowest"
    explicit_direction = params.get("rank_direction")
    if explicit_direction is not None:
        direction = str(explicit_direction).strip().lower()
        if direction not in set(_SUPPORTED_RANK_DIRECTIONS):
            raise ValueError(f"unsupported rank_direction for {TASK_ID}: {explicit_direction}")
        if source_direction is not None and str(source_direction) != str(direction):
            raise ValueError("query_id ranking alias conflicts with explicit rank_direction")
        return str(direction), {
            str(value): (1.0 if str(value) == str(direction) else 0.0)
            for value in _SUPPORTED_RANK_DIRECTIONS
        }
    if source_direction is not None:
        return str(source_direction), {
            str(value): (1.0 if str(value) == str(source_direction) else 0.0)
            for value in _SUPPORTED_RANK_DIRECTIONS
        }
    direction, probabilities = resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_RANK_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="rank_direction",
        weights_key="rank_direction_weights",
        balance_flag_key="balanced_rank_direction_sampling",
        axis_namespace="rank_direction",
    )
    return str(direction), dict(probabilities)


def _internal_rank_variant(rank_direction: str) -> str:
    """Map public rank direction to the construction variant."""

    if str(rank_direction) == "highest":
        return "kth_highest_in_column"
    if str(rank_direction) == "lowest":
        return "kth_lowest_in_column"
    raise ValueError(f"unsupported rank_direction for {TASK_ID}: {rank_direction}")


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual table scene variant."""

    return resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_TABLE_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _format_ordinal(value: int) -> str:
    """Return a short English ordinal string like 2nd or 3rd."""

    number = int(value)
    if 10 <= (number % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class TablesRankingLabelTask:
    """Return the kth highest or kth lowest row label in one queried numeric column."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "table_ranking"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        rank_direction, rank_direction_probabilities = _resolve_rank_direction(params, instance_seed=int(instance_seed))
        internal_query_id = _internal_rank_variant(str(rank_direction))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_ranking_label_dataset_for_variant(
            query_id=str(internal_query_id),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        is_unanswerable = should_use_unanswerable_branch(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.kth_rank_in_column",
            enabled=bool(getattr(self, "supports_unanswerable", False)),
        )
        if is_unanswerable:
            visible_columns = [str(header) for header in dataset["column_headers"]]
            missing_column = choose_missing_label(
                visible_labels=visible_columns,
                candidate_labels=resolve_chart_entity_labels(
                    spawn_rng(int(instance_seed), f"{TASK_ID}.missing_column_candidates"),
                    count=max(16, len(visible_columns) + 8),
                    min_chars=2,
                    max_chars=7,
                    allow_spaces=False,
                ).labels,
                fallback_prefix="Column ",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.missing_column",
            )
            dataset = {
                **dict(dataset),
                "query_column": str(missing_column),
                "query_column_index": -1,
                "answer_row_label": UNANSWERABLE_ANSWER,
                "answer_row_index": -1,
                "answer_value": None,
                "is_unanswerable": True,
                "absence_proof": absence_proof(
                    requested_item=str(missing_column),
                    visible_candidates=visible_columns,
                    checked_scope="table column headers",
                    absence_reason="requested column header is not visible in the table",
                ),
            }
        else:
            dataset = {**dict(dataset), "is_unanswerable": False, "absence_proof": {}}

        render_params = resolve_table_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        table_font_family = sample_table_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.table_font",
            params=params,
        )
        with temporary_default_font_family(str(table_font_family)):
            rendered_scene = render_table_scene(
                background,
                scene_variant=str(scene_variant),
                row_labels=list(dataset["row_labels"]),
                column_headers=list(dataset["column_headers"]),
                values_by_row=dict(dataset["values_by_row"]),
                render_params=render_params,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_spreadsheet",
                "object_description_zebra",
                "object_description_ledger",
                "object_description_card_table",
                "annotation_hint_kth_rank_in_column",
                "json_example_kth_rank_in_column",
                "json_example_answer_only_kth_rank_in_column",
                "unanswerable_instruction",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])

        prompt_selection = render_task_prompt_variants(
            domain=str(getattr(self, "prompt_domain", self.domain)),
            task_group=str(getattr(self, "prompt_task_group", self.task_group)),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "query_column": str(dataset["query_column"]),
                "query_rank": _format_ordinal(int(dataset["query_rank"])),
                "rank_direction": str(rank_direction),
                "unanswerable_instruction": (
                    str(prompt_defaults["unanswerable_instruction"])
                    if bool(getattr(self, "supports_unanswerable", False))
                    else ""
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        query_column = str(dataset["query_column"])
        if bool(dataset["is_unanswerable"]):
            annotation_bboxes = []
        else:
            annotation_projection = projected_table_region_bbox_annotation(
                rendered_scene,
                column_headers=[str(query_column)],
            )
            annotation_bboxes = [
                [round(float(value), 3) for value in bbox]
                for bbox in annotation_projection["bbox_set"]
            ]
        answer_row_label = str(dataset["answer_row_label"])
        answer_gt = TypedValue(type="string", value=str(answer_row_label))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in dataset["values_by_row"].items()
        }
        cell_bbox_map = {
            str(cell_trace["cell_id"]): list(cell_trace["bbox_px"])
            for cell_trace in rendered_scene.cell_traces
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"table_{str(scene_variant)}_ranking",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "query_column": str(query_column),
                    "query_rank": int(dataset["query_rank"]),
                    "rank_direction": str(rank_direction),
                    "answer_row_label": str(answer_row_label),
                    "answer_value": None if dataset["answer_value"] is None else int(dataset["answer_value"]),
                    "supporting_region_kind": "column",
                    "supporting_column_header": str(query_column),
                    "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                    **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "query_column": str(query_column),
                    "query_rank": int(dataset["query_rank"]),
                    "rank_direction": str(rank_direction),
                    "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                    **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "rank_direction_probabilities": dict(rank_direction_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "row_count": int(dataset["row_count"]),
                    "numeric_column_count": int(dataset["numeric_column_count"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "font_assets": table_font_asset_metadata(str(table_font_family)),
                "table_bbox_px": list(rendered_scene.table_bbox_px),
                "table_style": table_render_style_spec(render_params),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "value_font_size_px": int(render_params.value_font_size_px),
                },
                "grid_style": {
                    "border_width_px": int(render_params.border_width_px),
                    "grid_width_px": int(render_params.grid_width_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "table_bbox_px": list(rendered_scene.table_bbox_px),
                "row_region_bboxes_px": dict(rendered_scene.row_region_bboxes),
                "column_region_bboxes_px": dict(rendered_scene.column_region_bboxes),
                "row_label_bboxes_px": dict(rendered_scene.row_label_bboxes),
                "header_bboxes_px": dict(rendered_scene.header_bboxes),
                "cell_bboxes_px": dict(cell_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
                "scene_variant": str(scene_variant),
                "query_column": str(query_column),
                "query_column_index": int(dataset["query_column_index"]),
                "query_rank": int(dataset["query_rank"]),
                "rank_direction": str(rank_direction),
                "answer_row_label": str(answer_row_label),
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_value": None if dataset["answer_value"] is None else int(dataset["answer_value"]),
                "row_labels": [str(label) for label in dataset["row_labels"]],
                "column_headers": [str(header) for header in dataset["column_headers"]],
                "values_by_row": dict(values_by_row),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
                "row_count_range": list(dataset["row_count_range"]),
                "numeric_column_count_range": list(dataset["numeric_column_count_range"]),
                "value_range": list(dataset["value_range"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "rank_direction_probabilities": dict(rank_direction_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "column_ranking_label",
                "supporting_region_kind": "column",
                "supporting_column_header": str(query_column),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
            },
        }

        complexity = TaskComplexity(
            complexity_score=float(
                0.17
                + (0.02 * int(dataset["row_count"]))
                + (0.015 * int(dataset["numeric_column_count"]))
                + (0.02 * (int(dataset["query_rank"]) - 2))
                + (0.02 if str(rank_direction) == "lowest" else 0.01)
            ),
            complexity_components={
                "query_id": str(query_id),
                "rank_direction": str(rank_direction),
                "scene_variant": str(scene_variant),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
                "query_rank": int(dataset["query_rank"]),
            },
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
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsTableKthRankInColumnLabelTask(FixedChartQueryVariantTaskMixin, TablesRankingLabelTask):
    """Return the kth highest or lowest row label in one table column."""

    task_id = "task_charts__table__column_rank_label"
    domain = "charts"
    task_group = "table_ranking"
    prompt_domain = "charts"
    prompt_task_group = "table_ranking"
    fixed_query_id = "kth_rank_in_column"
    supports_unanswerable = True


__all__ = [
    "ChartsTableKthRankInColumnLabelTask",
    "TablesRankingLabelTask",
]
