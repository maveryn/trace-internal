"""Contract tests for illustration library tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.counting.library_book_count import _sample_spec as _sample_library_book_spec


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1


def test_books_in_section_count_contract() -> None:
    out = create_task("task_illustrations__library__books_in_section_count").generate(
        hash64(2026052404, "library-books-section", 0),
        params={"query_id": "books_in_section_count", "section_key": "science", "target_count": 7, "section_count": 4},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_book_ids = execution["counted_book_ids"]
    book_bboxes = trace["render_map"]["book_bboxes_px"]

    assert out.scene_id == "library"
    assert out.query_id == "books_in_section_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 7
    assert len(counted_book_ids) == 7
    assert execution["target_section_key"] == "science"
    assert sorted(out.annotation_gt.value) == sorted(book_bboxes[book_id] for book_id in counted_book_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for book in execution["books"]:
        if book["book_id"] in set(counted_book_ids):
            assert book["section_key"] == "science"
        else:
            assert book["section_key"] != "science"


def test_books_in_section_countseeded_sampler_covers_answer_counts() -> None:
    answers = [
        _sample_library_book_spec(
            instance_seed=hash64(2026052404, "library-books-section-sampling", index),
            params={"query_id": "books_in_section_count"},
            attempt_index=0,
        ).target_count
        for index in range(100)
    ]
    counts = Counter(answers)
    _assert_hash_balanced_counts(counts, range(3, 9))


def test_book_color_count_contract() -> None:
    out = create_task("task_illustrations__library__filtered_book_in_section_count").generate(
        hash64(2026052405, "library-book-color", 0),
        params={
            "query_id": "book_color_in_section_count",
            "section_key": "history",
            "color_name": "red",
            "target_count": 4,
            "section_count": 5,
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_book_ids = execution["counted_book_ids"]
    book_bboxes = trace["render_map"]["book_bboxes_px"]

    assert out.scene_id == "library"
    assert out.query_id == "book_color_in_section_count"
    assert int(out.answer_gt.value) == 4
    assert len(counted_book_ids) == 4
    assert execution["target_section_key"] == "history"
    assert execution["target_color_name"] == "red"
    assert execution["target_color_label"] == "red [#E63232]"
    assert sorted(out.annotation_gt.value) == sorted(book_bboxes[book_id] for book_id in counted_book_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for book in execution["books"]:
        is_target = book["section_key"] == "history" and book["color_name"] == "red"
        assert (book["book_id"] in set(counted_book_ids)) == is_target


def test_book_color_countseeded_sampler_covers_answer_counts() -> None:
    samples = [
        _sample_library_book_spec(
            instance_seed=hash64(2026052405, "library-book-color-sampling", index),
            params={"query_id": "book_color_in_section_count"},
            attempt_index=0,
        )
        for index in range(100)
    ]
    counts = Counter(sample.target_count for sample in samples)
    _assert_hash_balanced_counts(counts, range(1, 7))
    assert {sample.color_name for sample in samples} >= {"red", "blue", "green", "orange", "purple"}


def test_book_orientation_count_contract() -> None:
    out = create_task("task_illustrations__library__filtered_book_in_section_count").generate(
        hash64(2026052406, "library-book-orientation", 0),
        params={"query_id": "horizontal_book_in_section_count", "section_key": "art", "target_count": 3, "section_count": 4},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_book_ids = execution["counted_book_ids"]
    book_bboxes = trace["render_map"]["book_bboxes_px"]

    assert out.scene_id == "library"
    assert out.query_id == "horizontal_book_in_section_count"
    assert trace["query_spec"]["query_id"] == "horizontal_book_in_section_count"
    assert int(out.answer_gt.value) == 3
    assert len(counted_book_ids) == 3
    assert execution["target_section_key"] == "art"
    assert execution["target_orientation"] == "horizontal"
    assert sorted(out.annotation_gt.value) == sorted(book_bboxes[book_id] for book_id in counted_book_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for book in execution["books"]:
        is_target = book["section_key"] == "art" and book["orientation"] == "horizontal"
        assert (book["book_id"] in set(counted_book_ids)) == is_target


def test_book_orientation_countseeded_sampler_covers_answer_counts_and_variants() -> None:
    samples = [
        _sample_library_book_spec(
            instance_seed=hash64(2026052406, "library-book-orientation-sampling", index),
            params={"query_id_support": ["upright_book_in_section_count", "horizontal_book_in_section_count"]},
            attempt_index=0,
        )
        for index in range(100)
    ]
    counts = Counter(sample.target_count for sample in samples)
    _assert_hash_balanced_counts(counts, range(1, 7))
    assert {sample.query_id for sample in samples} == {"upright_book_in_section_count", "horizontal_book_in_section_count"}
