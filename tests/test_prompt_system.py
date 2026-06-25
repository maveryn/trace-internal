"""Tests for prompt bundle loading/rendering."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from trace.core.seed import hash64
from trace.core.prompts import load_prompt_bundle, load_scene_prompt_bundle, render_prompt, render_prompt_variants
from trace.core.prompts.schema import REQUIRED_PROMPT_VARIANTS
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.shared.prompt_json_example import build_prompt_json_examples, dump_prompt_json_examples

ANSWER_AND_ANNOTATION_CONTRACT = (
    'Use a valid JSON object with keys "annotation" and "answer" in that order for the final answer.'
)
ANSWER_ONLY_CONTRACT = 'Use a valid JSON object with key "answer" for the final answer.'
ANSWER_FORMAT_TEXT = re.compile(
    r"(Answer format:|Answer field:|Required answer format:|Final answer format:|Use this answer format:|Format for the \"answer\" field:)"
)
ANNOTATION_FORMAT_TEXT = re.compile(
    r"(Annotation format:|Annotation field:|Required annotation format:|Use this annotation format:|Format for the \"annotation\" field:)"
)
BAD_PROMPT_OPENER = re.compile(
    r"^\s*(Displayed is|Displayed are|Shown is|Shown are|Use this|Read this|Look at|The image contains|The chart is)\b",
    flags=re.IGNORECASE,
)


def _active_prompt_bundle_coords() -> list[tuple[str, str, str]]:
    """Return active prompt bundle coordinates from domain configs."""
    prompt_coords: dict[str, tuple[str, str]] = {}
    for path in sorted(Path("prompts").rglob("*.json")):
        if "dummy" in path.parts:
            continue
        bundle = json.loads(path.read_text())
        bundle_id = str(bundle.get("bundle_id", ""))
        if not bundle_id:
            continue
        prompt_coords[bundle_id] = (str(path.parts[1]), str(path.parts[2]))

    active_bundle_ids: set[str] = set()

    def _walk(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "bundle_id" and isinstance(child, str):
                    active_bundle_ids.add(str(child))
                _walk(child)
        elif isinstance(value, list):
            for child in value:
                _walk(child)

    for path in sorted(Path("configs/domains").rglob("*.yaml")):
        _walk(yaml.safe_load(path.read_text()) or {})

    missing = sorted(bundle_id for bundle_id in active_bundle_ids if bundle_id not in prompt_coords)
    assert missing == []
    return [
        (prompt_coords[bundle_id][0], prompt_coords[bundle_id][1], bundle_id)
        for bundle_id in sorted(active_bundle_ids)
    ]


def _semantic_prompt_part(prompt: str) -> str:
    """Return prompt text before output-mode formatting instructions."""
    markers = (
        "Annotation format:",
        "Annotation field:",
        "Required annotation format:",
        "Use this annotation format:",
        'Format for the "annotation" field:',
        "Answer format:",
        "Answer field:",
        "Required answer format:",
        "Final answer format:",
        "Use this answer format:",
        'Format for the "answer" field:',
    )
    marker_positions = [prompt.find(marker) for marker in markers if prompt.find(marker) >= 0]
    if not marker_positions:
        return str(prompt).strip()
    return str(prompt)[: min(marker_positions)].strip()


def test_render_prompt_is_deterministic() -> None:
    a = render_prompt(
        domain="geometry",
        scene_id="measurement",
        bundle_id="geometry_measurement_v0",
        scene_key="measurement_single_object",
        task_key="measurement_query",
        slots={
            "object_description": "a labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": ANSWER_AND_ANNOTATION_CONTRACT,
            "json_output_contract_answer_only": ANSWER_ONLY_CONTRACT,
            "annotation_hint": 'set "annotation" to an array of exactly three graph-paper points for the queried angle: the vertex and the two ray endpoints',
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"annotation":[[0,2],[0,0],[3,0]],"answer":90}',
            "json_example_answer_only": '{"answer":45}',
        },
        instance_seed=4242,
    )
    b = render_prompt(
        domain="geometry",
        scene_id="measurement",
        bundle_id="geometry_measurement_v0",
        scene_key="measurement_single_object",
        task_key="measurement_query",
        slots={
            "object_description": "a labeled angle",
            "question_text": "What is the measure of angle ABC in degrees?",
            "json_output_contract": ANSWER_AND_ANNOTATION_CONTRACT,
            "json_output_contract_answer_only": ANSWER_ONLY_CONTRACT,
            "annotation_hint": 'set "annotation" to an array of exactly three graph-paper points for the queried angle: the vertex and the two ray endpoints',
            "answer_hint": 'set "answer" to the angle measure as an integer value',
            "json_example": '{"annotation":[[0,2],[0,0],[3,0]],"answer":90}',
            "json_example_answer_only": '{"answer":45}',
        },
        instance_seed=4242,
    )
    assert a.prompt == b.prompt
    assert a.metadata == b.metadata
    assert a.metadata["slot_values"]["object_description"] == "a labeled angle"
    assert a.metadata["answer_or_annotation_key"] == "answer_and_annotation"
    assert "Example JSON" in a.prompt
    assert ANSWER_AND_ANNOTATION_CONTRACT not in a.prompt
    assert ANNOTATION_FORMAT_TEXT.search(a.prompt) is not None
    assert ANSWER_FORMAT_TEXT.search(a.prompt) is not None


def test_prompt_bundle_contract_and_required_slots() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v0")
    assert len(bundle.scene_templates["measurement_single_object"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["measurement_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.answer_or_annotation_templates["answer_only"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.answer_or_annotation_templates["answer_and_annotation"]) == REQUIRED_PROMPT_VARIANTS

    with pytest.raises(ValueError):
        render_prompt(
            domain="geometry",
            scene_id="measurement",
            bundle_id="geometry_measurement_v0",
            scene_key="measurement_single_object",
            task_key="measurement_query",
            slots={"object_description": "a polygon"},
            instance_seed=9999,
        )


def test_render_prompt_variants_contains_answer_only_and_answer_and_annotation() -> None:
    results = render_prompt_variants(
        domain="geometry",
        scene_id="measurement",
        bundle_id="geometry_measurement_v0",
        scene_key="measurement_single_object",
        task_key="measurement_query",
        answer_or_annotation_keys=("answer_only", "answer_and_annotation"),
        slots={
            "object_description": "a polygon",
            "question_text": "What is the area of the polygon in square units?",
            "json_output_contract": ANSWER_AND_ANNOTATION_CONTRACT,
            "json_output_contract_answer_only": ANSWER_ONLY_CONTRACT,
            "annotation_hint": 'set "annotation" to a JSON object mapping required labels to graph-unit coordinates [x, y]',
            "answer_hint": 'set "answer" to the polygon area as an integer value',
            "json_example": '{"annotation":{"A":[0,0],"B":[4,0],"C":[4,2],"D":[0,2]},"answer":8}',
            "json_example_answer_only": '{"answer":8}',
        },
        instance_seed=4242,
    )
    assert sorted(results.keys()) == ["answer_and_annotation", "answer_only"]
    assert "annotation" not in results["answer_only"].prompt.lower()
    assert "annotation" in results["answer_and_annotation"].prompt.lower()
    assert '"answer"' in results["answer_only"].prompt
    assert ANSWER_ONLY_CONTRACT not in results["answer_only"].prompt
    assert ANSWER_AND_ANNOTATION_CONTRACT not in results["answer_and_annotation"].prompt
    assert ANSWER_FORMAT_TEXT.search(results["answer_only"].prompt) is not None
    assert ANNOTATION_FORMAT_TEXT.search(results["answer_and_annotation"].prompt) is not None
    assert results["answer_only"].metadata["answer_or_annotation_key"] == "answer_only"
    assert results["answer_and_annotation"].metadata["answer_or_annotation_key"] == "answer_and_annotation"


def test_geometry_measurement_bundles_answer_templates_use_contract_and_avoid_only_just() -> None:
    banned = re.compile(r"\b(only|just)\b", flags=re.IGNORECASE)
    for bundle_id in ("geometry_angle_measure_v0", "geometry_measurement_v0"):
        bundle = load_prompt_bundle("geometry", "measurement", bundle_id)

        task_templates = bundle.task_templates[
            "measurement_angle_value" if bundle_id == "geometry_angle_measure_v0" else "measurement_query"
        ]
        answer_only_templates = bundle.answer_or_annotation_templates["answer_only"]
        annotation_templates = bundle.answer_or_annotation_templates["answer_and_annotation"]

        assert len(task_templates) == REQUIRED_PROMPT_VARIANTS
        assert len(answer_only_templates) == REQUIRED_PROMPT_VARIANTS
        assert len(annotation_templates) == REQUIRED_PROMPT_VARIANTS
        assert all(str(template).strip() for template in answer_only_templates)
        assert all("{json_output_contract_answer_only}" in str(template) for template in answer_only_templates)
        assert all(ANSWER_FORMAT_TEXT.search(str(template)) is not None for template in answer_only_templates)
        assert all("{answer_hint}" in str(template) for template in answer_only_templates)
        assert all("{json_example_answer_only}" in str(template) for template in answer_only_templates)
        assert all(banned.search(str(template)) is None for template in answer_only_templates)
        assert all(banned.search(str(template)) is None for template in annotation_templates)
        assert all("{json_output_contract}" in str(template) for template in annotation_templates)
        assert all(ANSWER_FORMAT_TEXT.search(str(template)) is not None for template in annotation_templates)
        assert all(ANNOTATION_FORMAT_TEXT.search(str(template)) is not None for template in annotation_templates)
        assert all("{annotation_hint}" in str(template) for template in annotation_templates)
        assert all("{answer_hint}" in str(template) for template in annotation_templates)
        assert all("{json_example}" in str(template) for template in annotation_templates)

        if bundle_id == "geometry_angle_measure_v0":
            assert len({str(template) for template in task_templates}) == REQUIRED_PROMPT_VARIANTS
            assert all("{angle_label}" in str(template) for template in task_templates)
            assert all("{question_text}" not in str(template) for template in task_templates)
            assert list(bundle.required_slots_by_key["task:measurement_angle_value"]) == ["angle_label"]
            assert all("option" not in str(template).lower() for template in task_templates)
            assert all("nearest integer" in str(template).lower() for template in task_templates)
        else:
            assert len({str(template) for template in task_templates}) == REQUIRED_PROMPT_VARIANTS
            assert all("{question_text}" in str(template) for template in task_templates)
            assert all("figure" not in str(template).lower() for template in task_templates)
            assert all("image" not in str(template).lower() for template in task_templates)
            assert all("diagram" not in str(template).lower() for template in task_templates)


def _assert_geometry_analytical_measurement_query_text(
    *,
    domain: str,
    scene_id: str,
    bundle_id: str,
    expected_query_text: dict[str, str],
    task_key: str = "analytical_measurement_value_query",
) -> None:
    bundle = load_prompt_bundle(domain, scene_id, bundle_id)
    assert len(bundle.task_templates[task_key]) == REQUIRED_PROMPT_VARIANTS
    assert all(str(template) == "" for template in bundle.task_templates[task_key])

    assert set(bundle.query_templates) >= set(expected_query_text)
    for query_key, query_text in expected_query_text.items():
        assert list(bundle.required_slots_by_key.get(f"query:{query_key}", ())) == []
        templates = bundle.query_templates[query_key]
        assert len(templates) == REQUIRED_PROMPT_VARIANTS
        assert templates == tuple([query_text] * REQUIRED_PROMPT_VARIANTS)
        assert all("{question_text}" not in str(template) for template in templates)


def test_geometry_analytical_measurement_bundle_owns_query_text() -> None:
    expected_query_text = {
        "similar_triangles_side_length": 'Segment "DE" is parallel to segment "BC". What is the length of segment "EC"?',
        "parallel_section_cross_length": 'What is the length of segment "DE"?',
        "parallel_section_base_length": 'What is the length of segment "BC"?',
        "chained_rectangle_diagonal_length": 'In the split rectangle, use diagonal "DE" first to infer the height. What is the length of diagonal "DB"?',
        "rectangle_triangle_shared_height_length": 'The rectangle and right triangle share segment "BD". Use diagonal "AD" first, then find the length of segment "CD".',
        "angle_bisector_split_length": 'Segment "AD" bisects angle "BAC". What is the length of segment "DC"?',
        "angle_bisector_base_length": 'Segment "AD" bisects angle "BAC". What is the full length of segment "BC"?',
        "centroid_vertex_segment_length": 'Point "G" is the centroid, and "D" is the midpoint of segment "BC". What is the length of segment "AG"?',
        "centroid_whole_median_length": 'Point "G" is the centroid, and "D" is the midpoint of segment "BC". What is the full length of median "AD"?',
        "rectangle_minus_triangle_area": "What is the area of the shaded region?",
        "l_shape_area": "What is the area of the shaded region?",
        "house_outline_perimeter": 'What is the perimeter of the outer boundary of pentagon "ABCDE"?',
        "tabbed_rectilinear_perimeter": "What is the perimeter of the outer boundary of the shaded figure?",
    }
    _assert_geometry_analytical_measurement_query_text(
        domain="geometry",
        scene_id="measurement",
        bundle_id="geometry_analytical_measurement_v0",
        expected_query_text=expected_query_text,
    )


def test_geometry_angle_relations_bundle_owns_query_text() -> None:
    expected_query_text = {
        "triangle_exterior_angle": 'What is the measure of angle "ABC"?',
        "parallel_supplement_angle": 'What is the measure of angle "CFE"?',
        "target_angle_value": 'Use the displayed angle expressions to solve for x. What is the measure of angle "ABC"?',
        "variable_x_value": "Use the displayed angle expressions. What is the value of x?",
    }
    _assert_geometry_analytical_measurement_query_text(
        domain="geometry",
        scene_id="angle_relations",
        bundle_id="geometry_angle_relations_v1",
        expected_query_text=expected_query_text,
        task_key="angle_relation_value_query",
    )


def test_active_task_bundles_use_json_output_contracts_for_both_modes() -> None:
    for domain, scene_id, bundle_id in _active_prompt_bundle_coords():
        bundle = load_prompt_bundle(domain, scene_id, bundle_id)
        answer_only_templates = bundle.answer_or_annotation_templates["answer_only"]
        annotation_templates = bundle.answer_or_annotation_templates["answer_and_annotation"]
        assert len(answer_only_templates) == REQUIRED_PROMPT_VARIANTS
        assert len(annotation_templates) == REQUIRED_PROMPT_VARIANTS
        assert all("{json_output_contract_answer_only}" in str(template) for template in answer_only_templates)
        assert all("{answer_hint}" in str(template) for template in answer_only_templates)
        assert all("{json_example_answer_only}" in str(template) for template in answer_only_templates)
        assert all("{json_output_contract}" in str(template) for template in annotation_templates)
        assert all("{annotation_hint}" in str(template) for template in annotation_templates)
        assert all("{answer_hint}" in str(template) for template in annotation_templates)
        assert all("{json_example}" in str(template) for template in annotation_templates)
        assert {
            "json_output_contract_answer_only",
            "answer_hint",
            "json_example_answer_only",
        }.issubset(set(bundle.required_slots_by_key.get("answer_or_annotation:answer_only", ())))
        assert {
            "json_output_contract",
            "annotation_hint",
            "answer_hint",
            "json_example",
        }.issubset(set(bundle.required_slots_by_key.get("answer_or_annotation:answer_and_annotation", ())))


def test_prompt_bundles_use_format_language_in_output_and_variant_templates() -> None:
    banned_variant_patterns = (
        re.compile(r"\bAnswer with\b", flags=re.IGNORECASE),
        re.compile(r"\bRespond with\b", flags=re.IGNORECASE),
        re.compile(r"\bReturn only\b", flags=re.IGNORECASE),
        re.compile(r"\bReturn the\b", flags=re.IGNORECASE),
        re.compile(r"\bGive the final\b", flags=re.IGNORECASE),
        re.compile(r"\bAnswer using the exact\b", flags=re.IGNORECASE),
        re.compile(r"\bAnswer using the integer sum\b", flags=re.IGNORECASE),
        re.compile(r"\bGive the count\b", flags=re.IGNORECASE),
    )

    for path in sorted(Path("prompts").rglob("*.json")):
        bundle = json.loads(path.read_text())

        for template in bundle.get("answer_or_annotation_templates", {}).get("answer_only", ()):
            assert "Return a valid JSON object" not in str(template), path
            assert ANSWER_FORMAT_TEXT.search(str(template)) is not None, path
        for template in bundle.get("answer_or_annotation_templates", {}).get("answer_and_annotation", ()):
            assert "Return a valid JSON object" not in str(template), path
            assert ANSWER_FORMAT_TEXT.search(str(template)) is not None, path
            assert ANNOTATION_FORMAT_TEXT.search(str(template)) is not None, path

        for templates in bundle.get("query_templates", {}).values():
            for template in templates:
                lowered = str(template)
                assert all(pattern.search(lowered) is None for pattern in banned_variant_patterns), path

    for path in sorted(Path("configs").rglob("*.yaml")):
        text = path.read_text()
        assert 'Return a valid JSON object with key "answer".' not in text, path
        assert 'Return a valid JSON object with keys "annotation" and "answer" in that order.' not in text, path
        assert ANSWER_ONLY_CONTRACT in text or ANSWER_AND_ANNOTATION_CONTRACT in text or "json_output_contract" not in text, path


def test_prompt_bundles_avoid_awkward_visual_openers() -> None:
    for path in sorted(Path("prompts").rglob("*.json")):
        if "dummy" in path.parts:
            continue
        bundle = json.loads(path.read_text())
        for layer_name in ("scene_templates", "task_templates", "query_templates"):
            for templates in bundle.get(layer_name, {}).values():
                for template in templates:
                    if not str(template).strip():
                        continue
                    assert BAD_PROMPT_OPENER.search(str(template)) is None, (path, template)


def _example_answer_matches_type(answer_type: str, value: object) -> bool:
    """Return true when one prompt JSON example matches the declared answer type."""
    if answer_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if answer_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if answer_type == "string":
        return isinstance(value, str)
    if answer_type == "option_letter":
        return isinstance(value, str) and len(value) == 1 and value.isalpha() and value.upper() == value
    if answer_type == "pi_expression":
        return isinstance(value, str)
    return True


def test_active_tasks_answer_only_prompts_stay_answer_only() -> None:
    banned_annotation_word = re.compile(r"\bannotation\b", flags=re.IGNORECASE)
    banned_bbox_word = re.compile(r"\bbbox\b|bounding box", flags=re.IGNORECASE)

    for task_id in sorted(TASK_REGISTRY):
        task = create_task(task_id)
        out = None
        last_error: Exception | None = None
        for sample_idx in range(8):
            try:
                out = task.generate(
                    hash64(20260411, f"{task_id}:answer_only_prompt_audit", sample_idx),
                    params={},
                    max_attempts=128,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised only on unlucky audit seeds
                last_error = exc
                continue
        if out is None:
            raise AssertionError(f"{task_id} failed answer-only audit generation across 8 deterministic seeds") from last_error
        prompt = str(out.prompt_variants.get("answer_only", ""))
        annotation_prompt = str(out.prompt_variants.get("answer_and_annotation", ""))
        assert prompt, task_id
        assert annotation_prompt, task_id
        assert BAD_PROMPT_OPENER.search(_semantic_prompt_part(prompt)) is None, task_id
        assert _semantic_prompt_part(prompt) == _semantic_prompt_part(annotation_prompt), task_id
        assert "Example JSON:" in prompt, task_id
        assert '"annotation"' not in prompt, task_id
        assert banned_annotation_word.search(prompt) is None, task_id
        assert banned_bbox_word.search(prompt) is None, task_id

        query_spec = out.trace_payload.get("query_spec", {})
        prompt_variants = query_spec.get("prompt_variants", {})
        answer_only_variant = prompt_variants.get("answer_only", {})
        metadata = answer_only_variant.get("metadata", {})
        slot_values = metadata.get("slot_values", {})

        answer_hint = str(slot_values.get("answer_hint", ""))
        assert answer_hint, task_id
        assert banned_annotation_word.search(answer_hint) is None, task_id
        assert banned_bbox_word.search(answer_hint) is None, task_id

        example = json.loads(str(slot_values.get("json_example_answer_only", "")))
        assert list(example.keys()) == ["answer"], task_id
        assert _example_answer_matches_type(str(out.answer_gt.type), example["answer"]), task_id


def test_cell_board_count_bundle_supports_both_count_and_component_queries() -> None:
    bundle = load_prompt_bundle("puzzles", "cell_board_count", "puzzles_cell_board_count_v0")
    assert len(bundle.task_templates["color_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["color_component_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:color_count_query"]) == ["query_color"]
    assert list(bundle.required_slots_by_key["task:color_component_count_query"]) == ["query_color"]


def test_pages_arithmetic_bundle_supports_section_expression_query() -> None:
    bundle = load_prompt_bundle("pages", "arithmetic", "pages_arithmetic_v0")
    assert len(bundle.scene_templates["structured_document_sections"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["section_expression_query"]) == REQUIRED_PROMPT_VARIANTS
    assert bundle.allow_empty_task_templates is True
    assert list(bundle.required_slots_by_key["query:sum_two_amounts_in_section"]) == [
        "section_label",
        "first_label",
        "second_label",
    ]
    assert list(bundle.required_slots_by_key["query:sum_minus_amount_in_section"]) == [
        "section_label",
        "first_label",
        "second_label",
        "third_label",
    ]


def test_pages_hierarchy_bundle_supports_tree_count_query() -> None:
    bundle = load_prompt_bundle("pages", "hierarchy", "pages_hierarchy_v0")
    assert len(bundle.scene_templates["hierarchy_diagram"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["tree_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert bundle.allow_empty_task_templates is True
    assert list(bundle.required_slots_by_key["query:subtree_descendant_count"]) == ["query_label"]
    assert list(bundle.required_slots_by_key["query:path_length_between_two_nodes"]) == [
        "query_label",
        "right_query_label",
    ]


def test_icons_relation_bundle_supports_anchor_relation_query() -> None:
    bundle = load_prompt_bundle("icons", "relation", "icons_relation_v0")
    assert len(bundle.task_templates["relation_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:relation_query"]) == ["question_text"]
    assert "named_reference_distance_relation" in bundle.scene_templates
    assert "reference_grid_mirror_symmetry_relation" in bundle.scene_templates


def test_icons_overlap_grid_bundle_supports_occlusion_order_count() -> None:
    bundle = load_prompt_bundle("icons", "overlap_grid", "icons_overlap_grid_v1")
    assert bundle.schema_version == "v1"
    assert len(bundle.task_templates["occlusion_order_count"]) == REQUIRED_PROMPT_VARIANTS
    assert "overlap_grid_occlusion_order" in bundle.scene_templates
    assert list(bundle.required_slots_by_key["scene:overlap_grid_occlusion_order"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["task:occlusion_order_count"]) == ["question_text"]


def test_icons_named_strip_bundle_supports_run_length_queries() -> None:
    bundle = load_prompt_bundle("icons", "named_strip", "icons_named_strip_v1")
    assert bundle.schema_version == "v1"
    assert bundle.allow_empty_task_templates is True
    assert len(bundle.task_templates["shape_run_length"]) == REQUIRED_PROMPT_VARIANTS
    assert set(bundle.query_templates.keys()) == {"longest_shape_run_length", "shortest_shape_run_length"}
    assert list(bundle.required_slots_by_key["query:longest_shape_run_length"]) == ["target_shape_name"]
    assert list(bundle.required_slots_by_key["query:shortest_shape_run_length"]) == ["target_shape_name"]
    assert "named_strip_run_length" in bundle.scene_templates


def test_icons_pattern_bundle_supports_structured_violation_query() -> None:
    bundle = load_prompt_bundle("icons", "pattern_grid", "icons_pattern_v0")
    assert len(bundle.task_templates["structured_violation_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:structured_violation_query"]) == ["question_text"]
    assert "structured_violation_scene" in bundle.scene_templates


def test_icons_wallpaper_panels_bundle_supports_reference_tasks() -> None:
    bundle = load_prompt_bundle("icons", "wallpaper_panels", "icons_wallpaper_panels_v1")
    assert set(bundle.scene_templates.keys()) == {
        "wallpaper_panel_violation_scene",
        "wallpaper_reference_match_scene",
    }
    assert set(bundle.task_templates.keys()) == {
        "motif_violation_label",
        "same_pattern_as_reference_label",
    }
    assert not bundle.query_templates
    assert "answer_hint" in bundle.static_slots_by_key["task:motif_violation_label"]


def test_icons_venn_field_bundle_supports_region_count_queries() -> None:
    bundle = load_prompt_bundle("icons", "venn_field", "icons_venn_field_v1")
    assert "venn_field_scene" in bundle.scene_templates
    assert len(bundle.task_templates["scoped_attribute_count"]) == REQUIRED_PROMPT_VARIANTS
    assert set(bundle.query_templates.keys()) == {
        "inside_both_circles_count",
        "inside_either_circle_count",
        "inside_exactly_one_circle_count",
        "outside_both_circles_count",
    }
    assert list(bundle.required_slots_by_key["query:inside_both_circles_count"]) == ["target_description"]


def test_graph_counting_bundle_supports_degree_count_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_counting_v0")
    assert "single_graph_counting" in bundle.scene_templates
    assert len(bundle.task_templates["degree_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["named_node_degree_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["node_color_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["edge_color_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["isolated_node_count_after_node_removal_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["degree_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["in_degree_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["out_degree_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["named_node_degree_value"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["named_node_in_degree_value"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["named_node_out_degree_value"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["named_node_total_degree_value"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["node_color_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["edge_color_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["isolated_node_count_after_node_removal"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:degree_count"]) == ["query_degree"]
    assert list(bundle.required_slots_by_key["query:in_degree_count"]) == ["query_degree"]
    assert list(bundle.required_slots_by_key["query:out_degree_count"]) == ["query_degree"]
    assert list(bundle.required_slots_by_key["query:named_node_degree_value"]) == ["query_label"]
    assert list(bundle.required_slots_by_key["query:named_node_in_degree_value"]) == ["query_label"]
    assert list(bundle.required_slots_by_key["query:named_node_out_degree_value"]) == ["query_label"]
    assert list(bundle.required_slots_by_key["query:named_node_total_degree_value"]) == ["query_label"]
    assert list(bundle.required_slots_by_key["query:node_color_count"]) == ["target_color_label"]
    assert list(bundle.required_slots_by_key["query:edge_color_count"]) == ["target_color_label"]
    assert list(bundle.required_slots_by_key["query:isolated_node_count_after_node_removal"]) == ["query_label"]


def test_graph_counting_bundle_supports_articulation_point_count_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_counting_v0")
    assert "single_graph_counting" in bundle.scene_templates
    assert len(bundle.task_templates["articulation_point_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["articulation_point_count"]) == REQUIRED_PROMPT_VARIANTS


def test_graph_counting_bundle_supports_bridge_count_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_counting_v0")
    assert "single_graph_counting" in bundle.scene_templates
    assert len(bundle.task_templates["bridge_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["bridge_count"]) == REQUIRED_PROMPT_VARIANTS


def test_graph_counting_bundle_supports_metro_transfer_station_count_query() -> None:
    bundle = load_scene_prompt_bundle("graph", "metro", "graph_metro_v1")
    assert "metro_route_map" in bundle.scene_templates
    assert len(bundle.task_templates["metro_route_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["metro_transfer_station_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["metro_single_route_station_count"]) == REQUIRED_PROMPT_VARIANTS


def test_graph_relation_bundle_supports_metro_exact_distance_count_query() -> None:
    bundle = load_scene_prompt_bundle("graph", "metro", "graph_metro_v1")
    assert "metro_route_map" in bundle.scene_templates
    assert len(bundle.query_templates["metro_exact_distance_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:metro_exact_distance_count"]) == ["query_label", "query_distance"]


def test_graph_path_bundle_supports_metro_shortest_path_length_query() -> None:
    bundle = load_scene_prompt_bundle("graph", "metro", "graph_metro_v1")
    assert "metro_route_map" in bundle.scene_templates
    assert len(bundle.query_templates["metro_shortest_path_length"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:metro_shortest_path_length"]) == ["source_label", "goal_label"]


def test_graph_relation_bundle_supports_same_component_count_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["same_component_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["same_component_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:same_component_count"]) == ["query_label"]


def test_graph_relation_bundle_supports_reachable_count_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["reachable_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["reachable_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:reachable_count"]) == ["query_label"]


def test_graph_relation_bundle_supports_common_neighbor_count_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["common_neighbor_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["common_neighbor_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["common_successor_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["common_predecessor_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:common_neighbor_count"]) == ["query_label_a", "query_label_b"]
    assert list(bundle.required_slots_by_key["query:common_successor_count"]) == ["query_label_a", "query_label_b"]
    assert list(bundle.required_slots_by_key["query:common_predecessor_count"]) == ["query_label_a", "query_label_b"]


def test_graph_relation_bundle_supports_component_size_after_edge_edit_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["component_size_after_edge_edit_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["component_size_after_edge_removal"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["component_size_after_edge_addition"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:component_size_after_edge_removal"]) == [
        "edit_label_a",
        "edit_label_b",
        "query_label",
    ]
    assert list(bundle.required_slots_by_key["query:component_size_after_edge_addition"]) == [
        "edit_label_a",
        "edit_label_b",
        "query_label",
    ]


def test_graph_relation_bundle_supports_reachable_count_after_edge_edit_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["reachable_count_after_edge_edit_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["reachable_count_after_edge_removal"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["reachable_count_after_edge_addition"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:reachable_count_after_edge_removal"]) == [
        "edit_label_a",
        "edit_label_b",
        "query_label",
    ]
    assert list(bundle.required_slots_by_key["query:reachable_count_after_edge_addition"]) == [
        "edit_label_a",
        "edit_label_b",
        "query_label",
    ]


def test_graph_relation_bundle_supports_unique_cycle_size_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["unique_cycle_size_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["unique_cycle_size"]) == REQUIRED_PROMPT_VARIANTS


def test_graph_relation_bundle_supports_largest_chordless_cycle_size_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["largest_chordless_cycle_size_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["largest_chordless_cycle_size"]) == REQUIRED_PROMPT_VARIANTS


def test_graph_relation_bundle_supports_hamiltonian_cycle_neighbor_label_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_relation_v0")
    assert "single_graph_relation" in bundle.scene_templates
    assert len(bundle.task_templates["hamiltonian_cycle_neighbor_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["next_in_hamiltonian_cycle_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["previous_in_hamiltonian_cycle_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:next_in_hamiltonian_cycle_label"]) == [
        "orientation_start_label",
        "orientation_final_label",
    ]
    assert list(bundle.required_slots_by_key["query:previous_in_hamiltonian_cycle_label"]) == [
        "orientation_start_label",
        "orientation_final_label",
    ]


def test_graph_pedigree_chart_scene_bundle_supports_label_queries() -> None:
    bundle = load_scene_prompt_bundle("graph", "pedigree_chart", "graph_pedigree_chart_v1")
    assert "pedigree_chart" in bundle.scene_templates
    assert len(bundle.task_templates["pedigree_chart_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["relationship_label_between_two_people"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["relatedness_coefficient_between_two_people"]) == REQUIRED_PROMPT_VARIANTS
    rendered = render_prompt(
        domain="graph",
        scene_id="pedigree_chart",
        bundle_id="graph_pedigree_chart_v1",
        scene_key="pedigree_chart",
        task_key="pedigree_chart_query",
        query_key="relationship_label_between_two_people",
        dynamic_slots={
            "object_description": "a pedigree chart with six relationship options",
            "person_label_a": "A",
            "person_label_b": "B",
            "json_output_contract": ANSWER_AND_ANNOTATION_CONTRACT,
            "json_output_contract_answer_only": ANSWER_ONLY_CONTRACT,
            "annotation_hint": 'set "annotation" to a keyed person-symbol bbox map',
            "answer_hint": "set \"answer\" to the exact option letter",
            "json_example": '{"annotation":{"person_a":[1,2,3,4],"person_b":[5,6,7,8]},"answer":"A"}',
            "json_example_answer_only": '{"answer":"A"}',
        },
        instance_seed=8123,
    )
    assert rendered.metadata["prompt_scene_id"] == "pedigree_chart"
    assert rendered.metadata["prompt_bundle_id"] == "graph_pedigree_chart_v1"


def test_graph_phylogeny_tree_scene_bundle_supports_tree_queries() -> None:
    bundle = load_scene_prompt_bundle("graph", "phylogeny_tree", "graph_phylogeny_tree_v1")
    assert "phylogeny_tree" in bundle.scene_templates
    assert "phylogeny_tree_options" in bundle.scene_templates
    assert len(bundle.task_templates["phylogeny_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["marked_clade_leaf_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["sister_leaf_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["mrca_leaf_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["topology_outlier_label"]) == REQUIRED_PROMPT_VARIANTS
    rendered = render_prompt(
        domain="graph",
        scene_id="phylogeny_tree",
        bundle_id="graph_phylogeny_tree_v1",
        scene_key="phylogeny_tree",
        task_key="phylogeny_query",
        query_key="sister_leaf_label",
        dynamic_slots={
            "object_description": "a rooted phylogeny cladogram with labeled taxa",
            "query_label": "A",
        },
        instance_seed=8124,
    )
    assert rendered.metadata["prompt_scene_id"] == "phylogeny_tree"
    assert rendered.metadata["prompt_bundle_id"] == "graph_phylogeny_tree_v1"


def test_graph_pipe_network_scene_bundle_supports_pipe_queries() -> None:
    bundle = load_scene_prompt_bundle("graph", "pipe_network", "graph_pipe_network_v1")
    assert "pipe_network" in bundle.scene_templates
    assert len(bundle.task_templates["pipe_network_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["pipe_shortest_path_length"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["pipe_bridge_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["pipe_reachable_junction_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["pipe_exact_distance_count"]) == REQUIRED_PROMPT_VARIANTS
    rendered = render_prompt(
        domain="graph",
        scene_id="pipe_network",
        bundle_id="graph_pipe_network_v1",
        scene_key="pipe_network",
        task_key="pipe_network_query",
        query_key="pipe_shortest_path_length",
        dynamic_slots={
            "object_description": "a labeled pipe-junction network with open pipes and blocked pipes",
            "source_label": "A",
            "goal_label": "F",
            "json_output_contract": ANSWER_AND_ANNOTATION_CONTRACT,
            "json_output_contract_answer_only": ANSWER_ONLY_CONTRACT,
            "annotation_hint": 'set "annotation" to an ordered array of [x,y] junction-center points',
            "answer_hint": 'set "answer" to the route length as an integer',
            "json_example": '{"annotation":[[1,2],[3,4]],"answer":1}',
            "json_example_answer_only": '{"answer":1}',
        },
        instance_seed=8126,
    )
    assert rendered.metadata["prompt_scene_id"] == "pipe_network"
    assert rendered.metadata["prompt_bundle_id"] == "graph_pipe_network_v1"


def test_graph_automaton_scene_bundle_supports_state_machine_queries() -> None:
    bundle = load_scene_prompt_bundle("graph", "automaton", "automaton_v1")
    assert "automaton" in bundle.scene_templates
    assert len(bundle.task_templates["state_after_input_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["accepted_string_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["nondeterministic_state_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["final_state_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["transition_step_state_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["dfa_accepted_string_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nfa_accepted_string_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nondeterministic_state_count"]) == REQUIRED_PROMPT_VARIANTS
    rendered = render_prompt(
        domain="graph",
        scene_id="automaton",
        bundle_id="automaton_v1",
        scene_key="automaton",
        task_key="state_after_input_label_query",
        query_key="transition_step_state_label",
        dynamic_slots={
            "object_description": "a deterministic state-transition diagram",
            "input_string": "0101",
            "transition_step_count": 2,
        },
        instance_seed=8125,
    )
    assert rendered.metadata["prompt_scene_id"] == "automaton"
    assert rendered.metadata["prompt_bundle_id"] == "automaton_v1"


def test_pages_schedule_bundle_supports_day_planner_queries() -> None:
    bundle = load_prompt_bundle("pages", "schedule", "pages_schedule_v0")
    assert "day_schedule" in bundle.scene_templates
    assert len(bundle.task_templates["schedule_day_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:day_schedule"]) == ["object_description"]


def test_pages_timeline_bundle_supports_milestone_queries() -> None:
    bundle = load_prompt_bundle("pages", "timeline", "pages_timeline_v0")
    assert "milestone_timeline" in bundle.scene_templates
    assert len(bundle.task_templates["timeline_milestone_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["interval_membership_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["event_date_gap_value"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:milestone_timeline"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:interval_membership_count"]) == [
        "interval_relation_description"
    ]
    assert list(bundle.required_slots_by_key["query:event_date_gap_value"]) == [
        "endpoint_pair_description"
    ]


def test_pages_step_list_bundle_supports_detail_lookup_queries() -> None:
    bundle = load_prompt_bundle("pages", "step_list", "pages_step_list_v0")
    assert "step_list" in bundle.scene_templates
    assert "instruction_panel" in bundle.scene_templates
    assert len(bundle.task_templates["step_lookup_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["instruction_panel_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["step_title_for_detail"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["step_number_for_detail"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["shared_control_for_step_set_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["step_for_control_pair_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:step_title_for_detail"]) == ["source_step_detail"]
    assert list(bundle.required_slots_by_key["query:step_number_for_detail"]) == ["source_step_detail"]
    assert list(bundle.required_slots_by_key["scene:instruction_panel"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:shared_control_for_step_set_label"]) == ["step_reference_list"]
    assert list(bundle.required_slots_by_key["query:step_for_control_pair_label"]) == [
        "first_control_label",
        "second_control_label",
    ]


def test_pages_document_lookup_bundle_supports_profile_ordering_queries() -> None:
    bundle = load_prompt_bundle("pages", "document_lookup", "pages_document_lookup_v0")
    assert "category_grid" not in bundle.scene_templates
    assert "comparison_panel" not in bundle.scene_templates
    assert "profile_card_grid" in bundle.scene_templates
    assert len(bundle.task_templates["profile_attribute_lookup_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["highest_field_profile_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["lowest_field_profile_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nth_highest_field_profile_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nth_lowest_field_profile_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:highest_field_profile_label"]) == ["field_label"]
    assert list(bundle.required_slots_by_key["query:lowest_field_profile_label"]) == ["field_label"]
    assert list(bundle.required_slots_by_key["query:nth_highest_field_profile_label"]) == [
        "field_label",
        "rank_ordinal",
    ]
    assert list(bundle.required_slots_by_key["query:nth_lowest_field_profile_label"]) == [
        "field_label",
        "rank_ordinal",
    ]


def test_pages_category_grid_scene_bundle_supports_lookup_queries() -> None:
    bundle = load_scene_prompt_bundle("pages", "category_grid", "pages_category_grid_v0")
    assert "category_grid" in bundle.scene_templates
    assert len(bundle.task_templates["category_grid_lookup_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["category_slot_item_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["category_item_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:category_slot_item_label"]) == [
        "category_label",
        "subcategory_label",
        "slot_ordinal",
    ]
    assert list(bundle.required_slots_by_key["query:category_item_count"]) == [
        "category_label",
        "subcategory_label",
    ]


def test_pages_comparison_panel_scene_bundle_supports_lookup_query() -> None:
    bundle = load_scene_prompt_bundle("pages", "comparison_panel", "pages_comparison_panel_v0")
    assert "comparison_panel" in bundle.scene_templates
    assert len(bundle.task_templates["comparison_panel_lookup_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["side_attribute_value_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:side_attribute_value_label"]) == [
        "side_label",
        "attribute_label",
    ]


def test_pages_infographic_bundle_supports_metric_ranked_item_queries() -> None:
    bundle = load_prompt_bundle("pages", "infographic", "pages_infographic_v0")
    assert "infographic_metric_arithmetic" in bundle.scene_templates
    assert "sectioned_infographic" in bundle.scene_templates
    assert "mixed_infographic_page" not in bundle.scene_templates
    assert len(bundle.task_templates["metric_arithmetic_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["sectioned_infographic_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["section_item_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["section_filtered_item_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:section_item_count"]) == ["target_section"]
    assert list(bundle.required_slots_by_key["query:section_filtered_item_label"]) == [
        "target_section",
        "filter_marker_label",
    ]
    for query_key in (
        "nth_highest_metric_label",
        "nth_lowest_metric_label",
        "nth_highest_metric_in_section_label",
        "nth_lowest_metric_in_section_label",
    ):
        assert len(bundle.query_templates[query_key]) == REQUIRED_PROMPT_VARIANTS
        assert len(set(bundle.query_templates[query_key])) == REQUIRED_PROMPT_VARIANTS

    assert list(bundle.required_slots_by_key["query:nth_highest_metric_label"]) == [
        "rank_ordinal",
        "rank_direction",
        "rank_order_phrase",
    ]
    assert list(bundle.required_slots_by_key["query:nth_lowest_metric_label"]) == [
        "rank_ordinal",
        "rank_direction",
        "rank_order_phrase",
    ]
    assert list(bundle.required_slots_by_key["query:nth_highest_metric_in_section_label"]) == [
        "target_section",
        "rank_ordinal",
        "rank_direction",
        "rank_order_phrase",
    ]
    assert list(bundle.required_slots_by_key["query:nth_lowest_metric_in_section_label"]) == [
        "target_section",
        "rank_ordinal",
        "rank_direction",
        "rank_order_phrase",
    ]


def test_pages_mixed_infographic_page_scene_bundle_supports_lookup_queries() -> None:
    bundle = load_scene_prompt_bundle("pages", "mixed_infographic_page", "pages_mixed_infographic_page_v0")
    assert "mixed_infographic_page" in bundle.scene_templates
    assert len(bundle.task_templates["mixed_infographic_lookup_query"]) == REQUIRED_PROMPT_VARIANTS
    for query_key in (
        "module_field_value_label",
        "module_field_extremum_item_label",
        "module_field_ranked_item_label",
        "page_field_extremum_module_label",
        "module_two_field_condition_item_label",
        "module_condition_item_count",
        "module_field_total_value",
        "two_module_field_total_comparison_module_label",
    ):
        assert len(bundle.query_templates[query_key]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:mixed_infographic_page"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:module_field_value_label"]) == [
        "module_title",
        "item_label",
        "field_label",
    ]


def test_graph_comparison_bundle_supports_largest_component_size_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_comparison_v0")
    assert "single_graph_comparison" in bundle.scene_templates
    assert len(bundle.task_templates["largest_component_size_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["extreme_degree_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["largest_component_size"]) == REQUIRED_PROMPT_VARIANTS
    for query_key in (
        "max_degree_value",
        "min_degree_value",
        "max_in_degree_value",
        "min_in_degree_value",
        "max_out_degree_value",
        "min_out_degree_value",
        "max_total_degree_value",
        "min_total_degree_value",
    ):
        assert len(bundle.query_templates[query_key]) == REQUIRED_PROMPT_VARIANTS
        assert list(bundle.required_slots_by_key[f"query:{query_key}"]) == []


def test_graph_path_bundle_supports_shortest_path_length_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_path_v0")
    assert "single_graph_path" in bundle.scene_templates
    assert len(bundle.task_templates["shortest_path_length_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["longest_path_length_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["shortest_path_length"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["directed_shortest_path_length"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["directed_longest_path_length"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:directed_longest_path_length"]) == []


def test_graph_order_bundle_supports_topological_endpoint_queries() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_order_v0")
    assert "single_graph_order" in bundle.scene_templates
    assert len(bundle.task_templates["topological_endpoint_node_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["first_in_topological_order_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["last_in_topological_order_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:first_in_topological_order_label"]) == []
    assert list(bundle.required_slots_by_key["query:last_in_topological_order_label"]) == []


def test_symbolic_clock_bundle_supports_offset_variants() -> None:
    bundle = load_prompt_bundle("symbolic", "clock", "symbolic_clock_v0")
    assert "analog_clock" in bundle.scene_templates
    assert "multi_analog_clock" in bundle.scene_templates
    assert "clock_match_panel" in bundle.scene_templates
    assert len(bundle.task_templates["clock_readout_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["clock_compare_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["clock_match_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["offset_time"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["time_extremum_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["analog_reference_digital_options"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["digital_reference_analog_options"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:analog_clock"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["scene:multi_analog_clock"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["scene:clock_match_panel"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:offset_time"]) == [
        "delta_value",
        "offset_unit",
        "offset_direction",
        "answer_format",
    ]
    assert list(bundle.required_slots_by_key["query:time_extremum_label"]) == ["extremum_direction"]
    assert list(bundle.required_slots_by_key["query:analog_reference_digital_options"]) == []
    assert list(bundle.required_slots_by_key["query:digital_reference_analog_options"]) == []


def test_symbolic_abacus_bundle_supports_displayed_value_readout() -> None:
    bundle = load_prompt_bundle("symbolic", "abacus", "symbolic_abacus_v0")
    assert "abacus_readout" in bundle.scene_templates
    assert "abacus_match_panel" in bundle.scene_templates
    assert len(bundle.task_templates["abacus_displayed_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["abacus_target_value_match_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["displayed_value_readout"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["target_value_match_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:abacus_readout"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["scene:abacus_match_panel"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:displayed_value_readout"]) == []
    assert list(bundle.required_slots_by_key["query:target_value_match_label"]) == ["target_value"]


def test_pages_calendar_bundle_supports_month_view_variants() -> None:
    bundle = load_prompt_bundle("pages", "calendar", "pages_calendar_v0")
    assert "month_calendar" in bundle.scene_templates
    assert "calendar_event_grid" not in bundle.scene_templates
    assert len(bundle.task_templates["calendar_month_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["date_of_weekday_occurrence"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["count_marked_day_class"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["workday_after_offset_date"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["workday_before_offset_date"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:month_calendar"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:date_of_weekday_occurrence"]) == ["ordinal", "weekday_name"]
    assert list(bundle.required_slots_by_key["query:count_marked_day_class"]) == [
        "marked_day_class",
        "marked_day_class_phrase",
    ]
    assert list(bundle.required_slots_by_key["query:workday_after_offset_date"]) == ["workday_offset"]
    assert list(bundle.required_slots_by_key["query:workday_before_offset_date"]) == ["workday_offset"]


def test_pages_calendar_event_grid_scene_bundle_supports_lookup_queries() -> None:
    bundle = load_scene_prompt_bundle("pages", "calendar_event_grid", "pages_calendar_event_grid_v0")
    assert "calendar_event_grid" in bundle.scene_templates
    assert len(bundle.task_templates["calendar_event_grid_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["date_slot_category_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["category_slot_day_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["date_for_category_slot_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:calendar_event_grid"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:date_slot_category_label"]) == ["date_number", "slot_label"]
    assert list(bundle.required_slots_by_key["query:category_slot_day_count"]) == ["category_label", "slot_label"]
    assert list(bundle.required_slots_by_key["query:date_for_category_slot_label"]) == ["category_label", "slot_label"]


def test_pages_schema_bundle_supports_relationship_endpoint_query() -> None:
    bundle = load_prompt_bundle("pages", "schema", "pages_schema_v0")
    assert len(bundle.task_templates["relationship_endpoint_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["relationship_cardinality_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["target_table_for_relationship_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["relationship_cardinality_between_tables"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:relationship_endpoint_label_query"]) == [
        "source_table_label",
        "relationship_label",
    ]
    assert list(bundle.required_slots_by_key["task:relationship_cardinality_label_query"]) == [
        "source_table_label",
        "target_table_label",
    ]
    assert list(bundle.required_slots_by_key["query:target_table_for_relationship_label"]) == []
    assert list(bundle.required_slots_by_key["query:relationship_cardinality_between_tables"]) == []


def test_graph_optimization_bundle_supports_minimum_spanning_tree_weight_query() -> None:
    bundle = load_prompt_bundle("graph", "node_link", "graph_optimization_v0")
    assert "single_graph_optimization" in bundle.scene_templates
    assert len(bundle.task_templates["minimum_spanning_tree_weight_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["minimum_spanning_tree_weight"]) == REQUIRED_PROMPT_VARIANTS


def test_cell_board_reachability_bundle_supports_region_size_query() -> None:
    bundle = load_prompt_bundle("puzzles", "cell_board_reachability", "puzzles_cell_board_reachability_v0")
    assert len(bundle.task_templates["region_size_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:region_size_query"]) == ["obstacle_color", "start_color"]


def test_cell_board_path_bundle_supports_shortest_path_and_reachable_target_queries() -> None:
    bundle = load_prompt_bundle("puzzles", "cell_board_path", "puzzles_cell_board_path_v0")
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


def test_cell_board_relation_bundle_supports_min_distance_query() -> None:
    bundle = load_prompt_bundle("puzzles", "cell_board_relation", "puzzles_cell_board_relation_v0")
    assert len(bundle.task_templates["min_distance_query"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["task:min_distance_query"]) == [
        "color_a",
        "color_b",
    ]


def test_charts_statistics_bundle_supports_summary_variants() -> None:
    bundle = load_prompt_bundle("charts", "statistics", "charts_statistics_v0")
    assert len(bundle.task_templates["summary_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["summary_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["median"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nth_highest"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nth_lowest"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["median_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nth_highest_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["nth_lowest_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:labeled_chart_statistics"]) == ["object_description"]


def test_charts_counting_bundle_supports_value_count_variants() -> None:
    bundle = load_prompt_bundle("charts", "counting", "charts_counting_v0")
    assert len(bundle.task_templates["value_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["threshold_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["in_interval"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:labeled_chart_counting"]) == ["object_description"]


def test_charts_radar_bundle_supports_profile_queries() -> None:
    bundle = load_prompt_bundle("charts", "radar", "charts_radar_v0")
    assert len(bundle.task_templates["radar_profile_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["highlighted_metric_threshold_panel_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["threshold_metric_count_for_panel"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["profile_advantage_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["matching_condition_panel_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:radar_profile_charts"]) == ["object_description"]


def test_tables_statistics_bundle_supports_filtered_subset_variants() -> None:
    bundle = load_prompt_bundle("charts", "table", "charts_table_statistics_v1")
    assert len(bundle.task_templates["summary_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["column_sum"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["column_mean"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["column_median"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["filtered_subset_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["above_threshold_filtered_mean"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["below_threshold_filtered_mean"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["interval_filtered_mean"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:interval_filtered_mean"]) == [
        "query_filter_column",
        "query_target_column",
        "filter_condition",
    ]


def test_tables_ranking_bundle_supports_kth_label_variants() -> None:
    bundle = load_prompt_bundle("charts", "table", "charts_table_ranking_v1")
    assert len(bundle.task_templates["rank_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["highest_rank_in_column"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["lowest_rank_in_column"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:styled_table_ranking"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:highest_rank_in_column"]) == [
        "query_column",
        "query_rank",
        "rank_direction",
    ]


def test_tables_counting_bundle_supports_value_count_variants() -> None:
    bundle = load_prompt_bundle("charts", "table", "charts_table_counting_v1")
    assert len(bundle.task_templates["value_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["above_threshold_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["below_threshold_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["interval_value_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["categorical_value_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["query:above_threshold_count"]) == [
        "query_column",
        "threshold_value",
    ]
    assert list(bundle.required_slots_by_key["query:interval_value_count"]) == [
        "query_column",
        "interval_min",
        "interval_max",
    ]
    assert list(bundle.required_slots_by_key["query:categorical_value_count"]) == [
        "query_column",
        "target_category",
    ]


def test_tables_temporal_bundle_supports_year_conditioned_variants() -> None:
    bundle = load_prompt_bundle("charts", "table", "charts_table_temporal_v1")
    assert len(bundle.task_templates["temporal_value_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["absolute_difference_between_rows_over_year_interval"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["sum_absolute_differences_between_rows_over_year_interval"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:styled_table_temporal"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:absolute_difference_between_rows_over_year_interval"]) == [
        "query_row_label_a",
        "query_row_label_b",
        "query_year_start",
        "query_year_end",
    ]
    assert list(bundle.required_slots_by_key["query:sum_absolute_differences_between_rows_over_year_interval"]) == [
        "query_row_label_a",
        "query_row_label_b",
        "query_year_start",
        "query_year_end",
    ]


def test_puzzles_logic_bundle_supports_grid_completion_variants() -> None:
    bundle = load_prompt_bundle("puzzles", "logic", "puzzles_logic_v0")
    assert len(bundle.task_templates["grid_completion_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["raven_matrix_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["nonogram_line_completion_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["nonogram_candidate_solution_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["tents_missing_tent_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["tents_valid_candidate_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["star_battle_valid_cell_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["star_battle_remaining_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["axis_uniqueness"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["row_and_column_uniqueness"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["line_completion_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["candidate_solution_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["missing_tent_cell_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_candidate_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_cell_anywhere_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_cell_in_marked_region_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_cell_for_marked_row_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["remaining_valid_cells_in_marked_region_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["remaining_valid_cells_in_marked_row_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["remaining_valid_cells_in_marked_column_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:logic_option_completion_puzzle"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["scene:raven_matrix_puzzle"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["scene:nonogram"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["scene:tents"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["scene:star_battle"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["query:axis_uniqueness"]) == ["uniqueness_axis"]
    assert list(bundle.required_slots_by_key["query:line_completion_label"]) == ["line_label"]


def test_symbolic_probability_bundle_supports_spinner_variants() -> None:
    bundle = load_prompt_bundle("symbolic", "probability", "symbolic_probability_v0")
    assert len(bundle.task_templates["single_dice_probability_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["pair_dice_probability_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["conditional_dice_probability_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["single_spinner_probability_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["pair_spinner_probability_query"]) == REQUIRED_PROMPT_VARIANTS
    dice_event_queries = (
        "single_parity_probability",
        "single_threshold_probability",
        "single_value_set_probability",
        "single_color_and_value_probability",
        "single_color_or_value_probability",
        "pair_sum_probability",
        "pair_sum_threshold_probability",
        "pair_difference_probability",
        "pair_parity_combo_probability",
        "pair_color_value_combo_probability",
    )
    for query_key in dice_event_queries:
        assert len(bundle.query_templates[query_key]) == REQUIRED_PROMPT_VARIANTS
        assert list(bundle.required_slots_by_key[f"query:{query_key}"]) == ["event_description"]
    for query_key in (
        "conditional_value_property_given_color_probability",
        "conditional_color_given_value_property_probability",
        "conditional_color_given_value_set_probability",
    ):
        assert len(bundle.query_templates[query_key]) == REQUIRED_PROMPT_VARIANTS
        assert list(bundle.required_slots_by_key[f"query:{query_key}"]) == ["given_description", "event_description"]
    for query_key in (
        "single_color_probability",
        "single_shape_probability",
        "single_color_and_shape_probability",
        "single_color_or_shape_probability",
        "pair_both_target_color_probability",
        "pair_at_least_one_target_color_probability",
        "pair_same_color_probability",
    ):
        assert len(bundle.query_templates[query_key]) == REQUIRED_PROMPT_VARIANTS
        assert list(bundle.required_slots_by_key[f"query:{query_key}"]) == ["event_description"]
    assert list(bundle.required_slots_by_key["scene:dice_probability"]) == ["object_description"]
    assert list(bundle.required_slots_by_key["scene:spinner_probability"]) == ["object_description"]


def test_puzzles_spatial_bundle_supports_fold_result_variants() -> None:
    bundle = load_prompt_bundle("puzzles", "spatial", "puzzles_spatial_v0")
    assert len(bundle.task_templates["transform_result_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["paper_fold_result"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["paper_fold_cut_result"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["overlay_result"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:spatial_transform_result_puzzle"]) == [
        "object_description",
    ]


def test_puzzles_spatial_bundle_supports_cube_structure_variants() -> None:
    bundle = load_prompt_bundle("puzzles", "spatial", "puzzles_spatial_v0")
    assert len(bundle.task_templates["cube_structure_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["total_cube_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["missing_to_complete_cuboid_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["removed_cube_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["painted_exterior_face_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["exact_k_painted_faces_cube_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["visible_cube_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:spatial_cube_structure_puzzle"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["query:visible_cube_count"]) == [
        "view_direction",
        "view_direction_description",
    ]


def test_games_sliding_block_bundle_supports_sliding_block_variants() -> None:
    bundle = load_prompt_bundle("games", "sliding_block", "games_sliding_block_v1")
    assert len(bundle.task_templates["sliding_block_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["blocker_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["movable_block_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["horizontal_block_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["vertical_block_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["move_result_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:sliding_block"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["query:move_result_label"]) == [
        "move_sequence_description",
    ]
    assert list(bundle.required_slots_by_key["query:horizontal_block_count"]) == []
    assert list(bundle.required_slots_by_key["query:vertical_block_count"]) == []


def test_puzzles_topology_bundle_supports_cyclic_order_variants() -> None:
    bundle = load_prompt_bundle("puzzles", "topology", "puzzles_topology_v0")
    assert len(bundle.task_templates["cyclic_order_match_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["cyclic_order_equivalent_label"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:topology_cyclic_order_puzzle"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["query:cyclic_order_equivalent_label"]) == [
        "token_render_style_instruction",
    ]


def test_puzzles_topology_bundle_supports_maze_exit_variants() -> None:
    bundle = load_prompt_bundle("puzzles", "topology", "puzzles_topology_v0")
    assert len(bundle.task_templates["maze_exit_label_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["exit_reachability_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["reachable_exit_count"]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:topology_maze_exit_puzzle"]) == [
        "object_description",
    ]
    assert list(bundle.required_slots_by_key["query:exit_reachability_label"]) == [
        "target_reachability_description",
    ]


def test_geometry_task_templates_avoid_awkward_comma_question_prefixes() -> None:
    bundle_coords = (
        ("geometry", "measurement", "geometry_measurement_v0", "measurement_query"),
        (
            "geometry",
            "analytical",
            "geometry_analytical_function_property_v0",
            "analytical_function_property_query",
        ),
        (
            "geometry",
            "analytical",
            "geometry_analytical_intersection_property_v0",
            "analytical_intersection_property_query",
        ),
    )
    for domain, scene_id, bundle_id, task_key in bundle_coords:
        bundle = load_prompt_bundle(domain, scene_id, bundle_id)
        templates = bundle.task_templates[task_key]
        assert all(", {question_text}" not in str(template) for template in templates)


def test_geometry_measurement_task_templates_do_not_repeat_graph_paper_reference() -> None:
    bundle = load_prompt_bundle("geometry", "measurement", "geometry_measurement_v0")
    templates = bundle.task_templates["measurement_query"]
    assert all("graph-paper image" not in str(template).lower() for template in templates)
    assert all("graph-paper diagram" not in str(template).lower() for template in templates)


def test_prompt_json_examples_use_non_degenerate_point_layouts() -> None:
    example_json, _ = build_prompt_json_examples(
        annotation_value={"A": [9, 9], "B": [8, 8], "C": [7, 7], "D": [6, 6]},
        answer_type="integer",
    )
    payload = json.loads(example_json)
    assert payload["annotation"] == {
        "A": [0, 0],
        "B": [4, 0],
        "C": [4, 2],
        "D": [0, 2],
    }


def test_dump_prompt_json_examples_uses_compact_answer_contract() -> None:
    answer_and_annotation, answer_only = dump_prompt_json_examples(
        annotation={"angle": [120, 180], "side": [220, 240]},
        answer="12π",
        ensure_ascii=False,
    )
    assert answer_and_annotation == '{"annotation":{"angle":[120,180],"side":[220,240]},"answer":"12π"}'
    assert answer_only == '{"answer":"12π"}'
