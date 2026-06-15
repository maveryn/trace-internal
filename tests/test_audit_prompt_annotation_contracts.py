"""Tests for prompt/annotation contract audit helpers."""

from __future__ import annotations

from scripts import audit_prompt_annotation_contracts as cli_audit
from trace.core import prompt_annotation_contract_audit as audit


def test_cli_wrapper_reexports_core_helpers() -> None:
    assert cli_audit._validate_annotation_value is audit._validate_annotation_value


def test_extract_example_json_reads_first_object_after_marker() -> None:
    prompt = 'Annotation format: use boxes.\nExample JSON: {"annotation":[[1,2,3,4]],"answer":2}\n'

    example, error = audit._extract_example_json(prompt)

    assert error == ""
    assert example == {"annotation": [[1, 2, 3, 4]], "answer": 2}


def test_redundancy_detector_flags_adjacent_overlap() -> None:
    prompt = (
        "Count the marked cells in the grid. "
        "Count the marked cells in the grid carefully.\n"
        "Answer format: use JSON."
    )

    issues = audit._find_redundancy_issues(prompt, mode="answer_only")

    assert any(issue["code"] == "adjacent_sentence_overlap" for issue in issues)


def test_annotation_prompt_audit_rejects_negative_annotation_format_instructions() -> None:
    prompt = (
        "Find the matching objects.\n"
        "Annotation format: set \"annotation\" to boxes [x0, y0, x1, y1] around the target objects; "
        "do not include labels.\n"
        "Example JSON: {\"annotation\":[[1,2,10,12]],\"answer\":2}"
    )

    issues = audit._audit_annotation_prompt(prompt, annotation_type="bbox_set", mode="answer_and_annotation")

    assert any(issue["code"] == "negative_annotation_format_instruction" for issue in issues)


def test_annotation_prompt_audit_rejects_degenerate_point_examples() -> None:
    prompt = (
        'Annotation format: set "annotation" to a JSON object mapping each key to a pixel point [x,y].\n'
        'Example JSON:\n'
        '{"annotation":{"A":[320,240],"B":[320,240],"C":[320,240],"D":[320,240]},"answer":8}'
    )

    issues = audit._audit_annotation_prompt(prompt, annotation_type="keyed_point_map", mode="answer_and_annotation")

    assert any(issue["code"] == "degenerate_example_points" for issue in issues)


def test_validate_bbox_set_checks_pixel_bounds_and_area() -> None:
    valid = audit._validate_annotation_value(
        "bbox_set",
        [[1, 2, 10, 12]],
        image_size=(32, 32),
    )
    invalid = audit._validate_annotation_value(
        "bbox_set",
        [[1, 2, 1, 12], [0, 0, 40, 10]],
        image_size=(32, 32),
    )

    assert valid == []
    assert any("positive-area" in message for message in invalid)
    assert any("outside image bounds" in message for message in invalid)


def test_validate_bbox_sequence_checks_pixel_bounds_and_area() -> None:
    valid = audit._validate_annotation_value(
        "bbox_sequence",
        [[1, 2, 10, 12]],
        image_size=(32, 32),
    )
    invalid = audit._validate_annotation_value(
        "bbox_sequence",
        [[1, 2, 1, 12], [0, 0, 40, 10]],
        image_size=(32, 32),
    )

    assert valid == []
    assert any("positive-area" in message for message in invalid)
    assert any("outside image bounds" in message for message in invalid)


def test_validate_point_sequence_checks_pixel_bounds() -> None:
    valid = audit._validate_annotation_value(
        "point_sequence",
        [[1, 2], [3, 4]],
        image_size=(10, 10),
    )
    invalid = audit._validate_annotation_value(
        "point_sequence",
        [[1, 2], [30, 4]],
        image_size=(10, 10),
    )

    assert valid == []
    assert any("outside image bounds" in message for message in invalid)


def test_validate_segment_set_checks_nested_points() -> None:
    valid = audit._validate_annotation_value(
        "segment_set",
        [[[1, 2], [3, 4]]],
        image_size=(10, 10),
    )
    invalid = audit._validate_annotation_value(
        "segment_set",
        [[[1, 2], [30, 4]], [[1, 2, 3]]],
        image_size=(10, 10),
    )

    assert valid == []
    assert any("outside image bounds" in message for message in invalid)
    assert any("not a two-endpoint segment" in message for message in invalid)


def test_validate_segment_checks_nested_points() -> None:
    valid = audit._validate_annotation_value(
        "segment",
        [[1, 2], [3, 4]],
        image_size=(10, 10),
    )
    invalid = audit._validate_annotation_value(
        "segment",
        [[1, 2], [30, 4]],
        image_size=(10, 10),
    )
    wrong_shape = audit._validate_annotation_value(
        "segment",
        [[[1, 2], [3, 4]]],
        image_size=(10, 10),
    )

    assert valid == []
    assert any("outside image bounds" in message for message in invalid)
    assert any("one two-endpoint segment" in message for message in wrong_shape)


def test_validate_keyed_point_map_checks_keys_points_and_bounds() -> None:
    valid = audit._validate_annotation_value(
        "keyed_point_map",
        {"A": [1, 2], "B": [3, 4]},
        image_size=(10, 10),
    )
    invalid = audit._validate_annotation_value(
        "keyed_point_map",
        {"": [1, 2], "B": [30, 4]},
        image_size=(10, 10),
    )

    assert valid == []
    assert any("empty key" in message for message in invalid)
    assert any("outside image bounds" in message for message in invalid)


def test_validate_keyed_bbox_map_checks_keys_boxes_and_bounds() -> None:
    valid = audit._validate_annotation_value(
        "keyed_bbox_map",
        {"source": [1, 2, 5, 6], "target": [6, 2, 9, 6]},
        image_size=(10, 10),
    )
    invalid = audit._validate_annotation_value(
        "keyed_bbox_map",
        {"": [1, 2, 5, 6], "target": [6, 2, 20, 6]},
        image_size=(10, 10),
    )

    assert valid == []
    assert any("empty key" in message for message in invalid)
    assert any("outside image bounds" in message for message in invalid)


def test_collect_task_records_uses_explicit_variant_manifest(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate_explicit_samples(**kwargs):
        captured.update(kwargs)
        return [], {"task": kwargs["task_id"], "sampling_mode": "explicit_manifest"}

    monkeypatch.setitem(
        audit._EXPLICIT_VARIANT_PARAMS,
        "task_test__scene__branch",
        [("branch_a", {"query_id": "branch_a"})],
    )
    monkeypatch.setattr(audit, "_generate_explicit_samples", fake_generate_explicit_samples)

    records, coverage = audit._collect_task_records(
        task_id="task_test__scene__branch",
        samples_per_query_id=1,
        seed=123,
        max_attempts=4,
        max_total_samples_per_task=8,
        workers=1,
    )

    assert records == []
    assert coverage["sampling_mode"] == "explicit_manifest"
    assert captured["variants"] == [("branch_a", {"query_id": "branch_a"})]
