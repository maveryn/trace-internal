"""Tests for prompt bundle loading/rendering."""

from __future__ import annotations

import re

import pytest

from trace.core.prompts import load_prompt_bundle, render_prompt, render_prompt_variants


def test_render_prompt_is_deterministic() -> None:
    a = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="measurement_single_object",
        query_type="measure",
        slots={
            "object_description": "a single labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "json_output_contract_answer_only": 'Return a valid JSON object with key "answer".',
            "evidence_hint": 'set "evidence" to a JSON object mapping required labels to graph-unit coordinates [x, y]',
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"evidence":{"A":[2,1],"B":[0,0],"C":[3,-1]},"answer":45}',
            "json_example_answer_only": '{"answer":45}',
        },
        instance_seed=4242,
    )
    b = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="measurement_single_object",
        query_type="measure",
        slots={
            "object_description": "a single labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "json_output_contract_answer_only": 'Return a valid JSON object with key "answer".',
            "evidence_hint": 'set "evidence" to a JSON object mapping required labels to graph-unit coordinates [x, y]',
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"evidence":{"A":[2,1],"B":[0,0],"C":[3,-1]},"answer":45}',
            "json_example_answer_only": '{"answer":45}',
        },
        instance_seed=4242,
    )
    assert a.prompt == b.prompt
    assert a.metadata == b.metadata
    assert a.metadata["slot_values"]["object_description"] == "a single labeled angle"
    assert a.metadata["answer_or_evidence_key"] == "answer_and_evidence"
    assert "Example JSON" in a.prompt


def test_prompt_bundle_contract_and_required_slots() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v1")
    assert len(bundle.task_type_templates["measurement_single_object"]) >= 10
    assert len(bundle.query_type_templates["measure"]) >= 10
    assert len(bundle.answer_or_evidence_templates["answer_only"]) >= 10
    assert len(bundle.answer_or_evidence_templates["answer_and_evidence"]) >= 10

    with pytest.raises(ValueError):
        render_prompt(
            domain="geometry",
            task_group="measurement",
            bundle_id="geometry_measurement_v1",
            task_type_key="measurement_single_object",
            query_type="measure",
            slots={"object_description": "a single polygon"},
            instance_seed=9999,
        )


def test_render_prompt_variants_contains_answer_only_and_answer_and_evidence() -> None:
    results = render_prompt_variants(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_type_key="measurement_single_object",
        query_type="measure",
        answer_or_evidence_keys=("answer_only", "answer_and_evidence"),
        slots={
            "object_description": "a single polygon",
            "question_text": "What is the area of the polygon in square units?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "json_output_contract_answer_only": 'Return a valid JSON object with key "answer".',
            "evidence_hint": 'set "evidence" to a JSON object mapping required labels to graph-unit coordinates [x, y]',
            "answer_hint": 'set "answer" to the polygon area as an integer value',
            "json_example": '{"evidence":{"A":[0,0],"B":[4,0],"C":[4,2],"D":[0,2]},"answer":8}',
            "json_example_answer_only": '{"answer":8}',
        },
        instance_seed=4242,
    )
    assert sorted(results.keys()) == ["answer_and_evidence", "answer_only"]
    assert "evidence" not in results["answer_only"].prompt.lower()
    assert "evidence" in results["answer_and_evidence"].prompt.lower()
    assert '"answer"' in results["answer_only"].prompt
    assert results["answer_only"].metadata["answer_or_evidence_key"] == "answer_only"
    assert results["answer_and_evidence"].metadata["answer_or_evidence_key"] == "answer_and_evidence"


def test_geometry_measurement_bundles_answer_templates_use_contract_and_avoid_only_just() -> None:
    banned = re.compile(r"\b(only|just)\b", flags=re.IGNORECASE)
    for bundle_id in ("geometry_angle_measure_v1", "geometry_measurement_v1"):
        bundle = load_prompt_bundle("geometry", "measurement", bundle_id)

        measure_templates = bundle.query_type_templates["measure"]
        answer_only_templates = bundle.answer_or_evidence_templates["answer_only"]
        evidence_templates = bundle.answer_or_evidence_templates["answer_and_evidence"]

        assert len(measure_templates) >= 10
        assert len(answer_only_templates) >= 10
        assert len(evidence_templates) >= 10
        assert all(str(template).strip() for template in answer_only_templates)
        assert all("{json_output_contract_answer_only}" in str(template) for template in answer_only_templates)
        assert all("{answer_hint}" in str(template) for template in answer_only_templates)
        assert all("{json_example_answer_only}" in str(template) for template in answer_only_templates)
        assert all(banned.search(str(template)) is None for template in answer_only_templates)
        assert all(banned.search(str(template)) is None for template in evidence_templates)
        assert all("{json_output_contract}" in str(template) for template in evidence_templates)
        assert all("{evidence_hint}" in str(template) for template in evidence_templates)
        assert all("{answer_hint}" in str(template) for template in evidence_templates)
        assert all("{json_example}" in str(template) for template in evidence_templates)

        if bundle_id == "geometry_angle_measure_v1":
            assert all("option" in str(template).lower() for template in measure_templates)
            assert any("option letter" in str(template).lower() for template in measure_templates)
        else:
            assert len({str(template) for template in measure_templates}) >= 10
            assert all("{question_text}" in str(template) for template in measure_templates)


def test_active_task_bundles_use_json_output_contracts_for_both_modes() -> None:
    bundle_coords = (
        ("geometry", "analytical_2d", "geometry_analytical_area_v1"),
        ("geometry", "measurement", "geometry_angle_measure_v1"),
        ("geometry", "measurement", "geometry_measurement_v1"),
        ("tile", "path", "tile_path_v1"),
    )
    for domain, task_group, bundle_id in bundle_coords:
        bundle = load_prompt_bundle(domain, task_group, bundle_id)
        answer_only_templates = bundle.answer_or_evidence_templates["answer_only"]
        evidence_templates = bundle.answer_or_evidence_templates["answer_and_evidence"]
        assert len(answer_only_templates) >= 10
        assert len(evidence_templates) >= 10
        assert all("{json_output_contract_answer_only}" in str(template) for template in answer_only_templates)
        assert all("{answer_hint}" in str(template) for template in answer_only_templates)
        assert all("{json_example_answer_only}" in str(template) for template in answer_only_templates)
        assert all("{json_output_contract}" in str(template) for template in evidence_templates)
        assert all("{evidence_hint}" in str(template) for template in evidence_templates)
        assert all("{answer_hint}" in str(template) for template in evidence_templates)
        assert all("{json_example}" in str(template) for template in evidence_templates)
        assert {
            "json_output_contract_answer_only",
            "answer_hint",
            "json_example_answer_only",
        }.issubset(set(bundle.required_slots_by_key.get("answer_or_evidence:answer_only", ())))
        assert {
            "json_output_contract",
            "evidence_hint",
            "answer_hint",
            "json_example",
        }.issubset(set(bundle.required_slots_by_key.get("answer_or_evidence:answer_and_evidence", ())))


def test_analytical_area_bundle_renders_deterministically() -> None:
    slots = {
        "object_description": "a single annotated geometric shape on graph paper",
        "question_text": "The shape is a rectangle. Use the annotated side lengths to compute its area in square units.",
        "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
        "json_output_contract_answer_only": 'Return a valid JSON object with key "answer".',
        "evidence_hint": 'set "evidence" to a JSON object that maps each required annotation label to its shown measurement value',
        "answer_hint": 'set "answer" to the area value as an integer',
        "json_example": '{"evidence":{"AB":6,"CD":4},"answer":24}',
        "json_example_answer_only": '{"answer":24}',
    }
    first = render_prompt(
        domain="geometry",
        task_group="analytical_2d",
        bundle_id="geometry_analytical_area_v1",
        task_type_key="analytical_single_shape",
        query_type="measure",
        slots=slots,
        instance_seed=7812,
    )
    second = render_prompt(
        domain="geometry",
        task_group="analytical_2d",
        bundle_id="geometry_analytical_area_v1",
        task_type_key="analytical_single_shape",
        query_type="measure",
        slots=slots,
        instance_seed=7812,
    )
    assert first.prompt == second.prompt
    assert first.metadata == second.metadata
