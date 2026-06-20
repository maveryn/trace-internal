"""Public task for `task_charts__part_whole__positional_segment_share_sum`."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import finish_part_whole_plan, run_part_whole_task, sample_part_whole_base
from .shared.defaults import DOMAIN, SAMPLING_NAMESPACE
from .shared.sampling import sample_positional_segments


SUPPORTED_QUERY_IDS = (
    "clockwise_offset_pair",
    "counterclockwise_offset_pair",
    "clockwise_opposite_pair",
    "counterclockwise_opposite_pair",
)


def _build_plan(params, instance_seed: int, selected: str, _probabilities):
    """Bind a circular positional relation and sum the selected segment shares."""

    branch = str(selected)
    relation = "opposite_neighbor_sum" if "opposite" in branch else "anchor_offset_sum"
    direction = "counterclockwise" if branch.startswith("counter") else "clockwise"
    base = sample_part_whole_base(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.positional.category_count.{relation}",
        min_key="positional_category_count_min",
        max_key="positional_category_count_max",
        fallback_min=4,
        fallback_max=6,
        even_only=str(relation) == "opposite_neighbor_sum",
    )
    selected_categories, anchor_labels, position_extras = sample_positional_segments(
        base.categories,
        relation=str(relation),
        direction=str(direction),
        params=params,
        count_params=base.count_params,
        instance_seed=int(instance_seed),
    )
    answer_value = int(sum(int(category.value) for category in selected_categories))
    extras = {
        **dict(base.base_extras),
        **dict(position_extras),
        "selected_share_value": int(answer_value),
    }
    return finish_part_whole_plan(
        base=base,
        selected=str(selected),
        instance_seed=int(instance_seed),
        answer_value=int(answer_value),
        annotation_labels=tuple(str(label) for label in anchor_labels)
        + tuple(str(category.label) for category in selected_categories),
        trace_extras=dict(extras),
    )


@register_task
class ChartsCompositionChartPositionalSegmentShareSumTask:
    """Return the share sum selected by a circular positional instruction."""

    task_id = "task_charts__part_whole__positional_segment_share_sum"
    domain = DOMAIN
    objective_contract = "positional_segment_share_sum"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    default_dataset_enabled = True
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Select positional branch and return a generated part-whole instance."""

        return run_part_whole_task(self, int(instance_seed), dict(params), int(max_attempts))


__all__ = ["ChartsCompositionChartPositionalSegmentShareSumTask"]
