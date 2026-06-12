"""Behavior tests for the consolidated GUI filter-counting task."""
from __future__ import annotations
from collections import Counter, defaultdict
import json
from pathlib import Path
from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.counting.filter_count import CONTROL_QUERY_IDS, SUPPORTED_QUERY_IDS, TABLE_QUERY_IDS, PagesControlBoardDisabledControlsInGroupCountTask, PagesControlBoardSelectedEnabledControlsInGroupCountTask, PagesRecordTableEnabledActionForTypeCountTask, PagesRecordTableSelectedRowsWithStatusCountTask, PagesRecordTableValueThresholdInGroupCountTask
from tests.helpers import extract_prompt_json_example, read_jsonl

def test_gui_counting_filter_count_contract_matches_trace() -> None:
    task_cases = ((PagesControlBoardDisabledControlsInGroupCountTask(), ('disabled_controls_in_group_count',)), (PagesControlBoardSelectedEnabledControlsInGroupCountTask(), ('selected_enabled_controls_in_group_count',)), (PagesRecordTableEnabledActionForTypeCountTask(), ('enabled_action_for_type_count',)), (PagesRecordTableSelectedRowsWithStatusCountTask(), ('selected_rows_with_status_count',)), (PagesRecordTableValueThresholdInGroupCountTask(), ('value_threshold_in_group_count',)))
    scene_variants = ('office_document', 'creative_workspace', 'developer_ide', 'cad_workspace', 'scientific_plotter')
    style_variants = ('standard', 'compact', 'contrast', 'standard', 'compact')
    case_index = 0

def test_gui_counting_filter_count_prompt_examples_match_integer_contract() -> None:
    task = PagesControlBoardDisabledControlsInGroupCountTask()
    out = task.generate(55200, params={'query_id': 'disabled_controls_in_group_count'}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants['answer_and_annotation']) == {'annotation': [[96, 218, 221, 300], [233, 218, 358, 300], [370, 310, 495, 392]], 'answer': 3}
    assert extract_prompt_json_example(out.prompt_variants['answer_only']) == {'answer': 3}

def test_gui_counting_filter_count_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    tasks = (PagesControlBoardDisabledControlsInGroupCountTask(), PagesControlBoardSelectedEnabledControlsInGroupCountTask(), PagesRecordTableEnabledActionForTypeCountTask(), PagesRecordTableSelectedRowsWithStatusCountTask(), PagesRecordTableValueThresholdInGroupCountTask())
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[int]] = defaultdict(Counter)
    for task in tasks:
        for index in range(75):
            out = task.generate(hash64(55300, task.task_id, index), params={}, max_attempts=20)
            execution = out.trace_payload['execution_trace']
            query_id = str(execution['query_id'])
            query_ids[query_id] += 1
            scene_variants[str(execution['scene_variant'])] += 1
            style_variants[str(execution['style_variant'])] += 1
            answers_by_query_id[query_id][int(execution['answer_value'])] += 1
    assert set(query_ids.keys()) == set(SUPPORTED_QUERY_IDS)
    assert query_ids['disabled_controls_in_group_count'] >= 30
    assert query_ids['selected_enabled_controls_in_group_count'] >= 30
    assert query_ids['selected_rows_with_status_count'] >= 20
    assert query_ids['enabled_action_for_type_count'] >= 20
    assert query_ids['value_threshold_in_group_count'] >= 20
    assert set(scene_variants.keys()) == {'office_document', 'creative_workspace', 'developer_ide', 'cad_workspace', 'scientific_plotter', 'os_file_manager'}
    assert set(style_variants.keys()) == {'standard', 'compact', 'contrast', 'cool', 'warm', 'sage'}
    assert set(answers_by_query_id['disabled_controls_in_group_count'].keys()).issubset({2, 3, 4, 5, 6})
    assert set(answers_by_query_id['selected_enabled_controls_in_group_count'].keys()).issubset({3, 4, 5, 6, 7})
    assert set(answers_by_query_id['enabled_action_for_type_count'].keys()).issubset({2, 3, 4, 5, 6})
    assert set(answers_by_query_id['selected_rows_with_status_count'].keys()).issubset({2, 3, 4, 5, 6, 7})
    assert set(answers_by_query_id['value_threshold_in_group_count'].keys()).issubset({2, 3, 4, 5, 6, 7})
    assert all((len(values) >= 5 for values in answers_by_query_id.values()))

def test_gui_counting_filter_count_deterministic() -> None:
    task = PagesRecordTableValueThresholdInGroupCountTask()
    params = {'query_id': 'value_threshold_in_group_count', 'scene_variant': 'cad_workspace', 'style_variant': 'contrast', 'answer_value': 5}
    out_a = task.generate(55400, params=params, max_attempts=20)
    out_b = task.generate(55400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_gui_counting_filter_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / 'task_pages__control_board__disabled_controls_in_group_count'
    config = BuildConfig(output_root=str(output_root), dataset_name='build_smoke_task_pages__control_board__disabled_controls_in_group_count', instance_version='v0', image_format='png', tasks=[BuildTaskConfig(task_id='task_pages__control_board__disabled_controls_in_group_count', count=5, params={})], strict_repro=False, max_attempts_per_instance=20, sampling_seed=41)
    final_path = build_dataset(config, code_hash='gui-counting-filter-count-smoke')
    assert final_path.exists()
    train_records = read_jsonl(final_path / 'train_instances.jsonl')
    assert len(train_records) == 5
    assert all((record['domain'] == 'pages' for record in train_records))
    assert all((record['scene_id'] == 'counting' for record in train_records))
    build_report = json.loads((final_path / 'build_report.json').read_text(encoding='utf-8'))
    assert int(build_report['accepted_counts_by_task']['task_pages__control_board__disabled_controls_in_group_count']) == 5
    validation = json.loads((final_path / 'validation_report.json').read_text(encoding='utf-8'))
    assert validation['total_errors'] == 0
