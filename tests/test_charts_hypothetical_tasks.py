"""Behavior tests for chart hypothetical/counterfactual tasks."""
from __future__ import annotations
import json
import pytest
from trace.tasks.charts.single_series.shared.counterfactual_value import ChartsHypotheticalCounterfactualValueTask, SUPPORTED_QUERY_IDS

def _extract_prompt_json_example(prompt: str) -> dict:
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)

def _mean(values: list[int]) -> int:
    assert sum(values) % len(values) == 0
    return int(sum(values) // len(values))

def _expected_answer(trace: dict) -> int:
    values_by_label = {str(label): int(value) for label, value in trace['values_by_label'].items()}
    variant = str(trace['query_id'])
    if variant == 'remaining_mean_after_removal':
        retained = [values_by_label[str(label)] for label in trace['retained_labels']]
        return _mean(retained)
    if variant == 'target_share_after_removal':
        retained_total = sum((values_by_label[str(label)] for label in trace['retained_labels']))
        target_value = values_by_label[str(trace['target_label'])]
        assert target_value * 100 % retained_total == 0
        return int(target_value * 100 // retained_total)
    if variant == 'baseline_from_aggregate_percent_change':
        aggregate_sum = sum((values_by_label[str(label)] for label in trace['aggregate_labels']))
        scale = 100 + int(trace['percent_value'])
        assert aggregate_sum * 100 % scale == 0
        return int(aggregate_sum * 100 // scale)
    raise AssertionError(f'unsupported variant: {variant}')

@pytest.mark.parametrize(('query_id', 'scene_variant'), [('remaining_mean_after_removal', 'bar'), ('target_share_after_removal', 'dot_plot'), ('baseline_from_aggregate_percent_change', 'lollipop')])
def test_chart_hypothetical_variants_match_contract(query_id: str, scene_variant: str) -> None:
    task = ChartsHypotheticalCounterfactualValueTask()
    out = task.generate(12100 + SUPPORTED_QUERY_IDS.index(query_id), params={'query_id': query_id, 'scene_variant': scene_variant}, max_attempts=10)
    trace = out.trace_payload
    execution = trace['execution_trace']
    render = trace['render_spec']
    assert out.query_id == query_id
    assert out.answer_gt.type == 'integer'
    assert out.annotation_gt.type == 'point_set'
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    assert str(execution['scene_variant']) == str(scene_variant)
    assert str(render['scene_variant']) == str(scene_variant)
    assert out.image.size == (int(render['canvas_width']), int(render['canvas_height']))
    labels = [str(label) for label in execution['labels']]
    annotation_labels = [str(label) for label in execution['annotation_labels']]
    annotation_points = [list(point) for point in out.annotation_gt.value]
    assert annotation_labels == sorted(annotation_labels)
    assert set(annotation_labels).issubset(set(labels))
    assert trace['projected_annotation']['point_set'] == annotation_points
    assert 'label_set' not in trace['projected_annotation']
    assert len(annotation_points) == len(annotation_labels)
    assert len(trace['projected_annotation']['bbox_set']) == len(annotation_labels)
    for x_coord, y_coord in annotation_points:
        assert 0 <= float(x_coord) <= int(render['canvas_width'])
        assert 0 <= float(y_coord) <= int(render['canvas_height'])
    assert int(out.answer_gt.value) == int(execution['answer_value'])
    assert int(out.answer_gt.value) == _expected_answer(execution)
    assert str(trace['query_spec']['query_id']) == str(query_id)
    assert str(trace['query_spec']['params']['scene_variant']) == str(scene_variant)
    assert len(trace['scene_ir']['entities']) == int(execution['mark_count'])
    assert set((str(entity['attrs']['label']) for entity in trace['scene_ir']['entities'])) == set(labels)
    assert set(trace['render_map']['label_centers_px'].keys()) == set(labels)

def test_chart_hypothetical_balances_variants_and_scenes() -> None:
    task = ChartsHypotheticalCounterfactualValueTask()
    variants = []
    scenes = []
    for index in range(30):
        out = task.generate(12200 + index, params={}, max_attempts=10)
        variants.append(str(out.query_id))
        scenes.append(str(out.trace_payload['execution_trace']['scene_variant']))
    assert {variant: variants.count(variant) for variant in set(variants)} == {'remaining_mean_after_removal': 10, 'target_share_after_removal': 10, 'baseline_from_aggregate_percent_change': 10}
    assert {scene: scenes.count(scene) for scene in set(scenes)} == {'bar': 10, 'dot_plot': 10, 'lollipop': 10}

def test_chart_hypothetical_prompt_examples_match_selected_variant() -> None:
    task = ChartsHypotheticalCounterfactualValueTask()
    expected = {'remaining_mean_after_removal': {'annotation': [[180, 360], [320, 240], [460, 300]], 'answer': 18}, 'target_share_after_removal': {'annotation': [[180, 260], [320, 340], [460, 220]], 'answer': 25}, 'baseline_from_aggregate_percent_change': {'annotation': [[220, 340], [360, 280], [500, 220]], 'answer': 40}}
    for index, query_id in enumerate(expected, start=12300):
        out = task.generate(index, params={'query_id': query_id}, max_attempts=10)
        answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
        answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
        assert answer_and_annotation == expected[query_id]
        assert answer_only == {'answer': expected[query_id]['answer']}

def test_chart_hypothetical_rejects_non_initial_scene_variants() -> None:
    task = ChartsHypotheticalCounterfactualValueTask()
    for scene_variant in ('horizontal_bar', 'line', 'area', 'scatter', 'pie', 'donut', 'radar'):
        with pytest.raises(ValueError):
            task.generate(12400, params={'query_id': 'remaining_mean_after_removal', 'scene_variant': scene_variant}, max_attempts=10)

def test_chart_hypothetical_task_is_deterministic() -> None:
    task = ChartsHypotheticalCounterfactualValueTask()
    params = {'query_id': 'target_share_after_removal', 'scene_variant': 'lollipop'}
    out_a = task.generate(12500, params=params, max_attempts=10)
    out_b = task.generate(12500, params=params, max_attempts=10)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.trace_payload['query_spec']['prompt_variant'] == out_b.trace_payload['query_spec']['prompt_variant']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
