"""Tests for prompt bundle loading/rendering."""

from __future__ import annotations

import json
import re

import pytest

from trace.core.prompts import load_prompt_bundle, render_prompt, render_prompt_variants
from trace.core.prompts.schema import REQUIRED_PROMPT_VARIANTS
from trace.tasks.shared.prompt_json_example import build_prompt_json_examples


def test_render_prompt_is_deterministic() -> None:
    a = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_family_key="measurement_single_object",
        task_key="measurement_query",
        slots={
            "object_description": "a labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "json_output_contract_answer_only": 'Return a valid JSON object with key "answer".',
            "evidence_hint": 'set "evidence" to an array of exactly three graph-paper points for the queried angle: the vertex and the two ray endpoints',
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"evidence":[[0,2],[0,0],[3,0]],"answer":90}',
            "json_example_answer_only": '{"answer":45}',
        },
        instance_seed=4242,
    )
    b = render_prompt(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_family_key="measurement_single_object",
        task_key="measurement_query",
        slots={
            "object_description": "a labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": 'Return a valid JSON object with keys "evidence" and "answer" in that order.',
            "json_output_contract_answer_only": 'Return a valid JSON object with key "answer".',
            "evidence_hint": 'set "evidence" to an array of exactly three graph-paper points for the queried angle: the vertex and the two ray endpoints',
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"evidence":[[0,2],[0,0],[3,0]],"answer":90}',
            "json_example_answer_only": '{"answer":45}',
        },
        instance_seed=4242,
    )
    assert a.prompt == b.prompt
    assert a.metadata == b.metadata
    assert a.metadata["slot_values"]["object_description"] == "a labeled angle"
    assert a.metadata["answer_or_evidence_key"] == "answer_and_evidence"
    assert "Example JSON" in a.prompt


def test_prompt_bundle_contract_and_required_slots() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v1")
    assert len(bundle.task_family_templates["measurement_single_object"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["measurement_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.answer_or_evidence_templates["answer_only"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.answer_or_evidence_templates["answer_and_evidence"]) == REQUIRED_PROMPT_VARIANTS

    with pytest.raises(ValueError):
        render_prompt(
            domain="geometry",
            task_group="measurement",
            bundle_id="geometry_measurement_v1",
            task_family_key="measurement_single_object",
            task_key="measurement_query",
            slots={"object_description": "a polygon"},
            instance_seed=9999,
        )


def test_render_prompt_variants_contains_answer_only_and_answer_and_evidence() -> None:
    results = render_prompt_variants(
        domain="geometry",
        task_group="measurement",
        bundle_id="geometry_measurement_v1",
        task_family_key="measurement_single_object",
        task_key="measurement_query",
        answer_or_evidence_keys=("answer_only", "answer_and_evidence"),
        slots={
            "object_description": "a polygon",
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

        task_templates = bundle.task_templates[
            "measurement_angle_value" if bundle_id == "geometry_angle_measure_v1" else "measurement_query"
        ]
        answer_only_templates = bundle.answer_or_evidence_templates["answer_only"]
        evidence_templates = bundle.answer_or_evidence_templates["answer_and_evidence"]

        assert len(task_templates) == REQUIRED_PROMPT_VARIANTS
        assert len(answer_only_templates) == REQUIRED_PROMPT_VARIANTS
        assert len(evidence_templates) == REQUIRED_PROMPT_VARIANTS
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
            assert len({str(template) for template in task_templates}) == REQUIRED_PROMPT_VARIANTS
            assert all("{question_text}" in str(template) for template in task_templates)
            assert all("option" not in str(template).lower() for template in task_templates)
            assert all("nearest integer" in str(template).lower() for template in task_templates)
        else:
            assert len({str(template) for template in task_templates}) == REQUIRED_PROMPT_VARIANTS
            assert all("{question_text}" in str(template) for template in task_templates)
            assert all("figure" not in str(template).lower() for template in task_templates)
            assert all("image" not in str(template).lower() for template in task_templates)
            assert all("diagram" not in str(template).lower() for template in task_templates)


def test_active_task_bundles_use_json_output_contracts_for_both_modes() -> None:
    bundle_coords = (
        ("charts", "composition", "charts_composition_v1"),
        ("charts", "counting", "charts_counting_v1"),
        ("charts", "statistics", "charts_statistics_v1"),
        ("geometry", "comparison", "geometry_comparison_v1"),
        ("geometry", "counting", "geometry_counting_v1"),
        ("geometry", "analytical_3d", "geometry_analytical_surface_area_v1"),
        ("geometry", "analytical_3d", "geometry_analytical_volume_v1"),
        ("geometry", "analytical_2d", "geometry_analytical_area_v1"),
        ("geometry", "analytical_2d", "geometry_analytical_composite_area_v1"),
        ("geometry", "analytical_2d", "geometry_analytical_length_v1"),
        ("geometry", "analytical_2d", "geometry_analytical_perimeter_v1"),
        ("geometry", "measurement", "geometry_angle_measure_v1"),
        ("geometry", "measurement", "geometry_measurement_v1"),
        ("icons", "counting", "icons_counting_v1"),
        ("icons", "relation", "icons_relation_v1"),
        ("icons", "sequence", "icons_sequence_v1"),
        ("icons", "transformation", "icons_transformation_v1"),
        ("tables", "readout", "tables_readout_v1"),
        ("tables", "statistics", "tables_statistics_v1"),
        ("tile", "count", "tile_count_v1"),
        ("tile", "pattern", "tile_pattern_v1"),
        ("tile", "relation", "tile_relation_v1"),
        ("tile", "reachability", "tile_reachability_v1"),
        ("tile", "path", "tile_path_v1"),
        ("tile", "symmetry", "tile_symmetry_v1"),
        ("tile", "transition", "tile_transition_v1"),
    )
    for domain, task_group, bundle_id in bundle_coords:
        bundle = load_prompt_bundle(domain, task_group, bundle_id)
        answer_only_templates = bundle.answer_or_evidence_templates["answer_only"]
        evidence_templates = bundle.answer_or_evidence_templates["answer_and_evidence"]
        assert len(answer_only_templates) == REQUIRED_PROMPT_VARIANTS
        assert len(evidence_templates) == REQUIRED_PROMPT_VARIANTS
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


def test_tile_count_bundle_supports_both_count_and_component_queries() -> None:
    bundle = load_prompt_bundle("tile", "count", "tile_count_v1")
    assert len(bundle.task_templates["color_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["color_component_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:color_count_query"]) == ["query_color"]
    assert list(bundle.required_slots_by_key["task:color_component_count_query"]) == ["query_color"]


def test_icons_relation_bundle_supports_anchor_relation_query() -> None:
    bundle = load_prompt_bundle("icons", "relation", "icons_relation_v1")
    assert len(bundle.task_templates["relation_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:relation_query"]) == ["question_text"]
    assert "scene_two_anchor_relation" in bundle.task_family_templates
    assert "reference_grid_mirror_symmetry_relation" in bundle.task_family_templates


def test_icons_sequence_bundle_supports_missing_count_query() -> None:
    bundle = load_prompt_bundle("icons", "sequence", "icons_sequence_v1")
    assert len(bundle.task_templates["missing_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:missing_count_query"]) == ["question_text"]


def test_tile_reachability_bundle_supports_region_size_query() -> None:
    bundle = load_prompt_bundle("tile", "reachability", "tile_reachability_v1")
    assert len(bundle.task_templates["region_size_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:region_size_query"]) == ["obstacle_color", "start_color"]


def test_tile_path_bundle_supports_shortest_path_and_reachable_target_queries() -> None:
    bundle = load_prompt_bundle("tile", "path", "tile_path_v1")
    assert len(bundle.task_templates["shortest_path_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["reachable_target_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:shortest_path_query"]) == [
        "obstacle_color",
        "start_color",
        "goal_color",
    ]
    assert list(bundle.required_slots_by_key["task:reachable_target_count_query"]) == [
        "obstacle_color",
        "start_color",
        "target_color",
    ]


def test_tile_pattern_bundle_supports_match3_query() -> None:
    bundle = load_prompt_bundle("tile", "pattern", "tile_pattern_v1")
    assert len(bundle.task_templates["match3_run_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:match3_run_count_query"]) == [
        "line_axis",
        "run_length",
        "query_color",
    ]


def test_tile_relation_bundle_supports_min_distance_query() -> None:
    bundle = load_prompt_bundle("tile", "relation", "tile_relation_v1")
    assert len(bundle.task_templates["min_distance_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:min_distance_query"]) == [
        "background_color",
        "color_a",
        "color_b",
    ]


def test_charts_statistics_bundle_supports_summary_variants() -> None:
    bundle = load_prompt_bundle("charts", "statistics", "charts_statistics_v1")
    assert len(bundle.task_templates["summary_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["summary_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["max"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["sum"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["mode"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["argmax"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["argmin"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["median_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task_family:labeled_chart_statistics"]) == ["object_description"]


def test_charts_counting_bundle_supports_value_count_variants() -> None:
    bundle = load_prompt_bundle("charts", "counting", "charts_counting_v1")
    assert len(bundle.task_templates["value_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["above_threshold"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["below_threshold"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["in_interval"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task_family:labeled_chart_counting"]) == ["object_description"]


def test_charts_readout_bundle_supports_subset_value_variants() -> None:
    bundle = load_prompt_bundle("charts", "readout", "charts_readout_v1")
    assert len(bundle.task_templates["subset_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["sum_two"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["difference_two_abs"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["max_two"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["min_two"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["mean_two"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task_family:labeled_chart_readout"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["task:subset_value_query"]) == ["query_label_a", "query_label_b"]


def test_charts_composition_bundle_supports_subset_value_variants() -> None:
    bundle = load_prompt_bundle("charts", "composition", "charts_composition_v1")
    assert len(bundle.task_templates["subset_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["stack_total_at_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["stack_segment_value"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["combined_share_subset"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task_family:composition_chart_value"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["task:subset_value_query"]) == [
        "query_category_label",
        "query_series_label",
        "query_label_a",
        "query_label_b",
    ]


def test_tables_readout_bundle_supports_subset_value_variants() -> None:
    bundle = load_prompt_bundle("tables", "readout", "tables_readout_v1")
    assert len(bundle.task_templates["subset_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["cell_lookup"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["cell_sum_two"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_variant_templates["cell_difference_two_abs"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task_family:styled_table_readout"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["task_variant:cell_lookup"]) == [
        "query_row_label_1",
        "query_column_1",
    ]
    assert list(bundle.required_slots_by_key["task_variant:cell_sum_two"]) == [
        "query_row_label_1",
        "query_column_1",
        "query_row_label_2",
        "query_column_2",
    ]


def test_geometry_task_templates_avoid_awkward_comma_question_prefixes() -> None:
    bundle_coords = (
        ("geometry", "measurement", "geometry_measurement_v1", "measurement_query"),
        ("geometry", "analytical_2d", "geometry_analytical_area_v1", "analytical_area_query"),
        ("geometry", "analytical_2d", "geometry_analytical_length_v1", "analytical_length_query"),
        ("geometry", "analytical_3d", "geometry_analytical_surface_area_v1", "analytical_surface_area_query"),
        ("geometry", "analytical_3d", "geometry_analytical_volume_v1", "analytical_volume_query"),
    )
    for domain, task_group, bundle_id, task_key in bundle_coords:
        bundle = load_prompt_bundle(domain, task_group, bundle_id)
        templates = bundle.task_templates[task_key]
        assert all(", {question_text}" not in str(template) for template in templates)


def test_geometry_measurement_task_templates_do_not_repeat_graph_paper_reference() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v1")
    templates = bundle.task_templates["measurement_query"]
    assert all("graph-paper image" not in str(template).lower() for template in templates)
    assert all("graph-paper diagram" not in str(template).lower() for template in templates)


def test_geometry_analytical_task_templates_do_not_repeat_image_reference() -> None:
    bundle_coords = (
        ("geometry", "analytical_2d", "geometry_analytical_area_v1", "analytical_area_query"),
        ("geometry", "analytical_2d", "geometry_analytical_length_v1", "analytical_length_query"),
        ("geometry", "analytical_3d", "geometry_analytical_volume_v1", "analytical_volume_query"),
        ("geometry", "analytical_3d", "geometry_analytical_surface_area_v1", "analytical_surface_area_query"),
    )
    for domain, task_group, bundle_id, task_key in bundle_coords:
        bundle = load_prompt_bundle(domain, task_group, bundle_id)
        templates = bundle.task_templates[task_key]
        lowered = [str(template).lower() for template in templates]
        assert all("from the image" not in template for template in lowered)
        assert all("from the figure" not in template for template in lowered)
        assert all("from the diagram" not in template for template in lowered)


def test_prompt_json_examples_use_non_degenerate_point_layouts() -> None:
    example_json, _ = build_prompt_json_examples(
        evidence_value={"A": [9, 9], "B": [8, 8], "C": [7, 7], "D": [6, 6]},
        answer_type="integer",
    )
    payload = json.loads(example_json)
    assert payload["evidence"] == {
        "A": [0, 0],
        "B": [4, 0],
        "C": [4, 2],
        "D": [0, 2],
    }


def test_analytical_area_bundle_renders_deterministically() -> None:
    slots = {
        "object_description": "an annotated geometric shape",
        "question_text": "The rectangle has two annotated side lengths. What is its area in square units?",
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
        task_family_key="analytical_single_shape",
        task_key="analytical_area_query",
        slots=slots,
        instance_seed=7812,
    )
    second = render_prompt(
        domain="geometry",
        task_group="analytical_2d",
        bundle_id="geometry_analytical_area_v1",
        task_family_key="analytical_single_shape",
        task_key="analytical_area_query",
        slots=slots,
        instance_seed=7812,
    )
    assert first.prompt == second.prompt
    assert first.metadata == second.metadata
