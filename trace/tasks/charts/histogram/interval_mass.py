"""Public task for `task_charts__histogram__interval_mass`."""

from __future__ import annotations

from trace.tasks.charts.histogram._lifecycle import (
    make_histogram_task_plan,
    run_histogram_lifecycle,
)
from trace.tasks.charts.histogram.shared.defaults import DOMAIN
from trace.tasks.charts.histogram.shared.rendering import resolve_mark_style
from trace.tasks.charts.histogram.shared.sampling import build_histogram_dataset
from trace.tasks.registry import register_task


TASK_ID = "task_charts__histogram__interval_mass"
OBJECTIVE_CONTRACT = "interval_mass"
PROMPT_QUERY_KEY = "interval_mass"
INSIDE_QUERY_ID = "inside_interval_mass"
OUTSIDE_QUERY_ID = "outside_interval_mass"
SUPPORTED_QUERY_IDS = (INSIDE_QUERY_ID, OUTSIDE_QUERY_ID)
DEFAULT_QUERY_ID = INSIDE_QUERY_ID
DATASET_VARIANT_BY_QUERY_ID = {
    INSIDE_QUERY_ID: "interval_mass",
    OUTSIDE_QUERY_ID: "outside_interval_mass",
}
RELATION_BY_QUERY_ID = {
    INSIDE_QUERY_ID: "inside",
    OUTSIDE_QUERY_ID: "outside",
}


def _build_interval_mass_plan(params, instance_seed, selected_query_id, query_probabilities):
    """Bind the interval-mass objective before neutral rendering."""

    if str(selected_query_id) not in DATASET_VARIANT_BY_QUERY_ID:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query_id}")
    dataset_variant = str(DATASET_VARIANT_BY_QUERY_ID[str(selected_query_id)])
    interval_relation = str(RELATION_BY_QUERY_ID[str(selected_query_id)])
    mark_style = resolve_mark_style(params, instance_seed=int(instance_seed), mark_count=1)
    bins, answer_value, annotation_labels, trace_extras = build_histogram_dataset(
        dataset_variant=dataset_variant,
        params=dict(params),
        instance_seed=int(instance_seed),
        mark_style=mark_style,
    )
    counts_by_label = {str(bin_spec.label): int(bin_spec.count) for bin_spec in bins}
    if int(answer_value) != sum(int(counts_by_label[str(label)]) for label in annotation_labels):
        raise RuntimeError("histogram interval-mass objective lost answer/annotation alignment")
    return make_histogram_task_plan(
        bins=bins,
        params=dict(params),
        mark_style=mark_style,
        answer_value=int(answer_value),
        answer_type="integer",
        question_format="numeric_open",
        annotation_type="bbox_set",
        annotation_labels=tuple(str(label) for label in annotation_labels),
        prompt_query_key=PROMPT_QUERY_KEY,
        dataset_variant=dataset_variant,
        trace_extras={**dict(trace_extras), "interval_relation": interval_relation},
        query_probabilities=query_probabilities,
        objective_contract=OBJECTIVE_CONTRACT,
        dynamic_slots={
            "query_interval_label": str(trace_extras.get("query_interval_label", "")),
            "interval_relation_phrase": interval_relation,
        },
        instance_seed=int(instance_seed),
    )


class ChartsDistributionHistogramIntervalMassTask:
    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = OBJECTIVE_CONTRACT
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return run_histogram_lifecycle(
            task=self,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            default_query_id=DEFAULT_QUERY_ID,
            build_plan=_build_interval_mass_plan,
        )
register_task(ChartsDistributionHistogramIntervalMassTask)
