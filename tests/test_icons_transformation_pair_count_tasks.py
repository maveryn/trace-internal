"""Behavior tests for icon transformation pair-count task."""
from __future__ import annotations
import json
from collections import Counter
from trace.core.seed import hash64
from trace.tasks.icons.shared.icon_assets import icon_transform_signature
from trace.tasks.icons.shared.icon_transform import IDENTITY_TRANSFORM_ID
from trace.tasks.icons.pair_grid.reference_transform_match_count import IconsPairGridReferenceTransformMatchCountTask

def _extract_prompt_json_example(prompt: str) -> dict:
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)

def test_icons_transformation_pair_count_contract_matches_scene() -> None:
    task = IconsPairGridReferenceTransformMatchCountTask()
    out = task.generate(14210, params={'object_count': 6, 'target_count': 3, 'transform_ids': ['rot90', 'rot180', 'flip_h', 'flip_diag_main']}, max_attempts=200)
    trace = out.trace_payload
    execution = trace['execution_trace']
    scene_entities = [entity for entity in trace['scene_ir']['entities'] if str(entity.get('panel')) == 'scene']
    assert out.answer_gt.type == 'integer'
    assert int(out.answer_gt.value) == 3
    assert out.annotation_gt.type == 'bbox_set'
    assert len(out.annotation_gt.value) == 3
    assert all((len(bbox) == 4 for bbox in out.annotation_gt.value))
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    assert trace['query_spec']['prompt_variant_active_key'] == 'answer_and_annotation'
    assert trace['scene_ir']['scene_kind'] == 'icons_reference_pair_transformation_count'
    assert trace['scene_ir']['query_id'] == 'single'
    assert trace['query_spec']['query_id'] == 'single'
    assert trace['query_spec']['params']['query_id_probabilities'] == {'single': 1.0}
    assert execution['question_format'] == 'count_scene_cells_matching_reference_transform'
    assert out.query_id == 'single'
    assert execution['query_id'] == 'single'
    assert int(execution['object_count']) == 6
    assert int(execution['target_count']) == 3
    assert int(execution['distractor_count']) == 3
    assert len(scene_entities) == 6
    reference_transform_id = str(execution['reference_transform_id'])
    reference_icon_id = str(execution['reference_icon_id'])
    matching_labels = set((str(value) for value in execution['matching_cell_labels']))
    assert len(matching_labels) == 3
    assert len(set((str(entity['label']) for entity in scene_entities))) == 6
    assert trace['witness_symbolic']['matching_cell_labels'] == execution['matching_cell_labels']
    annotation_by_label = {str(entity['label']): list(entity['cell_bbox_xyxy']) for entity in scene_entities}
    expected_annotation = [annotation_by_label[str(label)] for label in trace['witness_symbolic']['matching_cell_labels_top_left']]
    assert out.annotation_gt.value == expected_annotation
    assert trace['projected_annotation']['type'] == 'bbox_set'
    assert trace['projected_annotation']['bbox_set'] == out.annotation_gt.value
    style = trace['render_spec']['style']
    assert int(style['text_legibility']['failure_count']) == 0
    assert {str(record['role']) for record in style['text_legibility']['records']} >= {'icon_panel_header_text', 'icon_cell_label_text'}
    assert 'cell_label_stroke_rgb' in style
    sampled_palette = [tuple((int(channel) for channel in color)) for color in trace['render_spec']['style']['sampled_palette_rgb']]
    assert len(sampled_palette) == 1
    assert isinstance(trace['render_map']['anchors']['reference_pair']['left_noise_edits'], list)
    assert isinstance(trace['render_map']['anchors']['reference_pair']['right_noise_edits'], list)
    for entity in scene_entities:
        label = str(entity['label'])
        icon_id = str(entity['icon_id'])
        transform_id = str(entity['transform_id'])
        assert tuple((int(channel) for channel in entity['tint_rgb'])) in sampled_palette
        assert str(icon_id)
        assert str(transform_id)
        assert bool(entity['is_match']) == (label in matching_labels)
        if label in matching_labels:
            assert transform_id == reference_transform_id
        else:
            assert transform_id != reference_transform_id
        identity_sig = icon_transform_signature(str(icon_id), 72, IDENTITY_TRANSFORM_ID)
        active_sig = icon_transform_signature(str(icon_id), 72, transform_id)
        reference_sig = icon_transform_signature(str(icon_id), 72, reference_transform_id)
        assert active_sig != identity_sig
        if label not in matching_labels:
            assert active_sig != reference_sig
    assert str(trace['render_map']['anchors']['reference_pair']['icon_id']) == reference_icon_id

def test_icons_transformation_pair_count_supports_zero_matches() -> None:
    task = IconsPairGridReferenceTransformMatchCountTask()
    out = task.generate(14211, params={'target_count': 0, 'distractor_count': 6}, max_attempts=200)
    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.value == []

def test_icons_transformation_pair_count_prompt_example_matches_contract() -> None:
    task = IconsPairGridReferenceTransformMatchCountTask()
    out = task.generate(14212, params={'object_count': 6, 'target_count': 3}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
    assert answer_only == {'answer': 3}
    assert list(answer_and_annotation.keys()) == ['annotation', 'answer']
    assert answer_and_annotation['annotation'] == [[336, 104, 506, 274], [532, 104, 702, 274], [728, 104, 898, 274]]
    assert answer_and_annotation['answer'] == 3

def test_icons_transformation_pair_count_balanced_sampling_defaults() -> None:
    task = IconsPairGridReferenceTransformMatchCountTask()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    for index in range(42):
        out = task.generate(hash64(14213, 'icons_transformation_pair_count', index), params={}, max_attempts=200)
        execution = out.trace_payload['execution_trace']
        object_count = int(execution['object_count'])
        target_count = int(execution['target_count'])
        distractor_count = int(execution['distractor_count'])
        object_counts[object_count] += 1
        target_counts[target_count] += 1
        distractor_counts[distractor_count] += 1
        assert 0 <= target_count <= 4
        assert 1 <= distractor_count <= 9
        assert object_count == 6
    assert object_count == target_count + distractor_count
    assert set(target_counts.keys()) == set(range(0, 5))
    assert set(object_counts.keys()) == {6}
    assert min(distractor_counts.keys()) >= 1
    assert max(distractor_counts.keys()) <= 9
    assert sum(target_counts.values()) == 42
