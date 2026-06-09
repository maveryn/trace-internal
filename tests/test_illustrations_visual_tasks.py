"""Contract tests for shared illustration visual tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.visual.missing_patch_label import _GEN_DEFAULTS as _MISSING_PATCH_GEN_DEFAULTS
from trace.tasks.illustrations.visual.jigsaw_piece_order import _sample_spec as _sample_jigsaw_spec


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.85) + 1


def test_jigsaw_piece_order_contract() -> None:
    out = create_task("task_illustrations__image_cutout_board__jigsaw_piece_order").generate(
        hash64(2026052502, "jigsaw-piece-order", 0),
        params={"board_shape": "board_2x2", "source_task_id": "task_illustrations__library__books_in_section_count"},
        max_attempts=300,
    )
    trace = out.trace_payload
    labels = str(out.answer_gt.value).split()
    assert out.scene_id == "image_cutout_board"
    assert out.query_id == "jigsaw_piece_order"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "bbox_sequence"
    assert len(labels) == 3
    assert set(labels) == {"1", "2", "3"}
    assert len(out.annotation_gt.value) == 3
    assert trace["projected_annotation"]["bbox_sequence"] == out.annotation_gt.value
    assert trace["scene_ir"]["entities"]["source_image_shown"] is False
    assert trace["scene_ir"]["entities"]["anchored_piece"] == {"position": "top_left", "content_index": 0}
    assert trace["render_map"]["display_grid_shape"] == [2, 2]
    assert trace["render_map"]["anchored_content_index"] == 0
    assert trace["render_map"]["answer_positions"] == ["top_right", "bottom_left", "bottom_right"]
    assert sorted(trace["render_map"]["display_order_content_indices"]) == [1, 2, 3]
    assert trace["query_spec"]["params"]["board_shape"] == "board_2x2"
    assert trace["query_spec"]["params"]["option_piece_count"] == 3
    assert trace["render_spec"]["style"]["option_label_font"]["pool"] == "global_approved_font_pool"
    assert trace["render_spec"]["style"]["board_style"]["style_id"] in {"pale_cross", "warm_corner", "cool_dots"}
    assert "3 remaining piece labels" in out.prompt


def test_jigsaw_piece_order_one_by_three_contract() -> None:
    out = create_task("task_illustrations__image_cutout_board__jigsaw_piece_order").generate(
        hash64(2026052502, "jigsaw-piece-order-1x3", 0),
        params={"board_shape": "board_1x3", "source_task_id": "task_illustrations__library__books_in_section_count"},
        max_attempts=300,
    )
    trace = out.trace_payload
    labels = str(out.answer_gt.value).split()
    assert out.scene_id == "image_cutout_board"
    assert out.query_id == "jigsaw_piece_order"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "bbox_sequence"
    assert len(labels) == 2
    assert set(labels) == {"1", "2"}
    assert len(out.annotation_gt.value) == 2
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
            "source_task_id": "task_illustrations__library__books_in_section_count",
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    assert out.scene_id == "image_cutout_board"
    assert out.query_id == "rotated_tile_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert trace["render_map"]["correct_option_label"] == "E"
    assert trace["render_map"]["correct_tile_index"] == 4
    assert trace["render_map"]["rotation_degrees"] == 90
    assert trace["render_map"]["grid_shape"] == [3, 3]
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["render_spec"]["style"]["tile_label_font"]["pool"] == "global_approved_font_pool"
    assert trace["render_spec"]["style"]["grid_style"]["style_id"] in {"slate_badges", "ink_badges", "blueprint_badges"}
    assert trace["scene_ir"]["entities"]["source_image_shown"] is True
    assert trace["scene_ir"]["entities"]["rotated_tile"]["label"] == "E"
    assert trace["scene_ir"]["entities"]["rotated_tile"]["bbox"] == out.annotation_gt.value[0]


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
                "source_task_id": "task_illustrations__library__books_in_section_count",
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        assert out.scene_id == "missing_patch"
        assert out.query_id == mode
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value == expected_label
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert set(out.annotation_gt.value) == {"missing_region", "selected_option"}
        assert trace["render_map"]["correct_option_label"] == expected_label
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
        assert trace["render_map"]["annotation_bboxes_px"] == out.annotation_gt.value
        assert trace["render_spec"]["style"]["label_font"]["pool"] == "global_approved_font_pool"
        assert trace["render_spec"]["style"]["frame_style"]["style_id"] in {"slate_cards", "warm_cards", "cool_cards"}


def test_missing_patch_four_options_use_two_by_two_grid() -> None:
    out = create_task("task_illustrations__missing_patch__missing_patch_label").generate(
        hash64(2026052503, "missing-patch-grid", 0),
        params={
            "option_count": 4,
            "correct_option_index": 2,
            "source_task_id": "task_illustrations__library__books_in_section_count",
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    assert trace["query_spec"]["params"]["option_count"] == 4
    assert trace["render_spec"]["style"]["panel_grid"] == [2, 2]
    assert set(trace["render_map"]["option_bboxes_px"]) == {"A", "B", "C", "D"}


def test_missing_patch_source_support_excludes_mixed_sources() -> None:
    support = tuple(_MISSING_PATCH_GEN_DEFAULTS["source_task_id_support"])
    assert support == (
        "task_illustrations__environment__on_feature_object_count",
        "task_illustrations__library__books_in_section_count",
        "task_illustrations__park_playground__activity_person_count",
        "task_illustrations__transit_terminal__person_in_boarding_area_count",
        "task_illustrations__construction_site__worker_attribute_count",
    )
