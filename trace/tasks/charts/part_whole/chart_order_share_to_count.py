from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import finish_part_whole_plan, run_part_whole_task, sample_part_whole_base
from .shared.defaults import DOMAIN, SAMPLING_NAMESPACE
from .shared.sampling import (
    count_from_share,
    sample_chart_order_span,
    sample_total_count,
)


SUPPORTED_QUERY_IDS = ("clockwise_share_to_count", "counterclockwise_share_to_count")


def _build_plan(params, instance_seed: int, selected: str, _probabilities):
    # Bind one ordered span, expose total count, and convert share to count.
    direction = "counterclockwise" if str(selected).startswith("counter") else "clockwise"
    base = sample_part_whole_base(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.share_to_count.category_count",
        min_key="part_whole_category_count_min",
        max_key="part_whole_category_count_max",
        fallback_min=3,
        fallback_max=5,
    )
    selected_categories, span_extras = sample_chart_order_span(
        base.categories,
        direction=direction,
        params=params,
        count_params=base.count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.share_to_count.{direction}",
        min_key="part_whole_span_count_min",
        max_key="part_whole_span_count_max",
        fallback_min=2,
        fallback_max=3,
    )
    total_count = sample_total_count(params=params, count_params=base.count_params, instance_seed=int(instance_seed))
    answer_value = count_from_share(int(total_count), int(span_extras["selected_share_value"]))
    extras = {
        **dict(base.base_extras),
        **dict(span_extras),
        "category_list": [str(category.label) for category in selected_categories],
        "total_count": int(total_count),
        "calculation": "convert_contiguous_circular_chart_order_share_to_count",
    }
    return finish_part_whole_plan(
        base=base,
        selected=selected,
        instance_seed=int(instance_seed),
        answer_value=int(answer_value),
        annotation_labels=tuple(str(category.label) for category in selected_categories) + ("__total__",),
        trace_extras=extras,
    )


@register_task
class ChartsCompositionChartOrderShareToCountTask:
    task_id = "task_charts__part_whole__chart_order_share_to_count"
    domain = DOMAIN
    objective_contract = "chart_order_share_to_count"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    default_dataset_enabled = True
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_part_whole_task(self, int(instance_seed), dict(params), int(max_attempts))


__all__ = ["ChartsCompositionChartOrderShareToCountTask"]
