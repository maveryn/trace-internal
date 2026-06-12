"""Behavior tests for the consolidated ScreenSpot-style GUI professional target task."""
from __future__ import annotations
from collections import Counter, defaultdict
import json
from pathlib import Path
from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.professional_target_label import SUPPORTED_QUERY_IDS, PagesRelationProfessionalTargetLabelTask
from tests.helpers import extract_prompt_json_example, read_jsonl
TASK_ID = 'task_pages__workspace__toolbar_palette_control_label'
SCENE_KIND = 'gui_professional_target'

def test_gui_relation_professional_target_contract_matches_trace() -> None:
    task = PagesRelationProfessionalTargetLabelTask()
    scene_variants = ('office_document', 'creative_workspace', 'developer_ide', 'cad_workspace', 'scientific_plotter')
    style_variants = ('standard', 'compact', 'contrast', 'standard', 'compact')

def test_gui_relation_professional_target_prompt_examples_match_option_contract() -> None:
    task = PagesRelationProfessionalTargetLabelTask()
    out = task.generate(89200, params={}, max_attempts=20)
    annotation_keys = list(dict(out.annotation_gt.value).keys())
    assert extract_prompt_json_example(out.prompt_variants['answer_and_annotation']) == {'annotation': {annotation_keys[0]: [520, 130, 690, 196], annotation_keys[1]: [72, 260, 300, 344], annotation_keys[2]: [520, 212, 690, 252], annotation_keys[3]: [520, 360, 690, 444]}, 'answer': 'G'}
    assert extract_prompt_json_example(out.prompt_variants['answer_only']) == {'answer': 'G'}

def test_gui_relation_professional_target_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationProfessionalTargetLabelTask()
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    context_counts: Counter[int] = Counter()
    active_variants: set[str] | None = None
    for index in range(150):
        out = task.generate(hash64(89300, TASK_ID, index), params={}, max_attempts=20)
        execution = out.trace_payload['execution_trace']
        query_id = str(execution['query_id'])
        query_ids[query_id] += 1
        scene_variants[str(execution['scene_variant'])] += 1
        style_variants[str(execution['style_variant'])] += 1
        answers_by_query_id[query_id][str(execution['target_label'])] += 1
        context_counts[int(execution['context_count'])] += 1
        if active_variants is None:
            active_variants = {str(key) for key, value in dict(execution['query_id_probabilities']).items() if float(value) > 0.0}
    assert active_variants
    assert set(query_ids.keys()) == set(active_variants)
    assert set(active_variants) == set(SUPPORTED_QUERY_IDS)
    assert all((count >= 20 for count in query_ids.values()))
    assert set(scene_variants.keys()) == {'office_document', 'creative_workspace', 'developer_ide', 'cad_workspace', 'scientific_plotter', 'os_file_manager'}
    assert set(style_variants.keys()) == {'standard', 'compact', 'contrast', 'cool', 'warm', 'sage'}
    assert set(context_counts.keys()) == {3, 4, 5}
    for query_id in active_variants:
        assert len(answers_by_query_id[query_id]) >= 15

def test_gui_relation_professional_target_deterministic() -> None:
    task = PagesRelationProfessionalTargetLabelTask()
    params = {'query_id': SUPPORTED_QUERY_IDS[-1], 'scene_variant': 'cad_workspace', 'style_variant': 'contrast', 'target_label': 'M'}
    out_a = task.generate(89400, params=params, max_attempts=20)
    out_b = task.generate(89400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_gui_relation_professional_target_build_smoke(tmp_path: Path) -> None:
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
