"""Contract tests for shared illustration visual tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.visual.missing_patch_label import _GEN_DEFAULTS as _MISSING_PATCH_GEN_DEFAULTS
from trace.tasks.illustrations.visual.jigsaw_piece_order import _sample_spec as _sample_jigsaw_spec
from trace.tasks.illustrations.visual.object_difference_count import _sample_spec as _sample_difference_spec
from trace.tasks.illustrations.visual.odd_scene_label import _sample_spec as _sample_odd_scene_spec


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.85) + 1


def test_object_difference_count_variants_contract() -> None:
    for index, variant in enumerate(
        ["added_object_count", "removed_object_count", "changed_color_object_count", "moved_object_count"]
    ):
        out = create_task("task_illustrations__difference_pair__object_difference_count").generate(
            hash64(2026052501, "object-difference", index),
            params={"query_id": variant, "target_count": 2, "object_count": 9},
            max_attempts=300,
        )
        trace = out.trace_payload
        assert out.scene_id == "difference_pair"
        assert out.query_id == variant
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == 2
        assert len(out.evidence_gt.value) == 2
        assert len(trace["execution_trace"]["changed_object_ids"]) == 2
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value


def test_object_differenceseeded_sampler_balances_variants_and_answers() -> None:
    samples = [
        _sample_difference_spec(
            instance_seed=hash64(2026052501, "object-difference-sampling", index),
            params={},
        )
        for index in range(100)
    ]
    query_id_counts = Counter(sample.variant for sample in samples)
    answer_counts = Counter(sample.target_count for sample in samples)
    _assert_hash_balanced_counts(
        query_id_counts,
        {
            "added_object_count",
            "removed_object_count",
            "changed_color_object_count",
            "moved_object_count",
        },
    )
    _assert_hash_balanced_counts(answer_counts, [1, 2, 3, 4, 5])


def test_jigsaw_piece_order_contract() -> None:
    out = create_task("task_illustrations__image_cutout_board__jigsaw_piece_order").generate(
        hash64(2026052502, "jigsaw-piece-order", 0),
        params={"board_shape": "board_2x2", "source_task_id": "task_illustrations__library__section_book_count"},
        max_attempts=300,
    )
    trace = out.trace_payload
    labels = str(out.answer_gt.value).split()
    assert out.scene_id == "image_cutout_board"
    assert out.query_id == "jigsaw_piece_order"
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "bbox_sequence"
    assert len(labels) == 3
    assert set(labels) == {"1", "2", "3"}
    assert len(out.evidence_gt.value) == 3
    assert trace["projected_evidence"]["bbox_sequence"] == out.evidence_gt.value
    assert trace["scene_ir"]["entities"]["source_image_shown"] is False
    assert trace["scene_ir"]["entities"]["anchored_piece"] == {"position": "top_left", "content_index": 0}
    assert trace["scene_ir"]["entities"]["source_scene_id"] != "object_field"
    assert trace["render_map"]["display_grid_shape"] == [2, 2]
    assert trace["render_map"]["anchored_content_index"] == 0
    assert trace["render_map"]["answer_positions"] == ["top_right", "bottom_left", "bottom_right"]
    assert sorted(trace["render_map"]["display_order_content_indices"]) == [1, 2, 3]
    assert trace["query_spec"]["params"]["board_shape"] == "board_2x2"
    assert trace["query_spec"]["params"]["option_piece_count"] == 3
    assert "3 remaining piece labels" in out.prompt


def test_jigsaw_piece_order_one_by_three_contract() -> None:
    out = create_task("task_illustrations__image_cutout_board__jigsaw_piece_order").generate(
        hash64(2026052502, "jigsaw-piece-order-1x3", 0),
        params={"board_shape": "board_1x3", "source_task_id": "task_illustrations__library__section_book_count"},
        max_attempts=300,
    )
    trace = out.trace_payload
    labels = str(out.answer_gt.value).split()
    assert out.scene_id == "image_cutout_board"
    assert out.query_id == "jigsaw_piece_order"
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "bbox_sequence"
    assert len(labels) == 2
    assert set(labels) == {"1", "2"}
    assert len(out.evidence_gt.value) == 2
    assert trace["scene_ir"]["entities"]["anchored_piece"] == {"position": "left", "content_index": 0}
    assert trace["render_map"]["display_grid_shape"] == [1, 3]
    assert trace["render_map"]["answer_positions"] == ["middle", "right"]
    assert trace["query_spec"]["params"]["board_shape"] == "board_1x3"
    assert trace["query_spec"]["params"]["option_piece_count"] == 2
    assert "2 remaining piece labels" in out.prompt


def test_jigsaw_piece_orderseeded_sampler_decouples_shape_and_answer_order() -> None:
    counts: Counter[str] = Counter()
    for index in range(48):
        sample = _sample_jigsaw_spec(
            instance_seed=hash64(2026052502, "jigsaw-piece-order-sampling", index),
            params={},
        )
        shape = str(sample.board_shape)
        counts[shape] += 1
        assert sample.source_sample_index is None
        assert sample.option_permutation_index is None
    _assert_hash_balanced_counts(counts, {"board_1x3", "board_2x2"})


def test_rotated_tile_label_contract() -> None:
    out = create_task("task_illustrations__image_cutout_board__rotated_tile_label").generate(
        hash64(2026053001, "rotated-tile-label", 0),
        params={
            "correct_tile_index": 4,
            "rotation_degrees": 90,
            "source_task_id": "task_illustrations__library__section_book_count",
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    assert out.scene_id == "image_cutout_board"
    assert out.query_id == "rotated_tile_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["render_map"]["correct_option_label"] == "E"
    assert trace["render_map"]["correct_tile_index"] == 4
    assert trace["render_map"]["rotation_degrees"] == 90
    assert trace["render_map"]["grid_shape"] == [3, 3]
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert trace["scene_ir"]["entities"]["source_image_shown"] is True
    assert trace["scene_ir"]["entities"]["rotated_tile"]["label"] == "E"
    assert trace["scene_ir"]["entities"]["rotated_tile"]["bbox"] == out.evidence_gt.value[0]


def test_rotated_tile_label_sampling_balances_labels_and_rotations() -> None:
    task = create_task("task_illustrations__image_cutout_board__rotated_tile_label")
    labels: Counter[str] = Counter()
    rotations: Counter[int] = Counter()
    for index in range(108):
        out = task.generate(
            hash64(2026053001, "rotated-tile-label-sampling", index),
            params={},
            max_attempts=300,
        )
        labels[str(out.answer_gt.value)] += 1
        rotations[int(out.trace_payload["render_map"]["rotation_degrees"])] += 1
    _assert_hash_balanced_counts(labels, tuple("ABCDEFGHI"))
    _assert_hash_balanced_counts(rotations, (90, 180, 270))


def test_missing_patch_label_variants_contract() -> None:
    expected_labels = ("C", "C", "C")
    for index, (mode, expected_label) in enumerate(
        zip(["plain_patch_label", "transformed_patch_label", "irregular_cutout_patch_label"], expected_labels)
    ):
        out = create_task("task_illustrations__missing_patch__missing_patch_label").generate(
            hash64(2026052503, "missing-patch", index),
            params={
                "patch_mode": mode,
                "correct_option_index": 2,
                "source_task_id": "task_illustrations__library__section_book_count",
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        assert out.scene_id == "missing_patch"
        assert out.query_id == mode
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value == expected_label
        assert out.evidence_gt.type == "bbox_set"
        assert len(out.evidence_gt.value) == 2
        assert trace["render_map"]["correct_option_label"] == expected_label
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert trace["scene_ir"]["entities"]["source_scene_id"] != "object_field"


def test_missing_patch_four_options_use_two_by_two_grid() -> None:
    out = create_task("task_illustrations__missing_patch__missing_patch_label").generate(
        hash64(2026052503, "missing-patch-grid", 0),
        params={
            "option_count": 4,
            "correct_option_index": 2,
            "source_task_id": "task_illustrations__library__section_book_count",
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    assert trace["query_spec"]["params"]["option_count"] == 4
    assert trace["render_spec"]["style"]["panel_grid"] == [2, 2]
    assert set(trace["render_map"]["option_bboxes_px"]) == {"A", "B", "C", "D"}


def test_missing_patch_source_support_excludes_mixed_and_urban_market_sources() -> None:
    support = tuple(_MISSING_PATCH_GEN_DEFAULTS["source_task_id_support"])
    assert "task_illustrations__object_field__object_type_count" not in support
    assert "task_illustrations__market__shop_attribute_count" not in support
    assert support == (
        "task_illustrations__library__section_book_count",
        "task_illustrations__park_playground__person_count",
        "task_illustrations__construction_site__worker_attribute_count",
    )


def test_odd_scene_label_contract() -> None:
    out = create_task("task_illustrations__scene_options__odd_scene_label").generate(
        hash64(2026052504, "odd-scene", 0),
        params={
            "correct_option_index": 4,
            "source_query_key": "environment_road",
            "common_count": 3,
            "odd_count": 4,
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    assert out.scene_id == "scene_options"
    assert out.query_id == "odd_scene_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["render_map"]["correct_option_label"] == "E"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    roles = [record["role"] for record in trace["render_map"]["option_sources"]]
    assert roles.count("majority") == 5
    assert roles.count("odd") == 1
    target_counts = [record["target_count"] for record in trace["render_map"]["option_sources"]]
    assert target_counts.count(3) == 5
    assert target_counts.count(4) == 1
    assert trace["query_spec"]["params"]["option_count"] == 6
    assert trace["query_spec"]["params"]["source_query_key"] == "environment_road"
    assert trace["render_spec"]["style"]["panel_grid"] == [2, 3]


def test_odd_sceneseeded_sampler_balances_option_labels() -> None:
    samples = [
        _sample_odd_scene_spec(
            instance_seed=hash64(2026052504, "odd-scene-sampling", index),
            params={},
        )
        for index in range(120)
    ]
    label_counts = Counter(sample.correct_index for sample in samples)
    _assert_hash_balanced_counts(label_counts, range(6))
    assert all(sample.common_count != sample.odd_count for sample in samples)
