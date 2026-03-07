"""Tests for prompt bundle loading/rendering."""

from __future__ import annotations

import re

import pytest

from trace.core.prompts import load_prompt_bundle, render_prompt, render_prompt_variants


def test_render_prompt_is_deterministic() -> None:
    a = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v2",
        task_type_key="measurement_single_object",
        query_type="measure",
        slots={
            "object_description": "a single labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "evidence_hint": "the angle vertex [x, y] as integer graph-unit coordinates",
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"evidence":[[2,1],[0,0],[3,-1]],"answer":45}',
        },
        instance_seed=4242,
    )
    b = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v2",
        task_type_key="measurement_single_object",
        query_type="measure",
        slots={
            "object_description": "a single labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "evidence_hint": "the angle vertex [x, y] as integer graph-unit coordinates",
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"evidence":[[2,1],[0,0],[3,-1]],"answer":45}',
        },
        instance_seed=4242,
    )
    assert a.prompt == b.prompt
    assert a.metadata == b.metadata
    assert a.metadata["slot_values"]["object_description"] == "a single labeled angle"
    assert a.metadata["answer_or_evidence_key"] == "answer_and_evidence"
    assert "Example JSON" in a.prompt


def test_prompt_bundle_contract_and_required_slots() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v2")
    assert len(bundle.task_type_templates["measurement_single_object"]) >= 10
    assert len(bundle.query_type_templates["measure"]) >= 10
    assert len(bundle.answer_or_evidence_templates["answer_only"]) >= 10
    assert len(bundle.answer_or_evidence_templates["answer_and_evidence"]) >= 10

    with pytest.raises(ValueError):
        render_prompt(
            domain="geometry",
            task_group="measurement",
            bundle_id="geometry_measurement_v2",
            task_type_key="measurement_single_object",
            query_type="measure",
            slots={"object_description": "a single polygon"},
            instance_seed=9999,
        )


def test_render_prompt_variants_contains_answer_only_and_answer_and_evidence() -> None:
    results = render_prompt_variants(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v2",
        task_type_key="measurement_single_object",
        query_type="measure",
        answer_or_evidence_keys=("answer_only", "answer_and_evidence"),
        slots={
            "object_description": "a single polygon",
            "question_text": "What is the area of the polygon in square units?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "evidence_hint": "the polygon vertex coordinates as an unordered graph-unit point list",
            "answer_hint": 'set "answer" to the polygon area as an integer value',
            "json_example": '{"evidence":[[0,0],[4,0],[4,2],[0,2]],"answer":8}',
        },
        instance_seed=4242,
    )
    assert sorted(results.keys()) == ["answer_and_evidence", "answer_only"]
    assert "evidence" not in results["answer_only"].prompt.lower()
    assert "evidence" in results["answer_and_evidence"].prompt.lower()
    assert results["answer_only"].metadata["answer_or_evidence_key"] == "answer_only"
    assert results["answer_and_evidence"].metadata["answer_or_evidence_key"] == "answer_and_evidence"


def test_angle_prompt_bundle_answer_only_is_format_focused() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_angle_measure_v1")
    answer_only_templates = bundle.answer_or_evidence_templates["answer_only"]
    assert len(answer_only_templates) >= 10
    assert all(str(template).strip() == "" for template in answer_only_templates)

    measure_templates = bundle.query_type_templates["measure"]
    assert len(measure_templates) >= 10
    assert all("option" in str(template).lower() for template in measure_templates)
    assert any("option letter" in str(template).lower() for template in measure_templates)

    evidence_templates = bundle.answer_or_evidence_templates["answer_and_evidence"]
    assert len(evidence_templates) >= 10
    banned = re.compile(r"\b(only|just)\b", flags=re.IGNORECASE)
    assert all(banned.search(str(template)) is None for template in evidence_templates)
    assert all("{json_output_contract}" in str(template) for template in evidence_templates)
    assert all("{evidence_hint}" in str(template) for template in evidence_templates)
    assert all("{answer_hint}" in str(template) for template in evidence_templates)
    assert all("{json_example}" in str(template) for template in evidence_templates)


def test_geometry_measurement_bundle_answer_templates_avoid_only_just() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v2")
    banned = re.compile(r"\b(only|just)\b", flags=re.IGNORECASE)

    measure_templates = bundle.query_type_templates["measure"]
    answer_only_templates = bundle.answer_or_evidence_templates["answer_only"]
    evidence_templates = bundle.answer_or_evidence_templates["answer_and_evidence"]

    assert len(measure_templates) >= 10
    assert len({str(template) for template in measure_templates}) >= 10
    assert all("{question_text}" in str(template) for template in measure_templates)
    assert len(answer_only_templates) >= 10
    assert len(evidence_templates) >= 10
    assert all(str(template).strip() == "" for template in answer_only_templates)
    assert all(banned.search(str(template)) is None for template in answer_only_templates)
    assert all(banned.search(str(template)) is None for template in evidence_templates)
    assert all("{json_output_contract}" in str(template) for template in evidence_templates)
    assert all("{evidence_hint}" in str(template) for template in evidence_templates)
    assert all("{answer_hint}" in str(template) for template in evidence_templates)
    assert all("{json_example}" in str(template) for template in evidence_templates)
