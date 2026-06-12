"""Behavior tests for cell-board path tasks."""
from __future__ import annotations
import json
from trace.tasks.puzzles.cell_board.path_reachable_target_count import TileReachableTargetCountTask
from tests.cell_board_annotation_helpers import tile_coords_from_points, tile_ids_from_points
from trace.tasks.puzzles.cell_board.path_shortest_path import TileShortestPathTask

def _extract_prompt_json_example(prompt: str) -> dict:
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)

def test_cell_board_shortest_path_outputs_expected_contract() -> None:
    task = TileShortestPathTask()
    out = task.generate(7701, params={'rows': 7, 'cols': 7, 'target_shortest_len_min': 3, 'target_shortest_len_max': 10, 'short_side_px_min': 32, 'short_side_px_max': 32, 'aspect_ratio_min': 1.0, 'aspect_ratio_max': 1.0, 'obstacle_prob_min': 0.2, 'obstacle_prob_max': 0.2}, max_attempts=160)
    trace = out.trace_payload
    execution = trace['execution_trace']
    render = trace['render_spec']
    assert str(out.query_id) == 'shortest_path'
    assert out.answer_gt.type == 'integer'
    assert out.annotation_gt.type == 'point_sequence'
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    assert str(render['tiling_type']) == 'rectangular_tiling'
    assert float(render['tile_aspect_ratio']) == 1.0
    assert int(render['tile_width_px']) == int(render['tile_height_px'])
    assert out.image.size == (int(render['canvas_width_px']), int(render['canvas_height_px']))
    assert int(execution['board_size']) == 7
    assert execution['board_size_range'] == [7, 7]
    assert trace['projected_annotation']['type'] == 'point_sequence'
    assert trace['projected_annotation']['point_sequence'] == out.annotation_gt.value
    assert trace['projected_annotation']['pixel_point_sequence'] == out.annotation_gt.value
    path_coords = tile_coords_from_points(trace, out.annotation_gt.value)
    assert path_coords == execution['path_coords']
    assert int(out.answer_gt.value) == len(path_coords) - 1
    assert path_coords[0] == execution['start_coord']
    assert path_coords[-1] == execution['goal_coord']
    assert str(execution['obstacle_color_label']).endswith('[#000000]')
    assert str(execution['start_color_label']) in str(out.prompt)
    assert str(execution['goal_color_label']) in str(out.prompt)
    path_entities = [entity for entity in trace['scene_ir']['entities'] if bool(entity['attrs']['is_on_shortest_path'])]
    assert len(path_entities) == len(path_coords)
    start_entities = [entity for entity in path_entities if bool(entity['attrs']['is_start'])]
    goal_entities = [entity for entity in path_entities if bool(entity['attrs']['is_goal'])]
    assert len(start_entities) == 1
    assert len(goal_entities) == 1
    assert start_entities[0]['attrs']['fill_rgb'] == execution['start_color_rgb']
    assert goal_entities[0]['attrs']['fill_rgb'] == execution['goal_color_rgb']

def test_cell_board_shortest_path_is_deterministic() -> None:
    task = TileShortestPathTask()
    params = {'rows': 7, 'cols': 7, 'target_shortest_len_min': 3, 'target_shortest_len_max': 10, 'aspect_ratio_min': 1.0, 'aspect_ratio_max': 1.0}
    out_a = task.generate(7719, params=params, max_attempts=160)
    out_b = task.generate(7719, params=params, max_attempts=160)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['witness_symbolic'] == out_b.trace_payload['witness_symbolic']
    assert out_a.trace_payload['query_spec']['prompt_variant'] == out_b.trace_payload['query_spec']['prompt_variant']
    assert out_a.trace_payload['execution_trace']['target_shortest_len'] == out_b.trace_payload['execution_trace']['target_shortest_len']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_cell_board_shortest_path_prompt_example_matches_contract() -> None:
    task = TileShortestPathTask()
    out = task.generate(7733, params={}, max_attempts=160)
    example = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
    assert list(example.keys()) == ['annotation', 'answer']
    assert example['annotation'] == [[120, 120], [168, 120], [168, 168], [216, 168]]
    assert int(example['answer']) == 3

def test_cell_board_shortest_path_samples_square_board_size_range() -> None:
    task = TileShortestPathTask()
    observed_sizes = []
    for sampling_index in range(3):
        out = task.generate(7737 + sampling_index, params={'board_size_min': 6, 'board_size_max': 8}, max_attempts=320)
        execution = out.trace_payload['execution_trace']
        observed_sizes.append(int(execution['board_size']))
        assert int(execution['rows']) == int(execution['cols']) == int(execution['board_size'])
        assert execution['board_size_range'] == [6, 8]
    assert all((6 <= size <= 8 for size in observed_sizes))
    assert len(set(observed_sizes)) >= 2

def test_cell_board_reachable_target_count_outputs_expected_contract() -> None:
    task = TileReachableTargetCountTask()
    out = task.generate(7749, params={'rows': 7, 'cols': 7, 'target_reachable_target_count_min': 2, 'target_reachable_target_count_max': 2, 'short_side_px_min': 32, 'short_side_px_max': 32, 'aspect_ratio_min': 1.0, 'aspect_ratio_max': 1.0, 'obstacle_prob_min': 0.2, 'obstacle_prob_max': 0.2}, max_attempts=160)
    trace = out.trace_payload
    execution = trace['execution_trace']
    render = trace['render_spec']
    assert str(out.query_id) == 'reachable_target_count'
    assert out.answer_gt.type == 'integer'
    assert out.annotation_gt.type == 'point_set'
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    assert str(render['tiling_type']) == 'rectangular_tiling'
    assert float(render['tile_aspect_ratio']) == 1.0
    assert int(render['tile_width_px']) == int(render['tile_height_px'])
    assert out.image.size == (int(render['canvas_width_px']), int(render['canvas_height_px']))
    assert int(execution['board_size']) == 7
    assert execution['board_size_range'] == [7, 7]
    assert trace['projected_annotation']['type'] == 'point_set'
    assert trace['projected_annotation']['point_set'] == out.annotation_gt.value
    assert trace['projected_annotation']['pixel_point_set'] == out.annotation_gt.value
    annotation_coords = tile_coords_from_points(trace, out.annotation_gt.value)
    assert annotation_coords == execution['reachable_target_coords']
    assert int(out.answer_gt.value) == len(annotation_coords) == 2
    assert execution['target_reachable_target_count_range'] == [2, 2]
    assert int(execution['target_reachable_target_count']) == 2
    assert int(execution['total_target_count']) == 3
    assert str(execution['obstacle_color_label']).endswith('[#000000]')
    assert str(execution['start_color_label']) in str(out.prompt)
    assert str(execution['target_color_label']) in str(out.prompt)
    target_coords = {tuple(coord) for coord in execution['target_coords']}
    reachable_target_coords = {tuple(coord) for coord in execution['reachable_target_coords']}
    unreachable_target_coords = {tuple(coord) for coord in execution['unreachable_target_coords']}
    assert len(target_coords) == 3
    assert reachable_target_coords == {tuple(coord) for coord in annotation_coords}
    assert reachable_target_coords.isdisjoint({tuple(execution['start_coord'])})
    assert reachable_target_coords.issubset(target_coords)
    assert unreachable_target_coords.issubset(target_coords)
    assert reachable_target_coords.isdisjoint(unreachable_target_coords)
    target_entities = [entity for entity in trace['scene_ir']['entities'] if bool(entity['attrs']['is_target'])]
    assert len(target_entities) == 3
    reachable_target_entities = [entity for entity in target_entities if bool(entity['attrs']['is_reachable_target'])]
    unreachable_target_entities = [entity for entity in target_entities if bool(entity['attrs']['is_unreachable_target'])]
    assert len(reachable_target_entities) == 2
    assert len(unreachable_target_entities) == 1
    assert all((entity['attrs']['fill_rgb'] == execution['target_color_rgb'] for entity in target_entities))

def test_cell_board_reachable_target_count_supports_zero_answer_with_empty_annotation() -> None:
    task = TileReachableTargetCountTask()
    out = task.generate(7751, params={'rows': 7, 'cols': 7, 'target_reachable_target_count_min': 0, 'target_reachable_target_count_max': 0}, max_attempts=160)
    execution = out.trace_payload['execution_trace']
    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.value == []
    assert execution['reachable_target_coords'] == []
    assert int(execution['total_target_count']) >= 2
    assert 'or [] if no target tiles are reachable' in out.prompt_variants['answer_and_annotation']

def test_cell_board_reachable_target_count_is_deterministic() -> None:
    task = TileReachableTargetCountTask()
    params = {'rows': 7, 'cols': 7, 'target_reachable_target_count_min': 0, 'target_reachable_target_count_max': 5, 'aspect_ratio_min': 1.0, 'aspect_ratio_max': 1.0}
    out_a = task.generate(7767, params=params, max_attempts=160)
    out_b = task.generate(7767, params=params, max_attempts=160)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload['witness_symbolic'] == out_b.trace_payload['witness_symbolic']
    assert out_a.trace_payload['query_spec']['prompt_variant'] == out_b.trace_payload['query_spec']['prompt_variant']
    assert out_a.trace_payload['execution_trace']['target_reachable_target_count'] == out_b.trace_payload['execution_trace']['target_reachable_target_count']
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_cell_board_reachable_target_count_prompt_example_matches_contract() -> None:
    task = TileReachableTargetCountTask()
    out = task.generate(7773, params={}, max_attempts=160)
    example = _extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
    assert list(example.keys()) == ['annotation', 'answer']
    assert example['annotation'] == [[216, 120], [168, 216]]
    assert int(example['answer']) == 2

def test_cell_board_reachable_target_count_samples_square_board_size_range() -> None:
    task = TileReachableTargetCountTask()
    observed_sizes = []
    for sampling_index in range(3):
        out = task.generate(7777 + sampling_index, params={'board_size_min': 6, 'board_size_max': 8}, max_attempts=320)
        execution = out.trace_payload['execution_trace']
        observed_sizes.append(int(execution['board_size']))
        assert int(execution['rows']) == int(execution['cols']) == int(execution['board_size'])
        assert execution['board_size_range'] == [6, 8]
    assert all((6 <= size <= 8 for size in observed_sizes))
    assert len(set(observed_sizes)) >= 2
