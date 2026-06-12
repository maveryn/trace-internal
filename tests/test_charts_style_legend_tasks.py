"""Behavior tests for scientific style-legend chart tasks."""
from __future__ import annotations
from collections import Counter
import pytest
from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.style_legend.shared.style_legend_query import EXTREMUM_QUERY_IDS, GAP_QUERY_IDS, SUPPORTED_LEGEND_POSITIONS, SUPPORTED_STYLE_PALETTE_MODES, THRESHOLD_QUERY_IDS, ChartsStyleLegendPairwiseGapValueTask, ChartsStyleLegendThresholdSeriesCountTask, ChartsStyleLegendXPositionExtremumSeriesLabelTask
from trace.tasks.registry import list_default_task_ids
TASK_CASES = ((ChartsStyleLegendXPositionExtremumSeriesLabelTask, EXTREMUM_QUERY_IDS, 'string'), (ChartsStyleLegendPairwiseGapValueTask, GAP_QUERY_IDS, 'integer'), (ChartsStyleLegendThresholdSeriesCountTask, THRESHOLD_QUERY_IDS, 'integer'))

def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    x, y = [float(value) for value in point]
    assert 0 <= x <= width
    assert 0 <= y <= height

def _series_by_id(execution: dict) -> dict[str, dict]:
    return {str(series['series_id']): dict(series) for series in execution['series']}

def _expected_answer(execution: dict, query_id: str) -> int | str:
    target_x = int(execution['target_x_index'])
    series = list(execution['series'])
    if query_id == 'x_position_highest_series_label':
        winner = max(series, key=lambda item: int(item['values'][target_x]))
        return str(winner['label'])
    if query_id == 'x_position_lowest_series_label':
        winner = min(series, key=lambda item: int(item['values'][target_x]))
        return str(winner['label'])
    if query_id == 'pairwise_gap_value':
        left_id, right_id = [str(value) for value in execution['pair_series_ids']]
        by_id = _series_by_id(execution)
        return abs(int(by_id[left_id]['values'][target_x]) - int(by_id[right_id]['values'][target_x]))
    if query_id == 'above_threshold_series_count':
        threshold = int(execution['threshold_value'])
        return sum((1 for item in series if int(item['values'][target_x]) > threshold))
    if query_id == 'below_threshold_series_count':
        threshold = int(execution['threshold_value'])
        return sum((1 for item in series if int(item['values'][target_x]) < threshold))
    raise AssertionError(f'unsupported query_id: {query_id}')

@pytest.mark.parametrize(('task_cls', 'query_ids', 'answer_type'), TASK_CASES)
def test_charts_style_legend_tasks_match_contract(task_cls: type, query_ids: tuple[str, ...], answer_type: str) -> None:
    task = task_cls()

def test_charts_style_legend_prompt_examples_match_contract() -> None:
    for task_cls, _query_ids, answer_type in TASK_CASES:
        out = task_cls().generate(hash64(20260605, f'{task_cls.task_id}.prompt', len(task_cls.task_id)), params={}, max_attempts=80)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
        answer_only = extract_prompt_json_example(out.prompt_variants['answer_only'])
        assert isinstance(answer_and_annotation['annotation'], list)
        if answer_type == 'integer':
            assert isinstance(answer_and_annotation['answer'], int)
            assert isinstance(answer_only['answer'], int)
        else:
            assert isinstance(answer_and_annotation['answer'], str)
            assert isinstance(answer_only['answer'], str)
            assert len(answer_and_annotation['answer']) > 1

def test_charts_style_legend_balanced_sampling_covers_axes() -> None:
    query_counts: Counter[str] = Counter()
    palette_counts: Counter[str] = Counter()
    legend_counts: Counter[str] = Counter()
    for index in range(72):
        out = ChartsStyleLegendThresholdSeriesCountTask().generate(hash64(20260605, 'charts_style_legend_axes', index), params={}, max_attempts=80)
        execution = out.trace_payload['execution_trace']
        query_counts[str(out.query_id)] += 1
        palette_counts[str(execution['style_palette_mode'])] += 1
        legend_counts[str(execution['legend_position'])] += 1
    assert set(query_counts) == set(THRESHOLD_QUERY_IDS)
    assert set(palette_counts).issubset(set(SUPPORTED_STYLE_PALETTE_MODES))
    assert set(legend_counts) == {'right', 'top'}

def test_charts_style_legend_is_deterministic() -> None:
    params = {'query_id': 'pairwise_gap_value', 'style_palette_mode': 'grayscale', 'legend_position': 'right'}
    out_a = ChartsStyleLegendPairwiseGapValueTask().generate(2026060501, params=params, max_attempts=80)
    out_b = ChartsStyleLegendPairwiseGapValueTask().generate(2026060501, params=params, max_attempts=80)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']

def test_charts_style_legend_registry_and_config_are_wired() -> None:
    defaults = get_scene_defaults('charts', 'style_legend')
    prompt = defaults['prompt']['shared']
    assert str(prompt['bundle_id']) == 'charts_scientific_v0'
    assert str(prompt['scene_key_style_legend']) == 'style_legend_single_axis'
    assert str(prompt['task_key_style_legend']) == 'style_legend_query'
    assert ChartsStyleLegendXPositionExtremumSeriesLabelTask.task_id in list_default_task_ids()
    assert ChartsStyleLegendPairwiseGapValueTask.task_id in list_default_task_ids()
    assert ChartsStyleLegendThresholdSeriesCountTask.task_id in list_default_task_ids()
