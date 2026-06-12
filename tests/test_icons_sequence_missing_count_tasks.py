"""Behavior tests for icon sequence missing-count task."""
from __future__ import annotations
import json
from collections import Counter
from trace.core.seed import hash64
from trace.tasks.icons.sequence.missing_count import IconsSequenceMissingCountTask

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

def test_icons_sequence_missing_count_contract_matches_scene() -> None:
    task = IconsSequenceMissingCountTask()
    out = task.generate(15110, params={'sequence_length': 5, 'missing_cell_index': 2, 'target_count': 4, 'step_delta': 1}, max_attempts=200)
    trace = out.trace_payload
    execution = trace['execution_trace']
    entities = trace['scene_ir']['entities']
    cell_entities = [entity for entity in entities if str(entity['entity_kind']) == 'sequence_cell']
    icon_entities = [entity for entity in entities if str(entity['entity_kind']) == 'scene_icon']
    assert out.answer_gt.type == 'integer'
    assert int(out.answer_gt.value) == 4
    assert out.annotation_gt.type == 'bbox_set'
    assert len(out.annotation_gt.value) == 1
    assert trace['scene_ir']['scene_kind'] == 'icons_sequence_missing_count'
    assert execution['question_format'] == 'infer_missing_sequence_count'
    assert out.query_id == 'arithmetic_progression'
    assert execution['query_id'] == 'arithmetic_progression'
    assert int(execution['sequence_length']) == 5
    assert int(execution['missing_cell_index']) == 2
    assert int(execution['step_delta']) == 1
    assert execution['full_sequence_counts'] == [2, 3, 4, 5, 6]
    assert len(cell_entities) == 5
    assert len(icon_entities) == 16
    assert 112 <= int(execution['cell_box_width_px']) <= 160
    assert 96 <= int(execution['cell_box_height_px']) <= 144
    scene_colors: set[tuple[int, int, int]] = set()
    scene_icons_by_cell: dict[int, list[dict]] = {}
    for entity in icon_entities:
        scene_icons_by_cell.setdefault(int(entity['cell_index']), []).append(entity)
        assert str(entity['icon_id']) == str(execution['sequence_icon_id'])
        scene_colors.add(tuple((int(channel) for channel in entity['tint_rgb'])))
        assert int(entity['nominal_size_px']) >= 24
        assert int(entity['nominal_size_px']) <= 40
        assert int(entity['rotation_degrees']) in {0, 90, 180, 270}
        assert isinstance(entity['noise_edits'], list)
    assert len(scene_colors) == 1
    missing_boxes = out.annotation_gt.value
    assert trace['projected_annotation']['type'] == 'bbox_set'
    assert missing_boxes == trace['projected_annotation']['bbox_set']
    assert missing_boxes == trace['projected_annotation']['pixel_bbox_set']
    assert len(trace['projected_annotation']['pixel_point_set']) == 1
    drawn_text_roles = {str(record.get('role')) for record in trace['render_spec']['drawn_text']['text_legibility']['records']}
    assert 'icon_missing_mark_text' in drawn_text_roles
    missing_cell = [entity for entity in cell_entities if bool(entity['is_missing'])]
    assert len(missing_cell) == 1
    assert missing_boxes[0] == missing_cell[0]['cell_bbox_xyxy']
    assert int(missing_cell[0]['cell_index']) == 2
    assert int(missing_cell[0]['target_icon_count']) == 4
    assert int(missing_cell[0]['rendered_icon_count']) == 0
    expected_visible_counts = {0: 2, 1: 3, 3: 5, 4: 6}
    for cell in cell_entities:
        cell_index = int(cell['cell_index'])
        bbox = cell['cell_bbox_xyxy']
        cell_width = int(bbox[2]) - int(bbox[0])
        cell_height = int(bbox[3]) - int(bbox[1])
        assert abs(cell_width - int(execution['cell_box_width_px'])) <= 2
        assert abs(cell_height - int(execution['cell_box_height_px'])) <= 2
        if bool(cell['is_missing']):
            continue
        rendered_icons = scene_icons_by_cell.get(cell_index, [])
        assert len(rendered_icons) == int(cell['target_icon_count'])
        assert len(rendered_icons) == expected_visible_counts[cell_index]
        for left_index, left in enumerate(rendered_icons):
            for right in rendered_icons[left_index + 1:]:
                assert _overlap_fraction_smaller(left['bbox_xyxy'], right['bbox_xyxy']) <= 0.2 + 1e-06

def test_icons_sequence_missing_count_supports_end_missing_cell_and_zero_answer() -> None:
    task = IconsSequenceMissingCountTask()
    out = task.generate(15111, params={'sequence_length': 4, 'missing_cell_index': 3, 'target_count': 0, 'step_delta': -1}, max_attempts=200)
    execution = out.trace_payload['execution_trace']
    assert int(out.answer_gt.value) == 0
    assert len(out.annotation_gt.value) == 1
    assert int(execution['missing_cell_index']) == 3
    assert execution['full_sequence_counts'] == [3, 2, 1, 0]

def test_icons_sequence_missing_count_prompt_example_matches_contract() -> None:
    task = IconsSequenceMissingCountTask()
    out = task.generate(15112, params={'sequence_length': 6, 'missing_cell_index': 5, 'target_count': 7, 'step_delta': 1}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
    assert answer_only == {'answer': 5}
    assert list(answer_and_annotation.keys()) == ['annotation', 'answer']
    assert isinstance(answer_and_annotation['annotation'], list)
    assert len(answer_and_annotation['annotation']) == 1
    assert answer_and_annotation['answer'] == 5

def test_icons_sequence_missing_count_balanced_sampling_defaults() -> None:
    task = IconsSequenceMissingCountTask()
    target_counts: Counter[int] = Counter()
    sequence_lengths: Counter[int] = Counter()
    missing_cell_indices: Counter[int] = Counter()
    missing_by_length: dict[int, Counter[int]] = {}
    end_missing_count = 0
    for index in range(66):
        out = task.generate(hash64(15113, 'icons_sequence_missing_count', index), params={}, max_attempts=200)
        execution = out.trace_payload['execution_trace']
        target_count = int(execution['target_count'])
        sequence_length = int(execution['sequence_length'])
        missing_cell_index = int(execution['missing_cell_index'])
        target_counts[target_count] += 1
        sequence_lengths[sequence_length] += 1
        missing_cell_indices[missing_cell_index] += 1
        missing_by_length.setdefault(sequence_length, Counter())[missing_cell_index] += 1
        assert 0 <= target_count <= 10
        assert 4 <= sequence_length <= 6
        assert 0 <= missing_cell_index < sequence_length
        if missing_cell_index in {0, sequence_length - 1}:
            end_missing_count += 1
    assert set(target_counts.keys()) == set(range(0, 11))
    assert set(sequence_lengths.keys()) == {4, 5, 6}
    assert all((missing_by_length[length] for length in (4, 5, 6)))
    assert missing_cell_indices[0] <= 16
    assert max(missing_cell_indices.values()) <= 16
    assert end_missing_count > 0
