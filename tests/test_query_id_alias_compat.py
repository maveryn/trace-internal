"""Regression tests for canonical query_id and legacy query_variant inputs."""

from __future__ import annotations

from random import Random

import pytest

from trace.tasks.charts.shared.fixed_query_task import merged_query_params
from trace.tasks.games.shared.sampling import resolve_games_query_id
from trace.tasks.icons.shared.paired_canvas_common import choose_query_id
from trace.tasks.shared.fixed_query import (
    force_query_id_params,
    normalize_query_id_params,
)
from trace.tasks.three_d.shared.task_support import resolve_axis_variant


def test_normalize_query_id_params_accepts_legacy_query_variant() -> None:
    params = normalize_query_id_params(
        {
            "query_variant": "second",
            "query_variant_weights": {"first": 0.0, "second": 1.0},
        }
    )

    assert params["query_id"] == "second"
    assert params["query_id_weights"] == {"first": 0.0, "second": 1.0}
    assert "query_variant" not in params
    assert "query_variant_weights" not in params


def test_normalize_query_id_params_rejects_conflicting_aliases() -> None:
    with pytest.raises(ValueError, match="query_id conflicts with query_variant"):
        normalize_query_id_params({"query_id": "first", "query_variant": "second"})


def test_force_query_id_params_checks_legacy_alias_conflicts() -> None:
    forced = force_query_id_params(
        {"query_variant": "second", "query_variant_weights": {"second": 1.0}},
        query_id="second",
    )

    assert forced["query_id"] == "second"
    assert forced["query_id_weights"] == {"second": 1.0}
    assert "query_variant" not in forced
    assert "query_variant_weights" not in forced
    with pytest.raises(ValueError, match="public task query_id must match"):
        force_query_id_params({"query_variant": "first"}, query_id="second")


def test_games_query_resolver_honors_legacy_query_variant() -> None:
    query_id, probabilities = resolve_games_query_id(
        task_id="test_games_query_alias",
        instance_seed=123,
        params={"query_variant": "second"},
        gen_defaults={},
        supported_variants=("first", "second"),
    )

    assert query_id == "second"
    assert probabilities == {"first": 0.0, "second": 1.0}


def test_merged_chart_params_honor_legacy_query_variant_without_leaking_it() -> None:
    params = merged_query_params(
        {"query_variant": "second"},
        allowed_query_ids=("first", "second"),
    )

    assert params["query_id"] == "second"
    assert "query_variant" not in params
    with pytest.raises(ValueError, match="query_id conflicts with query_variant"):
        merged_query_params(
            {"query_id": "first", "query_variant": "second"},
            allowed_query_ids=("first", "second"),
        )


def test_paired_canvas_query_resolver_honors_legacy_query_variant() -> None:
    query_id, probabilities = choose_query_id(
        Random(0),
        params={"query_variant": "second"},
        gen_defaults={},
        instance_seed=123,
        task_id="test_icons_query_alias",
        query_ids=("first", "second"),
        weight_key="query_id_weights",
    )

    assert query_id == "second"
    assert probabilities == {"first": 0.0, "second": 1.0}


def test_three_d_axis_resolver_honors_legacy_query_variant() -> None:
    query_id, probabilities = resolve_axis_variant(
        {"query_variant": "second"},
        task_id="test_three_d_query_alias",
        gen_defaults={},
        instance_seed=123,
        supported_variants=("first", "second"),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )

    assert query_id == "second"
    assert probabilities == {"first": 0.0, "second": 1.0}
