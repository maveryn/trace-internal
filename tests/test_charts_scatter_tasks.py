"""Behavior tests for scatter cluster chart tasks."""
from __future__ import annotations
from collections import Counter
import pytest
from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.tasks import create_task
from trace.tasks.charts.scatter_cluster.shared.cluster_query import SUPPORTED_SCENE_VARIANTS, SUPPORTED_QUERY_IDS, ChartsScatterClusterQueryTask
_OPTION_LABELS = {'A', 'B', 'C', 'D', 'E', 'F'}
_AREA_RANK_QUERY_IDS = {'largest_cluster_area_label', 'second_largest_cluster_area_label', 'smallest_cluster_area_label'}

def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height

def _expected_answer(execution: dict) -> str:
    variant = str(execution['query_id'])
    labels = [str(label) for label in execution['cluster_labels']]
    if variant == 'cluster_trend_direction_label':
        slopes = {str(label): float(value) for label, value in execution['cluster_slopes'].items()}
        if str(execution['trend_direction']) == 'upward':
            return max(labels, key=lambda label: (slopes[label], label))
        return min(labels, key=lambda label: (slopes[label], label))
    if variant == 'cluster_separation_extremum_label':
        distances = {str(label): float(value) for label, value in execution['centroid_distances_from_reference'].items()}
        candidate_labels = sorted(distances)
        if str(execution['separation_extremum']) == 'closest':
            return min(candidate_labels, key=lambda label: (distances[label], label))
        return max(candidate_labels, key=lambda label: (distances[label], label))
    if variant == 'cluster_spread_extremum_label':
        metrics = {str(label): float(value) for label, value in execution['cluster_spread_metrics'].items()}
        if str(execution['spread_extremum']) == 'largest':
            return max(labels, key=lambda label: (metrics[label], label))
        return min(labels, key=lambda label: (metrics[label], label))
    if variant in _AREA_RANK_QUERY_IDS:
        metrics = {str(label): float(value) for label, value in execution['cluster_area_metrics'].items()}
        largest_to_smallest = sorted(labels, key=lambda label: (-metrics[label], label))
        if variant == 'second_largest_cluster_area_label':
            return largest_to_smallest[1]
        if variant == 'smallest_cluster_area_label':
            return largest_to_smallest[-1]
        return largest_to_smallest[0]
    if variant == 'centroid_option_selection_label':
        distances = {str(label): float(value) for label, value in execution['option_distances_to_centroid'].items()}
        return min(sorted(distances), key=lambda label: (distances[label], label))
    raise AssertionError(f'unsupported variant: {variant}')

@pytest.mark.parametrize('query_id', SUPPORTED_QUERY_IDS)
def test_chart_scatter_cluster_variants_match_contract(query_id: str) -> None:
    task = ChartsScatterClusterQueryTask()
    out = task.generate(91300 + SUPPORTED_QUERY_IDS.index(query_id), params={'query_id': query_id}, max_attempts=80)
    trace = out.trace_payload
    execution = trace['execution_trace']
    render = trace['render_spec']
    render_map = trace['render_map']
    assert out.query_id == query_id
    if query_id == 'centroid_option_selection_label':
        assert out.answer_gt.type == 'option_letter'
    else:
        assert out.answer_gt.type == 'string'
    assert out.annotation_gt.type == 'keyed_bbox_map'
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    assert str(execution['question_format']) == 'scatter_cluster_query'
    assert str(execution['scene_variant']) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render['canvas_width']), int(render['canvas_height']))
    assert 4 <= int(execution['cluster_count']) <= 7
    assert 8 <= int(execution['points_per_cluster']) <= 12
    assert int(execution['total_point_count']) == int(execution['cluster_count']) * int(execution['points_per_cluster'])
    assert len(execution['cluster_labels']) == int(execution['cluster_count'])
    assert len(set(execution['cluster_labels'])) == int(execution['cluster_count'])
    assert set(execution['cluster_labels']).isdisjoint({'A', 'B', 'C', 'D', 'E', 'F'})
    if query_id in _AREA_RANK_QUERY_IDS:
        assert str(execution['scene_variant']) == 'area_envelope_scatter'
        assert set(render_map['cluster_envelope_bboxes_px']) == set(execution['cluster_labels'])
    expected_answer = _expected_answer(execution)
    assert str(out.answer_gt.value) == expected_answer
    assert str(execution['answer']) == expected_answer
    assert trace['projected_annotation']['type'] == 'keyed_bbox_map'
    assert trace['projected_annotation']['keyed_bbox_map'] == out.annotation_gt.value
    assert trace['projected_annotation']['pixel_keyed_bbox_map'] == out.annotation_gt.value
    assert str(render['font_asset_version'])
    assert str(render['chart_font_family'])
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_inside_canvas([float(value) for value in bbox], width=int(render['canvas_width']), height=int(render['canvas_height']))
    annotation_clusters = [str(label) for label in trace['projected_annotation']['cluster_labels']]
    if query_id == 'cluster_separation_extremum_label':
        assert len(annotation_clusters) == 2
        assert len(out.annotation_gt.value) == 2
        assert annotation_clusters[0] == execution['reference_cluster_label']
        assert annotation_clusters[1] == expected_answer
        assert out.annotation_gt.value == {'reference_cluster': render_map['cluster_bboxes_px'][str(execution['reference_cluster_label'])], 'answer_cluster': render_map['cluster_bboxes_px'][expected_answer]}
    elif query_id == 'centroid_option_selection_label':
        option_labels = {str(label) for label in execution['option_labels']}
        assert int(execution['option_count']) in {4, 6}
        assert len(option_labels) == int(execution['option_count'])
        assert option_labels.issubset(_OPTION_LABELS)
        assert expected_answer in option_labels
        assert set(render_map['option_bboxes_px']) == option_labels
        assert set(render_map['option_centers_px']) == option_labels
        assert annotation_clusters == [str(execution['target_cluster_label'])]
        assert out.annotation_gt.value == {'target_cluster': render_map['cluster_bboxes_px'][str(execution['target_cluster_label'])], 'selected_option_marker': render_map['option_bboxes_px'][expected_answer]}
        distances = {str(label): float(value) for label, value in execution['option_distances_to_centroid'].items()}
        answer_distance = distances[expected_answer]
        assert all((answer_distance + float(execution['minimum_distance_margin']) < distance for label, distance in distances.items() if str(label) != expected_answer))
    elif query_id in _AREA_RANK_QUERY_IDS:
        assert len(out.annotation_gt.value) == 1
        assert annotation_clusters == [expected_answer]
        assert out.annotation_gt.value == {'answer_cluster': render_map['cluster_envelope_bboxes_px'][expected_answer]}
        assert out.annotation_gt.value == {'answer_cluster': render_map['cluster_bboxes_px'][expected_answer]}
        assert 0.1 <= float(execution['cluster_area_nearest_relative_gap']) <= 0.3
        ordered = [str(label) for label in execution['cluster_area_order_largest_to_smallest']]
        assert ordered == sorted([str(label) for label in execution['cluster_labels']], key=lambda label: (-float(execution['cluster_area_metrics'][label]), label))
    else:
        assert len(out.annotation_gt.value) == 1
        assert annotation_clusters == [expected_answer]
        assert out.annotation_gt.value == {'answer_cluster': render_map['cluster_bboxes_px'][expected_answer]}

def test_chart_scatter_prompt_examples_match_contract() -> None:
    task = ChartsScatterClusterQueryTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS, start=91400):
        out = task.generate(index, params={'query_id': query_id}, max_attempts=80)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
        answer_only = extract_prompt_json_example(out.prompt_variants['answer_only'])
        assert isinstance(answer_and_annotation['answer'], str)
        assert isinstance(answer_and_annotation['annotation'], dict)
        assert isinstance(answer_only['answer'], str)
        if query_id == 'centroid_option_selection_label':
            assert answer_and_annotation['answer'] in _OPTION_LABELS
            assert answer_only['answer'] in _OPTION_LABELS
        assert 'from from' not in out.prompt
        assert 'to to' not in out.prompt

def test_chart_scatter_balanced_sampling_covers_axes() -> None:
    task = ChartsScatterClusterQueryTask()
    variants: Counter[str] = Counter()
    cluster_answer_labels: Counter[str] = Counter()
    cluster_counts: Counter[int] = Counter()
    trend_directions: Counter[str] = Counter()
    separation_extrema: Counter[str] = Counter()
    spread_axes: Counter[str] = Counter()
    spread_extrema: Counter[str] = Counter()
    area_ranks: Counter[str] = Counter()
    option_answers: Counter[str] = Counter()
    for index in range(90):
        out = task.generate(hash64(91500, 'charts_scatter', index), params={}, max_attempts=300)
        execution = out.trace_payload['execution_trace']
        variants[str(execution['query_id'])] += 1
        if str(execution['query_id']) != 'centroid_option_selection_label':
            cluster_answer_labels[str(execution['answer'])] += 1
        cluster_counts[int(execution['cluster_count'])] += 1
        if 'trend_direction' in execution:
            trend_directions[str(execution['trend_direction'])] += 1
        if 'separation_extremum' in execution:
            separation_extrema[str(execution['separation_extremum'])] += 1
        if 'spread_axis' in execution:
            spread_axes[str(execution['spread_axis'])] += 1
        if 'spread_extremum' in execution:
            spread_extrema[str(execution['spread_extremum'])] += 1
        if 'area_rank' in execution:
            area_ranks[str(execution['area_rank'])] += 1
        if str(execution['query_id']) == 'centroid_option_selection_label':
            option_answers[str(execution['answer'])] += 1
    assert set(variants) == set(SUPPORTED_QUERY_IDS)
    assert min(cluster_counts) >= 4
    assert max(cluster_counts) <= 7
    assert len(cluster_counts) >= 3
    assert len(cluster_answer_labels) >= 8
    assert set(cluster_answer_labels).isdisjoint({'A', 'B', 'C', 'D', 'E', 'F'})
    assert set(trend_directions) == {'upward', 'downward'}
    assert set(separation_extrema) == {'closest', 'farthest'}
    assert set(spread_axes) == {'horizontal', 'vertical', 'overall'}
    assert set(spread_extrema) == {'largest', 'smallest'}
    assert set(area_ranks) == {'largest', 'second_largest', 'smallest'}
    assert set(option_answers).issubset(_OPTION_LABELS)
    assert {'A', 'B', 'C', 'D'}.issubset(set(option_answers))

def test_chart_scatter_is_deterministic() -> None:
    task = ChartsScatterClusterQueryTask()
    params = {'query_id': 'cluster_spread_extremum_label', 'spread_axis': 'overall', 'spread_extremum': 'largest'}
    out_a = task.generate(91600, params=params, max_attempts=80)
    out_b = task.generate(91600, params=params, max_attempts=80)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']

def test_chart_scatter_registered_and_group_config_loaded() -> None:
    assert create_task('task_charts__scatter_cluster__cluster_trend_direction_label').task_id == 'task_charts__scatter_cluster__cluster_trend_direction_label'
    assert create_task('task_charts__scatter_cluster__centroid_option_selection_label').task_id == 'task_charts__scatter_cluster__centroid_option_selection_label'
    assert create_task('task_charts__scatter_cluster__cluster_area_rank_label').task_id == 'task_charts__scatter_cluster__cluster_area_rank_label'
    cfg = get_scene_defaults('charts', 'scatter_cluster')
    assert isinstance(cfg.get('generation'), dict)
    assert isinstance(cfg.get('rendering'), dict)
    assert isinstance(cfg.get('prompt'), dict)
    generation = cfg['generation']['shared']
    assert int(generation['cluster_count_min']) == 4
    assert int(generation['cluster_count_max']) == 7
    assert sorted(generation['query_id_weights'].keys()) == sorted(SUPPORTED_QUERY_IDS)
    prompt = cfg['prompt']['shared']
    assert str(prompt['bundle_id']) == 'charts_scatter_v0'
    assert str(prompt['scene_key']) == 'scatter_cluster'
    assert str(prompt['task_key']) == 'scatter_cluster_query'
