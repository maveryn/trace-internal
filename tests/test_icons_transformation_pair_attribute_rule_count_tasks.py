"""Tests for icon pair attribute-rule counting."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.icons.pair_grid.attribute_delta_pair_count import IconsPairGridAttributeDeltaPairCountTask
from tests.helpers import read_jsonl

def _extract_prompt_json_example(prompt: str) -> dict:
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())

def test_icons_transformation_pair_attribute_rule_count_contract_matches_scene() -> None:
    task = IconsPairGridAttributeDeltaPairCountTask()
    out = task.generate(51200, params={'attribute_rule': 'color_and_size_change', 'object_count': 6, 'target_count': 3}, max_attempts=200)
    trace = out.trace_payload
    execution = trace['execution_trace']
    scene_entities = [entity for entity in trace['scene_ir']['entities'] if str(entity.get('panel')) == 'scene']
    assert out.answer_gt.type == 'integer'
    assert int(out.answer_gt.value) == 3
    assert out.annotation_gt.type == 'bbox_set'
    assert len(out.annotation_gt.value) == 3
    assert out.query_id == 'single'
    assert execution['query_id'] == 'single'
    assert trace['query_spec']['query_id'] == 'single'
    assert trace['query_spec']['params']['query_id_probabilities'] == {'single': 1.0}
    assert trace['query_spec']['params']['attribute_rule'] == 'color_and_size_change'
    assert execution['attribute_rule'] == 'color_and_size_change'
    assert execution['question_format'] == 'count_scene_cells_matching_reference_attribute_rule'
    assert execution['changed_attributes'] == ['color', 'size']
    assert int(execution['object_count']) == 6
    assert int(execution['target_count']) == 3
    assert len(scene_entities) == 6
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    matching_labels = set((str(value) for value in execution['matching_cell_labels']))
    annotation_by_label = {str(entity['label']): list(entity['cell_bbox_xyxy']) for entity in scene_entities}
    expected_annotation = [annotation_by_label[str(label)] for label in trace['witness_symbolic']['matching_cell_labels_top_left']]
    assert out.annotation_gt.value == expected_annotation
    assert trace['projected_annotation']['type'] == 'bbox_set'
    assert trace['projected_annotation']['bbox_set'] == out.annotation_gt.value
    assert trace['projected_annotation']['pixel_bbox_set'] == out.annotation_gt.value
    style = trace['render_spec']['style']
    assert int(style['text_legibility']['failure_count']) == 0
    assert {str(record['role']) for record in style['text_legibility']['records']} >= {'icon_panel_header_text', 'icon_cell_label_text'}
    assert 'cell_label_stroke_rgb' in style
    assert trace['render_map']['anchors']['reference_pair']['attribute_rule'] == 'color_and_size_change'
    for entity in scene_entities:
        label = str(entity['label'])
        is_match = label in matching_labels
        assert bool(entity['is_match']) == is_match
        if is_match:
            assert entity['attribute_rule'] == 'color_and_size_change'
            assert entity['changed_attributes'] == ['color', 'size']
        else:
            assert entity['attribute_rule'] in {'color_only_change', 'size_only_change'}
        if 'color' in entity['changed_attributes']:
            assert entity['left_tint_rgb'] != entity['right_tint_rgb']
        else:
            assert entity['left_tint_rgb'] == entity['right_tint_rgb']
        if 'size' in entity['changed_attributes']:
            assert float(entity['left_size_scale']) != float(entity['right_size_scale'])
        else:
            assert float(entity['left_size_scale']) == float(entity['right_size_scale']) == 1.0

def test_icons_transformation_pair_attribute_rule_count_deterministic_and_zero_match() -> None:
    task = IconsPairGridAttributeDeltaPairCountTask()
    out_a = task.generate(51201, params={'attribute_rule': 'color_only_change', 'target_count': 0}, max_attempts=200)
    out_b = task.generate(51201, params={'attribute_rule': 'color_only_change', 'target_count': 0}, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert int(out_a.answer_gt.value) == 0
    assert out_a.annotation_gt.value == []

def test_icons_transformation_pair_attribute_rule_count_prompt_example_matches_contract() -> None:
    task = IconsPairGridAttributeDeltaPairCountTask()
    out = task.generate(51202, params={'attribute_rule': 'size_only_change', 'target_count': 2}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
    assert answer_only == {'answer': 3}
    assert list(answer_and_annotation.keys()) == ['annotation', 'answer']
    assert answer_and_annotation['annotation'] == [[336, 104, 506, 274], [532, 104, 702, 274], [728, 104, 898, 274]]
    assert answer_and_annotation['answer'] == 3

def test_icons_transformation_pair_attribute_rule_count_balanced_sampling_defaults() -> None:
    task = IconsPairGridAttributeDeltaPairCountTask()
    rules: Counter[str] = Counter()
    target_counts: Counter[int] = Counter()
    for index in range(60):
        out = task.generate(hash64(51203, 'icons_pair_attribute_rule', index), params={}, max_attempts=200)
        execution = out.trace_payload['execution_trace']
        rules[str(execution['attribute_rule'])] += 1
        target_counts[int(execution['target_count'])] += 1
        assert 0 <= int(execution['target_count']) <= 4
        assert int(execution['object_count']) == 6
    assert set(rules.keys()) == {'color_only_change', 'size_only_change', 'color_and_size_change'}
    assert sum(rules.values()) == 60
    assert set(target_counts.keys()) == set(range(0, 5))

def test_icons_transformation_pair_attribute_rule_count_build_smoke(tmp_path: Path) -> None:
    task_id = 'task_icons__pair_grid__attribute_delta_pair_count'
    output_root = tmp_path / task_id
    config = BuildConfig(output_root=str(output_root), dataset_name=f'build_smoke_{task_id}', instance_version='v0', image_format='png', tasks=[BuildTaskConfig(task_id=task_id, count=4, params={'query_id': 'single', 'attribute_rule': 'color_only_change'})], strict_repro=False, max_attempts_per_instance=200, sampling_seed=37)
    final_path = build_dataset(config, code_hash='icons-transformation-attribute-rule-count-smoke')
    assert final_path.exists()
    train_records = read_jsonl(final_path / 'train_instances.jsonl')
    assert len(train_records) == 4
    assert all((record['domain'] == 'icons' for record in train_records))
    assert all((record['scene_id'] == 'pair_grid' for record in train_records))
    build_report = json.loads((final_path / 'build_report.json').read_text(encoding='utf-8'))
    assert int(build_report['accepted_counts_by_task'][task_id]) == 4
    validation = json.loads((final_path / 'validation_report.json').read_text(encoding='utf-8'))
    assert validation['total_errors'] == 0
