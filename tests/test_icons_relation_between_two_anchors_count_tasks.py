"""Behavior tests for the two-anchor strip icon relation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.relation.between_two_anchors_count import IconsRelationBetweenTwoAnchorsCountTask


def _overlap_fraction_smaller(left: list[int], right: list[int]) -> float:
    ix0 = max(int(left[0]), int(right[0]))
    iy0 = max(int(left[1]), int(right[1]))
    ix1 = min(int(left[2]), int(right[2]))
    iy1 = min(int(left[3]), int(right[3]))
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    left_area = max(1, int(left[2]) - int(left[0])) * max(1, int(left[3]) - int(left[1]))
    right_area = max(1, int(right[2]) - int(right[0])) * max(1, int(right[3]) - int(right[1]))
    return float(inter) / float(min(left_area, right_area))


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _center_in_strip(entity: dict, anchor_a: dict, anchor_b: dict, task_variant: str, margin_px: int) -> bool:
    cx, cy = [float(value) for value in entity["center_xy"]]
    ax, ay = [float(value) for value in anchor_a["center_xy"]]
    bx, by = [float(value) for value in anchor_b["center_xy"]]
    if str(task_variant) == "inside_vertical_strip":
        left, right = sorted((float(ax), float(bx)))
        return float(left + margin_px) <= float(cx) <= float(right - margin_px)
    if str(task_variant) == "inside_horizontal_strip":
        top, bottom = sorted((float(ay), float(by)))
        return float(top + margin_px) <= float(cy) <= float(bottom - margin_px)
    raise ValueError(f"unsupported task_variant: {task_variant}")


def test_icons_relation_between_two_anchors_count_contract_matches_scene() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    out = task.generate(
        14910,
        params={"task_variant": "inside_vertical_strip", "target_count": 2, "distractor_count": 4},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    entities = trace["scene_ir"]["entities"]
    anchors = [entity for entity in entities if str(entity["entity_kind"]) == "anchor_icon"]
    scene_entities = [entity for entity in entities if str(entity["entity_kind"]) == "scene_icon"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 2
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 2
    assert out.evidence_gt.value == sorted(out.evidence_gt.value, key=lambda box: (box[1], box[0], box[3], box[2]))
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert trace["scene_ir"]["scene_kind"] == "icons_two_anchor_strip_relation"
    assert execution["question_format"] == "count_scene_icon_centers_in_strip_between_two_anchors"
    assert execution["task_variant"] == "inside_vertical_strip"
    assert int(execution["object_count"]) == 6
    assert int(execution["target_count"]) == 2
    assert int(execution["distractor_count"]) == 4
    assert len(anchors) == 2
    assert len(scene_entities) == 6
    assert float(trace["render_spec"]["style"]["scene_max_overlap_fraction"]) == 0.08
    assert int(trace["render_spec"]["style"]["strip_boundary_margin_px"]) == 14

    anchor_a = next(entity for entity in anchors if str(entity["role"]) == "anchor_a")
    anchor_b = next(entity for entity in anchors if str(entity["role"]) == "anchor_b")
    assert str(anchor_a["icon_id"]) == str(anchor_b["icon_id"])
    assert list(anchor_a["tint_rgb"]) == list(anchor_b["tint_rgb"])
    assert int(anchor_a["rotation_degrees"]) == int(anchor_b["rotation_degrees"])
    assert abs(float(anchor_a["center_xy"][1]) - float(anchor_b["center_xy"][1])) <= 1e-6
    matching_indices = {int(value) for value in execution["matching_scene_indices"]}
    anchor_icon_id = str(anchor_a["icon_id"])
    anchor_highlights = [list(anchor_a["highlight_bbox_xyxy"]), list(anchor_b["highlight_bbox_xyxy"])]
    for index, entity in enumerate(scene_entities):
        assert str(entity["icon_id"]) != anchor_icon_id
        is_match = bool(entity["is_match"])
        assert is_match == (int(index) in matching_indices)
        in_strip = _center_in_strip(entity, anchor_a, anchor_b, "inside_vertical_strip", 14)
        assert bool(entity["center_in_strip"]) == bool(in_strip)
        assert bool(in_strip) == bool(is_match)
        for highlight in anchor_highlights:
            assert _overlap_fraction_smaller(list(entity["bbox_xyxy"]), highlight) <= 0.08 + 1e-6
        for other in scene_entities[index + 1 :]:
            assert _overlap_fraction_smaller(list(entity["bbox_xyxy"]), list(other["bbox_xyxy"])) <= 0.08 + 1e-6


def test_icons_relation_between_two_anchors_count_supports_zero_matches() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    out = task.generate(
        14911,
        params={"task_variant": "inside_horizontal_strip", "target_count": 0, "distractor_count": 4},
        max_attempts=200,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []


def test_icons_relation_between_two_anchors_count_prompt_example_matches_contract() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    out = task.generate(14912, params={"target_count": 2, "distractor_count": 4}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 2
    assert answer_and_evidence["answer"] == 2


def test_icons_relation_between_two_anchors_count_balanced_sampling_defaults() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    variant_counts: Counter[str] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(14913, "icons_relation_between_two_anchors_count", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        target_count = int(execution["target_count"])
        distractor_count = int(execution["distractor_count"])
        target_counts[target_count] += 1
        distractor_counts[distractor_count] += 1
        variant_counts[str(execution["task_variant"])] += 1
        assert 0 <= target_count <= 5
        assert 1 <= distractor_count <= 10
        assert int(execution["object_count"]) == int(target_count) + int(distractor_count)
    assert set(target_counts.keys()) == set(range(0, 6))
    assert set(variant_counts.keys()) == {"inside_vertical_strip", "inside_horizontal_strip"}
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert max(variant_counts.values()) - min(variant_counts.values()) <= 1
