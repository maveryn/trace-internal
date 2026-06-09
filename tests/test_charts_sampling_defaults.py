"""Tests for shared chart sampling/default helpers."""

from __future__ import annotations

from trace.tasks.charts.shared.sampling_defaults import (
    balanced_int_from_support,
    decouple_sample_cursor_for_axis_lengths,
    public_task_param_overrides,
    resolve_chart_axis_variant,
    support_sampling_params_for_uniform_query_cycle,
    uses_uniform_query_id_cycle,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index


def test_public_task_param_overrides_merges_generation_then_rendering() -> None:
    defaults = {
        "generation": {"task_overrides": {"task_a": {"alpha": 1, "shared": "generation"}}},
        "rendering": {"task_overrides": {"task_a": {"beta": 2, "shared": "rendering"}}},
        "prompt": {"task_overrides": {"task_a": {"ignored": True}}},
    }

    assert public_task_param_overrides(defaults, "task_a") == {
        "alpha": 1,
        "beta": 2,
        "shared": "rendering",
    }
    assert public_task_param_overrides(defaults, "missing") == {}


def test_uniform_query_cycle_detection_respects_overrides_and_weights() -> None:
    probabilities = {"a": 0.5, "b": 0.5}
    supported = ("a", "b")

    assert uses_uniform_query_id_cycle(
        {},
        gen_defaults={"balanced_query_id_sampling": True},
        query_id_probabilities=probabilities,
        supported_query_ids=supported,
    )
    assert not uses_uniform_query_id_cycle(
        {"query_id": "a"},
        gen_defaults={"balanced_query_id_sampling": True},
        query_id_probabilities=probabilities,
        supported_query_ids=supported,
    )
    assert not uses_uniform_query_id_cycle(
        {},
        gen_defaults={"balanced_query_id_sampling": False},
        query_id_probabilities=probabilities,
        supported_query_ids=supported,
    )
    assert not uses_uniform_query_id_cycle(
        {},
        gen_defaults={"balanced_query_id_sampling": True},
        query_id_probabilities={"a": 1.0, "b": 0.0},
        supported_query_ids=supported,
    )


def test_support_sampling_params_decouples_sample_cursor_only_for_uniform_query_cycle() -> None:
    params = {"_sample_cursor": 9}
    probabilities = {"a": 0.5, "b": 0.5}
    supported = ("a", "b")

    assert support_sampling_params_for_uniform_query_cycle(
        params,
        gen_defaults={"balanced_query_id_sampling": True},
        query_id_probabilities=probabilities,
        supported_query_ids=supported,
    )["_sample_cursor"] == 4
    assert support_sampling_params_for_uniform_query_cycle(
        {**params, "query_id": "a"},
        gen_defaults={"balanced_query_id_sampling": True},
        query_id_probabilities=probabilities,
        supported_query_ids=supported,
    )["_sample_cursor"] == 9


def test_decouple_sample_cursor_for_axis_lengths_preserves_explicit_policy() -> None:
    axes = (
        (2, ("query_id", "query_id_weights")),
        (3, ("statistic_kind", "statistic_kind_weights")),
    )

    assert decouple_sample_cursor_for_axis_lengths({"_sample_cursor": 23}, axes=axes)["_sample_cursor"] == 3
    assert decouple_sample_cursor_for_axis_lengths({"_sample_cursor": 23, "query_id": None}, axes=axes)[
        "_sample_cursor"
    ] == 7
    assert decouple_sample_cursor_for_axis_lengths(
        {"_sample_cursor": 23, "query_id": None},
        axes=axes,
        explicit_policy="non_null",
    )["_sample_cursor"] == 3
    assert decouple_sample_cursor_for_axis_lengths(
        {"_sample_cursor": -23},
        axes=axes,
        use_abs=True,
    )["_sample_cursor"] == 3


def test_balanced_int_from_support_preserves_ordered_support_selection() -> None:
    support = (30, 10, 20)
    namespace = "charts.test.support"
    seed = 987
    expected_index = resolve_selection_index(params={}, instance_seed=seed, namespace=namespace) % len(support)

    assert balanced_int_from_support(support, params={}, instance_seed=seed, namespace=namespace) == support[expected_index]


def test_resolve_chart_axis_variant_is_available_from_sampling_defaults() -> None:
    selected, probabilities = resolve_chart_axis_variant(
        params={"query_id": "b"},
        gen_defaults={},
        instance_seed=12,
        supported_variants=("a", "b"),
        task_id="charts_test_task",
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )

    assert selected == "b"
    assert probabilities == {"a": 0.0, "b": 1.0}
