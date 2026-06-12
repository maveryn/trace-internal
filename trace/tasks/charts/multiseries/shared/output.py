
from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.multiseries.shared.comparison_common import (
    SCENE_VARIANT_LOADS,
    normalize_multiseries_visual_scan,
)
from trace.tasks.charts.multiseries.shared.runtime import (
    MultiseriesRenderResult,
    render_map_payload,
    render_spec_payload,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec




def build_trace_payload(
    *,
    result: MultiseriesRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    scene_variant: str,
    variant_family: str,
    internal_query_id: str,
    answer_value: Any,
    question_format: str,
    trace_extras: Mapping[str, Any],
    relations_extra: Mapping[str, Any],
    query_params_extra: Mapping[str, Any],
    execution_extra: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
) -> dict[str, Any]:
    relation_payload = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "variant_family": str(variant_family),
        "internal_query_id": str(internal_query_id),
        **dict(relations_extra),
    }
    query_params = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "variant_family": str(variant_family),
        "internal_query_id": str(internal_query_id),
        "series_count": int(trace_extras["series_count"]),
        "series_count_range": list(trace_extras["series_count_range"]),
        "category_count": int(trace_extras["category_count"]),
        "category_count_range": list(trace_extras["category_count_range"]),
        "queried_series_labels": list(trace_extras.get("queried_series_labels", [])),
        **dict(query_params_extra),
    }
    execution_trace = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "variant_family": str(variant_family),
        "internal_query_id": str(internal_query_id),
        "category_labels": list(result.category_labels),
        "series_labels": list(result.series_labels),
        "queried_series_labels": list(trace_extras.get("queried_series_labels", [])),
        "series_count": int(trace_extras["series_count"]),
        "series_count_range": list(trace_extras["series_count_range"]),
        "category_count": int(trace_extras["category_count"]),
        "category_count_range": list(trace_extras["category_count_range"]),
        "value_range": list(trace_extras.get("value_range", [])),
        "values_by_category": dict(trace_extras.get("values_by_category", {})),
        "question_format": str(question_format),
        "mark_color_sampling_policy": str(result.mark_style["sampling_policy"]),
        **dict(execution_extra),
        **{str(key): value for key, value in result.mark_style.items() if key != "sampling_policy"},
    }
    return {
        "scene_ir": {
            "scene_kind": f"chart_{str(scene_variant)}_multiseries",
            "entities": [dict(entity) for entity in result.rendered_scene.entities],
            "relations": relation_payload,
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=query_params,
        ),
        "render_spec": render_spec_payload(result, scene_variant=str(scene_variant)),
        "render_map": render_map_payload(result),
        "execution_trace": execution_trace,
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
    }


