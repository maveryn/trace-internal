"""Behavior tests for chart distribution tasks."""
from __future__ import annotations
import json
from trace.tasks.charts.boxplot.shared.boxplot_label import ChartsDistributionBoxplotLabelTask, ChartsDistributionBoxplotMedianRankDifferenceValueTask, ChartsDistributionBoxplotPairedMedianShiftLabelTask
from trace.tasks.charts.histogram.shared.histogram_count import ChartsDistributionHistogramCountTask, ChartsDistributionHistogramCumulativeRankLabelTask
from trace.tasks.charts.violin.shared.violin_label import ChartsDistributionViolinLabelTask, ChartsDistributionViolinModeExtremumLabelTask, ChartsDistributionViolinModalityLabelTask, ChartsDistributionViolinSupportWidthExtremumLabelTask

def _extract_prompt_json_example(prompt: str) -> dict:
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)

def _assert_value_axis_covers_values(render: dict, values: list[int]) -> None:
    assert int(render['value_axis_min']) <= min((int(value) for value in values))
    assert max((int(value) for value in values)) <= int(render['value_axis_max'])
    assert int(render['value_axis_span']) == int(render['value_axis_max']) - int(render['value_axis_min'])
    assert set((int(value) for value in render['y_ticks'])).issubset(set((int(value) for value in render['value_axis_minor_ticks'])))

def test_chart_distribution_histogram_variants_match_contract() -> None:
    task = ChartsDistributionHistogramCountTask()
    cases = (('interval_mass', {'interval_relation': 'inside'}), ('interval_mass', {'interval_relation': 'outside'}), ('bin_count_between_values', {}), ('rank_item_bin_label', {}))
    for seed, (query_id, extra_params) in enumerate(cases, start=11010):
        out = task.generate(seed, params={'query_id': query_id, **extra_params}, max_attempts=10)
        trace = out.trace_payload
        execution = trace['execution_trace']
        render = trace['render_spec']
        labels = [str(label) for label in execution['labels']]
        counts = [int(value) for value in execution['bin_counts']]
        counts_by_label = {str(label): int(value) for label, value in execution['counts_by_label'].items()}
        intervals_by_label = {str(entity['attrs']['label']): (int(entity['attrs']['interval_start']), int(entity['attrs']['interval_end'])) for entity in trace['scene_ir']['entities']}
        annotation_bboxes = [list(bbox) for bbox in out.annotation_gt.value]
        annotation_labels = [str(label) for label in execution['annotation_labels']]
        axis_values = [int(label) for label in labels]
        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == 'integer'
        assert out.annotation_gt.type == 'bbox_set'
        assert str(execution['scene_variant']) == 'histogram'
        assert str(render['scene_variant']) == 'histogram'
        assert render['information_scene_style']['kind'] == 'information_scene_style'
        assert render['information_scene_style']['style_request']['style_family'] == 'information_scene'
        assert render['information_scene_style']['style_request']['domain'] == 'charts'
        assert trace['projected_annotation']['bbox_set'] == annotation_bboxes
        assert len(trace['projected_annotation']['bbox_set']) == len(annotation_labels)
        assert len(annotation_bboxes) == len(annotation_labels)
        assert len(trace['scene_ir']['entities']) == int(execution['bin_count'])
        assert set((str(entity['attrs']['label']) for entity in trace['scene_ir']['entities'])) == set(labels)
        assert set(trace['render_map']['label_centers_px'].keys()) == set(labels)
        assert out.image.size == (int(render['canvas_width']), int(render['canvas_height']))
        assert max(axis_values) <= 99
        assert all((int(entity['attrs']['interval_start']) == int(entity['attrs']['interval_end']) for entity in trace['scene_ir']['entities']))
        _assert_value_axis_covers_values(render, counts)
        assert int(render['value_axis_min']) == 0
        assert render['guide_line_style'] in {'dashed', 'dotted', 'solid'}
        assert len(render['guide_lines']) == int(execution['bin_count'])
        if str(query_id) in {'interval_mass', 'bin_count_between_values'}:
            query_start = int(execution['query_interval_start_value'])
            query_end = int(execution['query_interval_end_value'])
            assert str(execution['query_interval_label']) == f'{query_start}-{query_end}'
            inside_interval_labels = [str(label) for label in labels if int(intervals_by_label[str(label)][0]) >= query_start and int(intervals_by_label[str(label)][1]) <= query_end]
            outside_interval_labels = [str(label) for label in labels if str(label) not in set(inside_interval_labels)]
        if str(query_id) == 'interval_mass' and str(execution['interval_relation']) == 'inside':
            assert 5 <= len(annotation_labels) <= int(execution['bin_count'])
            assert annotation_labels == inside_interval_labels
            assert int(out.answer_gt.value) == sum((int(counts_by_label[label]) for label in annotation_labels))
        elif str(query_id) == 'bin_count_between_values':
            assert 2 <= len(annotation_labels) <= 15
            assert annotation_labels == inside_interval_labels
            assert int(out.answer_gt.value) == len(annotation_labels)
        elif str(query_id) == 'rank_item_bin_label':
            answer_index = int(execution['answer_bin_index'])
            target_rank = int(execution['target_rank'])
            assert annotation_labels == [labels[answer_index]]
            assert str(execution['answer_bin_label']) == str(labels[answer_index])
            assert int(out.answer_gt.value) == int(labels[answer_index])
            assert int(execution['cumulative_count_before_answer_bin']) < target_rank
            assert target_rank <= int(execution['cumulative_count_through_answer_bin'])
        else:
            assert str(query_id) == 'interval_mass'
            assert str(execution['interval_relation']) == 'outside'
            assert 2 <= len(annotation_labels) <= int(execution['bin_count'])
            assert annotation_labels == outside_interval_labels
            assert int(out.answer_gt.value) == sum((int(counts_by_label[label]) for label in annotation_labels))
            assert int(execution['outside_bin_count']) == len(annotation_labels)
            assert int(execution['outside_left_bin_count']) >= 1
            assert int(execution['outside_right_bin_count']) >= 1
            assert int(execution['outside_left_bin_count']) + int(execution['outside_right_bin_count']) == len(annotation_labels)
            assert int(execution['excluded_interval_bin_span']) == len(inside_interval_labels)
            assert int(execution['excluded_interval_bin_span']) >= 2

def test_histogram_bins_are_contiguous_numeric_intervals() -> None:
    task = ChartsDistributionHistogramCountTask()
    out = task.generate(11030, params={'query_id': 'interval_mass'}, max_attempts=10)
    entities = out.trace_payload['scene_ir']['entities']
    intervals = [(int(entity['attrs']['interval_start']), int(entity['attrs']['interval_end'])) for entity in entities]
    for index in range(len(intervals) - 1):
        assert int(intervals[index][1]) + 1 == int(intervals[index + 1][0])
    assert all((int(start) == int(end) for start, end in intervals))
    assert max((int(end) for _, end in intervals)) <= 99

def test_chart_distribution_histogram_prompt_examples_match_selected_variant() -> None:
    task = ChartsDistributionHistogramCountTask()
    expected = {'interval_mass': {'annotation': [[160, 260, 204, 520], [212, 300, 256, 520], [264, 240, 308, 520]], 'answer': 15}, 'bin_count_between_values': {'annotation': [[160, 260, 204, 520], [212, 300, 256, 520], [264, 240, 308, 520]], 'answer': 3}, 'rank_item_bin_label': {'annotation': [[264, 240, 308, 520]], 'answer': 18}}
    for index, query_id in enumerate(expected, start=11040):
        out = task.generate(index, params={'query_id': query_id}, max_attempts=10)
        answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
        answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
        assert answer_and_annotation == expected[query_id]
        assert answer_only == {'answer': expected[query_id]['answer']}

def test_chart_distribution_histogram_task_is_deterministic() -> None:
    task = ChartsDistributionHistogramCountTask()
    params = {'query_id': 'bin_count_between_values'}
    out_a = task.generate(11060, params=params, max_attempts=10)
    out_b = task.generate(11060, params=params, max_attempts=10)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.trace_payload['query_spec']['prompt_variant'] == out_b.trace_payload['query_spec']['prompt_variant']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_chart_distribution_histogramseeded_sampler_decouples_variant_and_answer_support() -> None:
    task = ChartsDistributionHistogramCountTask()
    bin_count_answers = []
    for sampling_index in range(42):
        out = task.generate(11070 + sampling_index, params={}, max_attempts=10)
        if str(out.query_id) == 'bin_count_between_values':
            bin_count_answers.append(int(out.answer_gt.value))
    assert set(bin_count_answers).issubset(set(range(2, 16)))
    assert len(set(bin_count_answers)) >= 8

def test_chart_distribution_histogram_cumulative_rank_public_task_contract() -> None:
    task = ChartsDistributionHistogramCumulativeRankLabelTask()
    out = task.generate(11080, params={}, max_attempts=10)
    execution = out.trace_payload['execution_trace']
    query_spec = out.trace_payload['query_spec']
    assert str(out.query_id) == 'rank_item_bin_label'
    assert str(execution['query_id']) == 'rank_item_bin_label'
    assert str(query_spec['params']['query_id']) == 'rank_item_bin_label'
    assert out.answer_gt.type == 'integer'
    assert out.annotation_gt.type == 'bbox_set'

def test_chart_distribution_boxplot_variants_match_contract() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    cases = (('median_reference_label', {'median_reference_direction': 'above_reference_q3'}), ('median_reference_label', {'median_reference_direction': 'below_reference_q1'}), ('iqr_extremum_label', {'extremum_direction': 'largest'}), ('iqr_extremum_label', {'extremum_direction': 'smallest'}))
    for seed, (query_id, extra_params) in enumerate(cases, start=11110):
        out = task.generate(seed, params={'query_id': query_id, **extra_params}, max_attempts=10)
        trace = out.trace_payload
        execution = trace['execution_trace']
        render = trace['render_spec']
        quartiles_by_label = {str(label): dict(values) for label, values in execution['quartiles_by_label'].items()}
        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == 'string'
        assert str(execution['scene_variant']) == 'boxplot'
        assert str(render['scene_variant']) == 'boxplot'
        if str(query_id) == 'median_reference_label':
            assert out.annotation_gt.type == 'keyed_point_map'
            assert trace['projected_annotation']['type'] == 'keyed_point_map'
            assert set(out.annotation_gt.value) == {'reference_boxplot', 'answer_boxplot'}
            assert trace['projected_annotation']['keyed_point_map'] == out.annotation_gt.value
        else:
            assert out.annotation_gt.type == 'point_set'
            annotation_points = [list(point) for point in out.annotation_gt.value]
            assert trace['projected_annotation']['type'] == 'point_set'
            assert trace['projected_annotation']['point_set'] == annotation_points
            assert trace['projected_annotation']['pixel_point_set'] == annotation_points
            assert len(trace['projected_annotation']['bbox_set']) == 1
        assert out.image.size == (int(render['canvas_width']), int(render['canvas_height']))
        all_box_values = [int(value) for stats in quartiles_by_label.values() for value in (stats['whisker_min'], stats['q1'], stats['median'], stats['q3'], stats['whisker_max'])]
        _assert_value_axis_covers_values(render, all_box_values)
        for stats in quartiles_by_label.values():
            assert int(stats['whisker_min']) <= int(stats['q1']) < int(stats['median']) < int(stats['q3']) <= int(stats['whisker_max'])
        if str(query_id) == 'median_reference_label' and str(execution['median_reference_direction']) == 'above_reference_q3':
            reference_label = str(execution['reference_label'])
            reference_q3 = int(execution['reference_q3'])
            target_label = max((str(label) for label in quartiles_by_label if str(label) != str(reference_label)), key=lambda label: int(quartiles_by_label[label]['median']) - int(reference_q3))
            assert str(out.answer_gt.value) == str(target_label)
            assert int(execution['annotation_value']) == int(quartiles_by_label[target_label]['median']) - int(reference_q3)
        elif str(query_id) == 'median_reference_label' and str(execution['median_reference_direction']) == 'below_reference_q1':
            reference_label = str(execution['reference_label'])
            reference_q1 = int(execution['reference_q1'])
            target_label = max((str(label) for label in quartiles_by_label if str(label) != str(reference_label)), key=lambda label: int(reference_q1) - int(quartiles_by_label[label]['median']))
            assert str(out.answer_gt.value) == str(target_label)
            assert int(execution['annotation_value']) == int(reference_q1) - int(quartiles_by_label[target_label]['median'])
        elif str(query_id) == 'iqr_extremum_label' and str(execution['extremum_direction']) == 'largest':
            target_label = max(quartiles_by_label, key=lambda label: int(quartiles_by_label[label]['iqr']))
            assert str(out.answer_gt.value) == str(target_label)
            assert int(execution['annotation_value']) == int(quartiles_by_label[target_label]['iqr'])
        else:
            assert str(query_id) == 'iqr_extremum_label'
            assert str(execution['extremum_direction']) == 'smallest'
            target_label = min(quartiles_by_label, key=lambda label: int(quartiles_by_label[label]['iqr']))
            assert str(out.answer_gt.value) == str(target_label)
            assert int(execution['annotation_value']) == int(quartiles_by_label[target_label]['iqr'])

def test_chart_distribution_boxplot_prompt_examples_match_selected_variant() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    expected = {'median_reference_label': {'annotation': {'reference_boxplot': [240, 300], 'answer_boxplot': [430, 250]}, 'answer': 'Maple'}, 'iqr_extremum_label': {'annotation': [[430, 250]], 'answer': 'Ivory'}}
    for index, query_id in enumerate(expected, start=11140):
        out = task.generate(index, params={'query_id': query_id}, max_attempts=10)
        answer_and_annotation = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
        answer_only = _extract_prompt_json_example(out.prompt_variants['answer_only'])
        assert answer_and_annotation == expected[query_id]
        assert answer_only == {'answer': expected[query_id]['answer']}

def test_chart_distribution_boxplot_task_is_deterministic() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    params = {'query_id': 'iqr_extremum_label', 'extremum_direction': 'largest'}
    out_a = task.generate(11160, params=params, max_attempts=10)
    out_b = task.generate(11160, params=params, max_attempts=10)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['execution_trace'] == out_b.trace_payload['execution_trace']
    assert out_a.trace_payload['query_spec']['prompt_variant'] == out_b.trace_payload['query_spec']['prompt_variant']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_chart_distribution_boxplot_can_tighten_reference_q3_winner_gap() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    out = task.generate(11162, params={'query_id': 'median_reference_label', 'median_reference_direction': 'above_reference_q3', 'category_count_min': 7, 'category_count_max': 7, 'median_reference_winner_gap_min': 1, 'median_reference_winner_gap_max': 1}, max_attempts=10)
    execution = out.trace_payload['execution_trace']
    quartiles_by_label = execution['quartiles_by_label']
    reference_q3 = int(execution['reference_q3'])
    margins = sorted((int(stats['median']) - int(reference_q3) for label, stats in quartiles_by_label.items() if str(label) != str(execution['reference_label']) and int(stats['median']) > int(reference_q3)))
    assert margins[-1] - margins[-2] == 1

def test_chart_distribution_boxplot_supports_query_id_overrides() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    out = task.generate(11164, params={'query_id': 'median_reference_label', 'median_reference_direction': 'above_reference_q3', 'category_count_min': 4, 'category_count_max': 7, 'query_id_overrides': {'median_reference_label': {'category_count_min': 8, 'category_count_max': 8, 'median_reference_winner_gap_min': 1, 'median_reference_winner_gap_max': 1}}}, max_attempts=10)
    execution = out.trace_payload['execution_trace']
    assert int(execution['category_count']) == 8
    reference_q3 = int(execution['reference_q3'])
    margins = sorted((int(stats['median']) - int(reference_q3) for label, stats in execution['quartiles_by_label'].items() if str(label) != str(execution['reference_label']) and int(stats['median']) > int(reference_q3)))
    assert margins[-1] - margins[-2] == 1

def test_chart_distribution_boxplot_can_tighten_iqr_winner_gap() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    for seed, extremum_direction in enumerate(('largest', 'smallest'), start=11163):
        out = task.generate(seed, params={'query_id': 'iqr_extremum_label', 'extremum_direction': extremum_direction, 'category_count_min': 7, 'category_count_max': 7, 'iqr_winner_gap_min': 1, 'iqr_winner_gap_max': 1}, max_attempts=10)
        quartiles_by_label = out.trace_payload['execution_trace']['quartiles_by_label']
        iqrs = sorted((int(stats['iqr']) for stats in quartiles_by_label.values()))
        if extremum_direction == 'largest':
            assert iqrs[-1] - iqrs[-2] == 1
        else:
            assert iqrs[1] - iqrs[0] == 1

def test_chart_distribution_boxplot_uses_configured_iqr_winner_gap() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    for seed, extremum_direction in enumerate(('largest', 'smallest'), start=11167):
        out = task.generate(seed, params={'query_id': 'iqr_extremum_label', 'extremum_direction': extremum_direction, 'category_count_min': 7, 'category_count_max': 7}, max_attempts=10)
        quartiles_by_label = out.trace_payload['execution_trace']['quartiles_by_label']
        iqrs = sorted((int(stats['iqr']) for stats in quartiles_by_label.values()))
        if extremum_direction == 'largest':
            assert iqrs[-1] - iqrs[-2] == 1
        else:
            assert iqrs[1] - iqrs[0] == 1

def test_chart_distribution_boxplot_public_role_bound_tasks_use_keyed_annotation() -> None:
    median_rank = ChartsDistributionBoxplotMedianRankDifferenceValueTask().generate(11180, params={'query_id': 'median_top_second_difference_value'}, max_attempts=10)
    assert median_rank.answer_gt.type == 'integer'
    assert median_rank.annotation_gt.type == 'keyed_point_map'
    assert set(median_rank.annotation_gt.value) == {'highest_median_boxplot', 'second_highest_median_boxplot'}
    assert median_rank.trace_payload['projected_annotation']['type'] == 'keyed_point_map'
    assert median_rank.trace_payload['projected_annotation']['keyed_point_map'] == median_rank.annotation_gt.value
    paired_shift = ChartsDistributionBoxplotPairedMedianShiftLabelTask().generate(11181, params={'query_id': 'paired_median_greatest_increase_label'}, max_attempts=10)
    assert paired_shift.answer_gt.type == 'string'
    assert paired_shift.annotation_gt.type == 'keyed_point_map'
    assert set(paired_shift.annotation_gt.value) == {'before_boxplot', 'after_boxplot'}
    assert paired_shift.trace_payload['projected_annotation']['type'] == 'keyed_point_map'
    assert paired_shift.trace_payload['projected_annotation']['keyed_point_map'] == paired_shift.annotation_gt.value

def test_chart_distribution_violin_variants_match_contract() -> None:
    task = ChartsDistributionViolinLabelTask()
    for seed, query_id in enumerate(('highest_mode', 'lowest_mode', 'bimodal_label', 'widest_support', 'narrowest_support'), start=11210):
        out = task.generate(seed, params={'query_id': query_id}, max_attempts=10)
        trace = out.trace_payload
        execution = trace['execution_trace']
        render = trace['render_spec']
        support_by_label = {str(label): dict(values) for label, values in execution['support_by_label'].items()}
        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == 'string'
        assert out.annotation_gt.type == 'bbox_set'
        assert str(execution['scene_variant']) == 'violin'
        assert str(render['scene_variant']) == 'violin'
        assert str(render['violin_style']['mode_line_style']) in {'full', 'short', 'dot', 'none'}
        assert str(render['violin_style']['fill_style']) in {'solid', 'light', 'outline', 'hatch'}
        assert str(render['violin_style']['palette_mode']) in {'single', 'per_violin_muted'}
        assert str(render['font_assets']['chart_font_family']).strip()
        assert str(trace['scene_ir']['scene_kind']) == 'chart_violin_distribution'
        assert trace['projected_annotation']['type'] == 'bbox_set'
        assert trace['projected_annotation']['bbox_set'] == [list(bbox) for bbox in out.annotation_gt.value]
        assert len(trace['projected_annotation']['bbox_set']) == 1
        assert out.image.size == (int(render['canvas_width']), int(render['canvas_height']))
        assert len(trace['scene_ir']['entities']) == int(execution['category_count'])
        assert set(trace['render_map']['label_centers_px'].keys()) == set(execution['labels'])
        if str(query_id) == 'highest_mode':
            expected = max(support_by_label, key=lambda label: int(support_by_label[label]['mode_values'][0]))
        elif str(query_id) == 'lowest_mode':
            expected = min(support_by_label, key=lambda label: int(support_by_label[label]['mode_values'][0]))
        elif str(query_id) == 'bimodal_label':
            expected = next((label for label, values in support_by_label.items() if bool(values['bimodal'])))
            assert len(execution['annotation_values']) == 2
        elif str(query_id) == 'widest_support':
            expected = max(support_by_label, key=lambda label: int(support_by_label[label]['support_span']))
        else:
            expected = min(support_by_label, key=lambda label: int(support_by_label[label]['support_span']))
        assert str(out.answer_gt.value) == str(expected)

def test_chart_distribution_violin_public_task_contract() -> None:
    cases = ((ChartsDistributionViolinModeExtremumLabelTask, {'highest_mode', 'lowest_mode'}), (ChartsDistributionViolinSupportWidthExtremumLabelTask, {'widest_support', 'narrowest_support'}), (ChartsDistributionViolinModalityLabelTask, {'bimodal_label'}))
    for task_cls, allowed_query_ids in cases:
        out = task_cls().generate(11280 + len(task_cls.task_id), params={}, max_attempts=10)
        execution = out.trace_payload['execution_trace']
        query_spec = out.trace_payload['query_spec']
        assert str(out.query_id) in allowed_query_ids
        assert str(execution['query_id']) == str(out.query_id)
        assert str(query_spec['params']['query_id']) == str(out.query_id)
        assert out.answer_gt.type == 'string'
        assert out.annotation_gt.type == 'bbox_set'
