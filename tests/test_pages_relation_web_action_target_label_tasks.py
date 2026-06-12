"""Behavior tests for the web-style GUI action target task."""
from __future__ import annotations
from collections import Counter, defaultdict
import json
from pathlib import Path
from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.web_action_target_label import SUPPORTED_QUERY_IDS, PagesRelationWebActionTargetLabelTask
from tests.helpers import extract_prompt_json_example, read_jsonl
TASK_ID = 'task_pages__web_action__click_target_label'
SCENE_KIND = 'gui_web_action_target'

def test_gui_relation_web_action_target_contract_matches_trace() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    scene_variants = ('shop_catalog', 'travel_booking', 'support_center')
    style_variants = ('standard', 'compact', 'contrast')

def test_gui_relation_web_action_target_prompt_examples_match_option_contract() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    out = task.generate(99200, params={}, max_attempts=20)
    expected_roles_by_query = {'click_target_label': ('action_key_guide', 'item_card', 'target_button'), 'type_field_label': ('field_key_guide', 'form_section', 'target_input'), 'select_option_label': ('option_key_guide', 'option_group', 'target_option')}
    guide_role, context_role, target_role = expected_roles_by_query[str(out.query_id)]
    assert extract_prompt_json_example(out.prompt_variants['answer_and_annotation']) == {'annotation': {'instruction_banner': [80, 150, 1200, 210], guide_role: [210, 222, 430, 278], context_role: [92, 310, 590, 430], target_role: [410, 378, 560, 418]}, 'answer': 'G'}
    assert extract_prompt_json_example(out.prompt_variants['answer_only']) == {'answer': 'G'}

def test_gui_relation_web_action_target_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for index in range(180):
        out = task.generate(hash64(99300, TASK_ID, index), params={}, max_attempts=20)
        execution = out.trace_payload['execution_trace']
        query_id = str(execution['query_id'])
        query_ids[query_id] += 1
        scene_variants[str(execution['scene_variant'])] += 1
        style_variants[str(execution['style_variant'])] += 1
        answers_by_query_id[query_id][str(execution['target_label'])] += 1
    assert set(query_ids.keys()) == set(SUPPORTED_QUERY_IDS)
    assert max(query_ids.values()) - min(query_ids.values()) <= 12
    assert set(scene_variants.keys()) == {'shop_catalog', 'travel_booking', 'support_center', 'learning_portal', 'finance_portal', 'content_cms'}
    assert set(style_variants.keys()) == {'standard', 'compact', 'contrast', 'cool', 'warm', 'sage'}
    for query_id in SUPPORTED_QUERY_IDS:
        assert len(answers_by_query_id[query_id]) >= 20

def test_gui_relation_web_action_target_deterministic() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    params = {'query_id': 'select_option_label', 'scene_variant': 'finance_portal', 'style_variant': 'contrast', 'target_label': 'M'}
    out_a = task.generate(99400, params=params, max_attempts=20)
    out_b = task.generate(99400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_gui_relation_web_action_target_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / TASK_ID
    config = BuildConfig(output_root=str(output_root), dataset_name=f'build_smoke_{TASK_ID}', instance_version='v0', image_format='png', tasks=[BuildTaskConfig(task_id=TASK_ID, count=4, params={})], strict_repro=False, max_attempts_per_instance=20, sampling_seed=41)
    final_path = build_dataset(config, code_hash=f'{TASK_ID}-smoke')
    assert final_path.exists()
    train_records = read_jsonl(final_path / 'train_instances.jsonl')
    assert len(train_records) == 4
    assert all((record['domain'] == 'pages' for record in train_records))
    assert all((record['scene_id'] == 'relation' for record in train_records))
    build_report = json.loads((final_path / 'build_report.json').read_text(encoding='utf-8'))
    assert int(build_report['accepted_counts_by_task'][TASK_ID]) == 4
    validation = json.loads((final_path / 'validation_report.json').read_text(encoding='utf-8'))
    assert validation['total_errors'] == 0
