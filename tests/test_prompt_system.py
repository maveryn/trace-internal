"""Tests for prompt bundle loading/rendering."""

from __future__ import annotations

import pytest

from trace.core.prompts import load_prompt_bundle, render_prompt, render_prompt_variants


def test_render_prompt_is_deterministic() -> None:
    a = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="measurement_value_query",
        query_type="closest_to_x",
        slots={
            "candidate_count": 7,
            "entity_plural": "angles",
            "value_name_singular": "angle",
            "unit_name": "degrees",
            "evidence_single": "the selected angle vertex",
            "evidence_pair": "ordered vertices [largest, smallest]",
            "evidence_hint": "the selected angle vertex",
            "target_x": 90,
        },
        instance_seed=4242,
    )
    b = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="measurement_value_query",
        query_type="closest_to_x",
        slots={
            "candidate_count": 7,
            "entity_plural": "angles",
            "value_name_singular": "angle",
            "unit_name": "degrees",
            "evidence_single": "the selected angle vertex",
            "evidence_pair": "ordered vertices [largest, smallest]",
            "evidence_hint": "the selected angle vertex",
            "target_x": 90,
        },
        instance_seed=4242,
    )
    assert a.prompt == b.prompt
    assert a.metadata == b.metadata
    assert a.metadata["slot_values"]["target_x"] == 90
    assert a.metadata["answer_or_evidence_key"] == "answer_and_evidence"
    assert "integer answer" in a.prompt


def test_required_prompt_slots_enforced() -> None:
    with pytest.raises(ValueError):
        render_prompt(
            domain="geometry",
            task_group="measurement",
            bundle_id="geometry_measurement_v1",
            task_type_key="measurement_value_query",
            query_type="closest_to_x",
            slots={"candidate_count": 7, "entity_plural": "angles"},
            instance_seed=9999,
        )


def test_render_prompt_variants_contains_answer_only_and_answer_and_evidence() -> None:
    results = render_prompt_variants(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="measurement_value_query",
        query_type="min",
        answer_or_evidence_keys=("answer_only", "answer_and_evidence"),
        slots={
            "candidate_count": 7,
            "entity_plural": "angles",
            "value_name_singular": "angle",
            "unit_name": "degrees",
            "evidence_hint": "the selected angle vertex",
        },
        instance_seed=4242,
    )
    assert sorted(results.keys()) == ["answer_and_evidence", "answer_only"]
    assert "evidence" not in results["answer_only"].prompt.lower()
    assert "evidence" in results["answer_and_evidence"].prompt.lower()
    assert results["answer_only"].metadata["answer_or_evidence_key"] == "answer_only"
    assert results["answer_and_evidence"].metadata["answer_or_evidence_key"] == "answer_and_evidence"


def test_bundle_contains_required_variant_counts() -> None:
    bundle = load_prompt_bundle("tile", "path", "tile_path_v1")
    assert len(bundle.task_type_templates["maze_path"]) >= 10
    assert len(bundle.query_type_templates["shortest_path"]) >= 10
    assert len(bundle.answer_or_evidence_templates["answer_only"]) >= 10
    assert len(bundle.answer_or_evidence_templates["answer_and_evidence"]) >= 10
