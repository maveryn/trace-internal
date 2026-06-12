"""Behavior tests for the GUI command-intent relation task."""
from __future__ import annotations
from collections import Counter, defaultdict
import json
from pathlib import Path
from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.command_intent_target_label import SUPPORTED_QUERY_IDS, PagesRelationCommandIntentTargetLabelTask
from tests.helpers import extract_prompt_json_example, read_jsonl

def test_gui_relation_command_intent_target_label_contract_matches_trace() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    scene_variants = ('office_document', 'creative_workspace', 'developer_ide', 'cad_workspace', 'scientific_plotter')
    style_variants = ('standard', 'compact', 'contrast', 'standard', 'compact')

def test_gui_relation_command_intent_target_label_prompt_examples_match_option_contract() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    out = task.generate(79200, params={'query_id': 'create_insert_command_label'}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants['answer_and_annotation']) == {'annotation': {'action_cue_guide': [290, 150, 480, 190], 'object_row': [70, 240, 270, 310], 'action_code_header': [290, 200, 480, 235], 'target_command_cell': [290, 320, 480, 390]}, 'answer': 'G'}
    assert extract_prompt_json_example(out.prompt_variants['answer_only']) == {'answer': 'G'}

def test_gui_relation_command_intent_target_label_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    query_ids: Counter[str] = Counter()
    intent_categories: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for index in range(260):
        out = task.generate(hash64(79300, 'gui_relation_command_intent_target_label', index), params={}, max_attempts=20)
        execution = out.trace_payload['execution_trace']
        query_id = str(execution['query_id'])
        query_ids[query_id] += 1
        intent_categories[str(execution['intent_category'])] += 1
        scene_variants[str(execution['scene_variant'])] += 1
        style_variants[str(execution['style_variant'])] += 1
        answers_by_query_id[query_id][str(execution['target_label'])] += 1
    assert set(query_ids.keys()) == set(SUPPORTED_QUERY_IDS)
    assert all((abs(count - 130) <= 10 for count in query_ids.values()))
    assert set(intent_categories.keys()) == {'create_insert', 'select_choose', 'view_toggle', 'edit_transform', 'format_style'}
    assert all((count >= 40 for count in intent_categories.values()))
    assert max(intent_categories.values()) - min(intent_categories.values()) <= 32
    assert set(scene_variants.keys()) == {'office_document', 'creative_workspace', 'developer_ide', 'cad_workspace', 'scientific_plotter', 'os_file_manager'}
    assert set(style_variants.keys()) == {'standard', 'compact', 'contrast', 'cool', 'warm', 'sage'}
    for query_id in SUPPORTED_QUERY_IDS:
        assert len(answers_by_query_id[query_id]) >= 20

def test_gui_relation_command_intent_target_label_deterministic() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    params = {'query_id': 'edit_transform_command_label', 'scene_variant': 'cad_workspace', 'style_variant': 'contrast', 'target_label': 'M'}
    out_a = task.generate(79400, params=params, max_attempts=20)
    out_b = task.generate(79400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_gui_relation_command_intent_target_label_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / 'task_pages__command_matrix__command_intent_target_label'
    config = BuildConfig(output_root=str(output_root), dataset_name='build_smoke_task_pages__command_matrix__command_intent_target_label', instance_version='v0', image_format='png', tasks=[BuildTaskConfig(task_id='task_pages__command_matrix__command_intent_target_label', count=4, params={})], strict_repro=False, max_attempts_per_instance=20, sampling_seed=41)
    final_path = build_dataset(config, code_hash='gui-relation-command-intent-target-label-smoke')
    assert final_path.exists()
    train_records = read_jsonl(final_path / 'train_instances.jsonl')
    assert len(train_records) == 4
    assert all((record['domain'] == 'pages' for record in train_records))
    assert all((record['scene_id'] == 'relation' for record in train_records))
    build_report = json.loads((final_path / 'build_report.json').read_text(encoding='utf-8'))
    assert int(build_report['accepted_counts_by_task']['task_pages__command_matrix__command_intent_target_label']) == 4
    validation = json.loads((final_path / 'validation_report.json').read_text(encoding='utf-8'))
    assert validation['total_errors'] == 0
