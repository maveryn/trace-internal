"""Tests for prompt/evidence contract audit helpers."""

from __future__ import annotations

from scripts import audit_prompt_evidence_contracts as audit


def test_extract_example_json_reads_first_object_after_marker() -> None:
    prompt = 'Evidence format: use boxes.\nExample JSON: {"evidence":[[1,2,3,4]],"answer":2}\n'

    example, error = audit._extract_example_json(prompt)

    assert error == ""
    assert example == {"evidence": [[1, 2, 3, 4]], "answer": 2}


def test_redundancy_detector_flags_adjacent_overlap() -> None:
    prompt = (
        "Count the marked cells in the grid. "
        "Count the marked cells in the grid carefully.\n"
        "Answer format: use JSON."
    )

    issues = audit._find_redundancy_issues(prompt, mode="answer_only")

    assert any(issue["code"] == "adjacent_sentence_overlap" for issue in issues)


def test_validate_bbox_set_checks_pixel_bounds_and_area() -> None:
    valid = audit._validate_evidence_value(
        "bbox_set",
        [[1, 2, 10, 12]],
        image_size=(32, 32),
    )
    invalid = audit._validate_evidence_value(
        "bbox_set",
        [[1, 2, 1, 12], [0, 0, 40, 10]],
        image_size=(32, 32),
    )

    assert valid == []
    assert any("positive-area" in message for message in invalid)
    assert any("outside image bounds" in message for message in invalid)


def test_validate_bbox_sequence_checks_pixel_bounds_and_area() -> None:
    valid = audit._validate_evidence_value(
        "bbox_sequence",
        [[1, 2, 10, 12]],
        image_size=(32, 32),
    )
    invalid = audit._validate_evidence_value(
        "bbox_sequence",
        [[1, 2, 1, 12], [0, 0, 40, 10]],
        image_size=(32, 32),
    )

    assert valid == []
    assert any("positive-area" in message for message in invalid)
    assert any("outside image bounds" in message for message in invalid)


def test_validate_point_sequence_checks_pixel_bounds() -> None:
    valid = audit._validate_evidence_value(
        "point_sequence",
        [[1, 2], [3, 4]],
        image_size=(10, 10),
    )
    invalid = audit._validate_evidence_value(
        "point_sequence",
        [[1, 2], [30, 4]],
        image_size=(10, 10),
    )

    assert valid == []
    assert any("outside image bounds" in message for message in invalid)


def test_validate_point_pair_set_checks_nested_points() -> None:
    valid = audit._validate_evidence_value(
        "point_pair_set",
        [[[1, 2], [3, 4]]],
        image_size=(10, 10),
    )
    invalid = audit._validate_evidence_value(
        "point_pair_set",
        [[[1, 2], [30, 4]], [[1, 2, 3]]],
        image_size=(10, 10),
    )

    assert valid == []
    assert any("outside image bounds" in message for message in invalid)
    assert any("not a two-point pair" in message for message in invalid)
