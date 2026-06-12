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
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)

def _center_in_strip(entity: dict, anchor_a: dict, anchor_b: dict, strip_axis: str, margin_px: int) -> bool:
    cx, cy = [float(value) for value in entity['center_xy']]
    ax, ay = [float(value) for value in anchor_a['center_xy']]
    bx, by = [float(value) for value in anchor_b['center_xy']]
    if str(strip_axis) == 'vertical':
        left, right = sorted((float(ax), float(bx)))
        return float(left + margin_px) <= float(cx) <= float(right - margin_px)
    if str(strip_axis) == 'horizontal':
        top, bottom = sorted((float(ay), float(by)))
        return float(top + margin_px) <= float(cy) <= float(bottom - margin_px)
    raise ValueError(f'unsupported strip_axis: {strip_axis}')

def test_icons_relation_between_two_anchors_count_contract_matches_scene() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    out = task.generate(14910, params={'query_id': 'inside_vertical_strip', 'target_count': 2, 'distractor_count': 4}, max_attempts=200)
    trace = out.trace_payload
    execution = trace['execution_trace']
    entities = trace['scene_ir']['entities']
    anchors = [entity for entity in entities if str(entity['entity_kind']) == 'anchor_icon']
    scene_entities = [entity for entity in entities if str(entity['entity_kind']) == 'scene_icon']
    assert out.answer_gt.type == 'integer'
    assert int(out.answer_gt.value) == 2
    assert out.annotation_gt.type == 'bbox_set'
    assert len(out.annotation_gt.value) == 2
    assert out.annotation_gt.value == sorted(out.annotation_gt.value, key=lambda box: (box[1], box[0], box[3], box[2]))
    assert trace['projected_annotation']['type'] == 'bbox_set'
    assert trace['projected_annotation']['bbox_set'] == out.annotation_gt.value
    assert trace['projected_annotation']['pixel_bbox_set'] == out.annotation_gt.value
    assert len(trace['projected_annotation']['pixel_point_set']) == len(out.annotation_gt.value)
    drawn_text_roles = {str(record.get('role')) for record in trace['render_spec']['drawn_text']['text_legibility']['records']}
    assert 'icon_anchor_label_text' in drawn_text_roles
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    assert trace['query_spec']['prompt_variant_active_key'] == 'answer_and_annotation'
    assert trace['scene_ir']['scene_kind'] == 'icons_two_anchor_strip_relation'
    assert execution['question_format'] == 'count_scene_icon_centers_in_strip_between_two_anchors'
    assert out.query_id == 'inside_vertical_strip'
    assert execution['query_id'] == 'inside_vertical_strip'
    assert execution['internal_query_id'] == 'inside_vertical_strip'
    assert execution['strip_axis'] == 'vertical'
    assert int(execution['object_count']) == 6
    assert int(execution['target_count']) == 2
    assert int(execution['distractor_count']) == 4
    assert len(anchors) == 2
    assert len(scene_entities) == 6
    assert float(trace['render_spec']['style']['scene_max_overlap_fraction']) == 0.08
    assert int(trace['render_spec']['style']['strip_boundary_margin_px']) == 14
    anchor_a = next((entity for entity in anchors if str(entity['role']) == 'anchor_a'))
    anchor_b = next((entity for entity in anchors if str(entity['role']) == 'anchor_b'))
    assert str(anchor_a['icon_id']) == str(anchor_b['icon_id'])
    assert list(anchor_a['tint_rgb']) == list(anchor_b['tint_rgb'])
    assert int(anchor_a['rotation_degrees']) == int(anchor_b['rotation_degrees'])
    assert abs(float(anchor_a['center_xy'][1]) - float(anchor_b['center_xy'][1])) <= 1e-06
    matching_indices = {int(value) for value in execution['matching_scene_indices']}
    anchor_icon_id = str(anchor_a['icon_id'])
    anchor_highlights = [list(anchor_a['highlight_bbox_xyxy']), list(anchor_b['highlight_bbox_xyxy'])]
    for index, entity in enumerate(scene_entities):
        assert str(entity['icon_id']) != anchor_icon_id
        is_match = bool(entity['is_match'])
        assert is_match == (int(index) in matching_indices)
        in_strip = _center_in_strip(entity, anchor_a, anchor_b, 'vertical', 14)
        assert bool(entity['center_in_strip']) == bool(in_strip)
        assert bool(in_strip) == bool(is_match)
        for highlight in anchor_highlights:
            assert _overlap_fraction_smaller(list(entity['bbox_xyxy']), highlight) <= 0.08 + 1e-06
        for other in scene_entities[index + 1:]:
            assert _overlap_fraction_smaller(list(entity['bbox_xyxy']), list(other['bbox_xyxy'])) <= 0.08 + 1e-06

def test_icons_relation_between_two_anchors_count_supports_zero_matches() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    out = task.generate(14911, params={'query_id': 'inside_horizontal_strip', 'target_count': 0, 'distractor_count': 4}, max_attempts=200)
    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.value == []

def test_icons_relation_between_two_anchors_count_prompt_example_matches_contract() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    out = task.generate(14912, params={'target_count': 2, 'distractor_count': 4}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
    assert answer_only == {'answer': 2}
    assert list(answer_and_annotation.keys()) == ['annotation', 'answer']
    assert isinstance(answer_and_annotation['annotation'], list)
    assert len(answer_and_annotation['annotation']) == 2
    assert answer_and_annotation['answer'] == 2

def test_icons_relation_between_two_anchors_count_balanced_sampling_defaults() -> None:
    task = IconsRelationBetweenTwoAnchorsCountTask()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    strip_axis_counts: Counter[str] = Counter()
    axis_target_counts: dict[str, Counter[int]] = {'vertical': Counter(), 'horizontal': Counter()}
    for index in range(60):
        out = task.generate(hash64(14913, 'icons_relation_between_two_anchors_count', index), params={}, max_attempts=200)
        execution = out.trace_payload['execution_trace']
        target_count = int(execution['target_count'])
        distractor_count = int(execution['distractor_count'])
        target_counts[target_count] += 1
        distractor_counts[distractor_count] += 1
        assert str(execution['query_id']) in {'inside_vertical_strip', 'inside_horizontal_strip'}
        strip_axis = str(execution['strip_axis'])
        strip_axis_counts[strip_axis] += 1
        axis_target_counts[strip_axis][target_count] += 1
        assert 0 <= target_count <= 5
        assert 1 <= distractor_count <= 10
        assert int(execution['object_count']) == int(target_count) + int(distractor_count)
    assert set(target_counts.keys()) == set(range(0, 6))
    assert set(strip_axis_counts.keys()) == {'vertical', 'horizontal'}
    assert set(axis_target_counts['vertical'].keys()) == set(range(0, 6))
    assert set(axis_target_counts['horizontal'].keys()) == set(range(0, 6))
    assert sum(target_counts.values()) == 60
    assert sum(strip_axis_counts.values()) == 60
