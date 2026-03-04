"""Tests for prompt bundle loading/rendering."""

from __future__ import annotations

import pytest

from trace.core.prompts import load_prompt_bundle, render_prompt


def test_render_prompt_is_deterministic() -> None:
    a = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="angle_measurement",
        query_type="closest_to_x",
        slots={"candidate_count": 7, "entity_plural": "angles", "target_x": 90},
        instance_seed=4242,
    )
    b = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="angle_measurement",
        query_type="closest_to_x",
        slots={"candidate_count": 7, "entity_plural": "angles", "target_x": 90},
        instance_seed=4242,
    )
    assert a.prompt == b.prompt
    assert a.metadata == b.metadata
    assert a.metadata["slot_values"]["target_x"] == 90


def test_required_prompt_slots_enforced() -> None:
    with pytest.raises(ValueError):
        render_prompt(
            domain="geometry",
            task_group="measurement",
            bundle_id="geometry_measurement_v1",
            task_type_key="angle_measurement",
            query_type="closest_to_x",
            slots={"candidate_count": 7, "entity_plural": "angles"},
            instance_seed=9999,
        )


def test_bundle_contains_required_variant_counts() -> None:
    bundle = load_prompt_bundle("tile", "path", "tile_path_v1")
    assert len(bundle.task_type_templates["maze_path"]) >= 10
    assert len(bundle.query_type_templates["shortest_path"]) >= 10
