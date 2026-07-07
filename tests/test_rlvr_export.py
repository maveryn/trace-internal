from __future__ import annotations
import json
from pathlib import Path
import pyarrow.parquet as pq
from PIL import Image
from trace.core.rlvr_export import build_rlvr_row, export_trace_dataset_to_rlvr

def _write_trace_dataset(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    dataset_root = tmp_path / 'trace_dataset'
    image_path = dataset_root / 'images' / 'geometry' / 'task_geometry__coordinate_plane__segment_relation_count' / '000000.png'
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (8, 8), (255, 255, 255)).save(image_path)
    train_record = {'instance_id': 'inst-001', 'domain': 'geometry', 'scene_id': 'coordinate', 'task': 'task_geometry__coordinate_plane__segment_relation_count', 'scene_id': 'coordinate_plane', 'query_id': 'perpendicular_count', 'prompt': 'active prompt', 'prompt_variants': {'answer_only': 'Count the marked dots.\nUse a valid JSON object with key "answer" for the final answer.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"answer":3}', 'answer_and_annotation': 'Count the marked dots and cite the supporting positions.\nUse a valid JSON object with keys "annotation" and "answer" in that order for the final answer.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'}, 'images': [{'image_id': 'img-001', 'format': 'png', 'image_hash': 'hash-001', 'path': 'images/geometry/task_geometry__coordinate_plane__segment_relation_count/000000.png'}], 'answer_gt': {'type': 'integer', 'value': 3}, 'annotation_gt': {'type': 'point_set', 'value': [[1, 2], [3, 4], [5, 6]]}, 'reward_contract': {'reward_contract_version': 'v0', 'answer': {'id': 'answer_exact_match_v0', 'type': 'integer'}, 'annotation': {'id': 'point_set_soft_distance_v0', 'type': 'point_set'}}, 'trace_ref': {'shard_id': 'trace-0001', 'line_index': 0, 'trace_record_hash': 'trace-hash'}}
    train_instances_path = dataset_root / 'train_instances.jsonl'
    train_instances_path.parent.mkdir(parents=True, exist_ok=True)
    train_instances_path.write_text(json.dumps(train_record) + '\n', encoding='utf-8')
    return (dataset_root, train_record)

def test_build_rlvr_row_uses_requested_prompt_variant_and_relative_image_paths(tmp_path: Path) -> None:
    dataset_root, train_record = _write_trace_dataset(tmp_path)
    export_parent = tmp_path / 'exports' / 'jsonl'
    export_parent.mkdir(parents=True, exist_ok=True)
    row = build_rlvr_row(train_record, dataset_root=dataset_root, output_parent=export_parent, prompt_variant='answer_only', image_path_mode='relative')
    assert row['uid'] == 'inst-001'
    assert row['instance_id'] == 'inst-001'
    assert row['domain'] == 'geometry'
    assert row['scene_id'] == 'coordinate_plane'
    assert row['query_id'] == 'perpendicular_count'
    assert row['prompt'] == '<image>Count the marked dots.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"answer":3}'
    assert row['prompt_answer_only'] == '<image>Count the marked dots.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"answer":3}'
    assert row['prompt_answer_and_annotation'] == '<image>Count the marked dots and cite the supporting positions.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'
    assert row['prompt_active'] == '<image>active prompt'
    assert row['prompt_mode'] == 'answer_only'
    assert row['images'] == [{'path': '../../trace_dataset/images/geometry/task_geometry__coordinate_plane__segment_relation_count/000000.png'}]
    assert row['answer_gt'] == train_record['answer_gt']
    assert row['annotation_gt'] == train_record['annotation_gt']
    assert row['reward_contract'] == train_record['reward_contract']

def test_build_rlvr_row_normalizes_existing_image_placeholders(tmp_path: Path) -> None:
    dataset_root, train_record = _write_trace_dataset(tmp_path)
    train_record['prompt_variants']['answer_and_annotation'] = '<image>   Count the marked dots and cite the supporting positions.\nUse a valid JSON object with keys "annotation" and "answer" in that order for the final answer.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'
    export_parent = tmp_path / 'exports' / 'jsonl'
    export_parent.mkdir(parents=True, exist_ok=True)
    row = build_rlvr_row(train_record, dataset_root=dataset_root, output_parent=export_parent, prompt_variant='answer_and_annotation', image_path_mode='relative')
    assert row['prompt'] == '<image>Count the marked dots and cite the supporting positions.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'

def test_build_rlvr_row_accepts_annotation_prompt_alias(tmp_path: Path) -> None:
    dataset_root, train_record = _write_trace_dataset(tmp_path)
    export_parent = tmp_path / 'exports' / 'jsonl'
    export_parent.mkdir(parents=True, exist_ok=True)
    row = build_rlvr_row(train_record, dataset_root=dataset_root, output_parent=export_parent, prompt_variant='annotation', image_path_mode='relative')
    assert row['prompt_mode'] == 'answer_and_annotation'
    assert row['prompt'] == row['prompt_answer_and_annotation']

def test_export_trace_dataset_to_rlvr_jsonl_and_parquet(tmp_path: Path) -> None:
    dataset_root, _ = _write_trace_dataset(tmp_path)
    jsonl_path = tmp_path / 'rlvr_jsonl'
    jsonl_result = export_trace_dataset_to_rlvr(dataset_root, jsonl_path, prompt_variant='answer_and_annotation', image_path_mode='relative')
    assert jsonl_result.output_path.name == 'train.jsonl'
    jsonl_rows = [json.loads(line) for line in jsonl_result.output_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(jsonl_rows) == 1
    assert jsonl_rows[0]['prompt'] == '<image>Count the marked dots and cite the supporting positions.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'
    assert jsonl_rows[0]['prompt_answer_only'] == '<image>Count the marked dots.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"answer":3}'
    assert jsonl_rows[0]['prompt_answer_and_annotation'] == '<image>Count the marked dots and cite the supporting positions.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'
    assert jsonl_rows[0]['difficulty_bin'] == 0
    assert jsonl_rows[0]['bucket_id_str'] == 'task_geometry__coordinate_plane__segment_relation_count::q0'
    assert jsonl_rows[0]['images'] == [{'path': '../trace_dataset/images/geometry/task_geometry__coordinate_plane__segment_relation_count/000000.png'}]
    parquet_path = tmp_path / 'exports' / 'trace_train.parquet'
    parquet_result = export_trace_dataset_to_rlvr(dataset_root, parquet_path, output_format='parquet', prompt_variant='active', image_path_mode='absolute', parquet_cpu_count=1)
    assert parquet_result.output_path == parquet_path.resolve()
    table = pq.read_table(parquet_result.output_path)
    parquet_rows = table.to_pylist()
    assert len(parquet_rows) == 1
    assert parquet_rows[0]['prompt'] == '<image>active prompt'
    assert parquet_rows[0]['prompt_answer_only'] == '<image>Count the marked dots.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"answer":3}'
    assert parquet_rows[0]['prompt_answer_and_annotation'] == '<image>Count the marked dots and cite the supporting positions.\nRequired annotation format: set "annotation" to the supporting point list.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"annotation":[[1,2]],"answer":3}'
    assert parquet_rows[0]['difficulty_bin'] == 0
    assert parquet_rows[0]['bucket_id_str'] == 'task_geometry__coordinate_plane__segment_relation_count::q0'
    assert json.loads(parquet_rows[0]['answer_gt']) == {'type': 'integer', 'value': 3}
    assert json.loads(parquet_rows[0]['annotation_gt']) == {'type': 'point_set', 'value': [[1, 2], [3, 4], [5, 6]]}
    assert json.loads(parquet_rows[0]['reward_contract']) == {'reward_contract_version': 'v0', 'answer': {'id': 'answer_exact_match_v0', 'type': 'integer'}, 'annotation': {'id': 'point_set_soft_distance_v0', 'type': 'point_set'}}
    assert json.loads(parquet_rows[0]['trace_ref']) == {'shard_id': 'trace-0001', 'line_index': 0, 'trace_record_hash': 'trace-hash'}
    assert parquet_rows[0]['images'] == [{'path': str((dataset_root / 'images' / 'geometry' / 'task_geometry__coordinate_plane__segment_relation_count' / '000000.png').resolve())}]

def test_export_trace_dataset_to_rlvr_parquet_supports_embedded_images(tmp_path: Path) -> None:
    from datasets import load_dataset
    dataset_root, _ = _write_trace_dataset(tmp_path)
    parquet_path = tmp_path / 'exports' / 'trace_train_embedded.parquet'
    result = export_trace_dataset_to_rlvr(dataset_root, parquet_path, output_format='parquet', prompt_variant='answer_and_annotation', image_storage_mode='embedded_bytes', parquet_cpu_count=1)
    rows = pq.read_table(result.output_path).to_pylist()
    assert len(rows) == 1
    assert 'bytes' in rows[0]['images'][0]
    assert rows[0]['images'][0].get('path') is None
    assert isinstance(rows[0]['images'][0]['bytes'], (bytes, bytearray))
    loaded = load_dataset('parquet', data_files=str(result.output_path), split='train')
    loaded_row = loaded[0]
    assert loaded_row['prompt_answer_only'] == '<image>Count the marked dots.\nRequired answer format: set "answer" to the requested integer value.\nExample JSON:\n{"answer":3}'
    assert isinstance(loaded_row['images'][0], Image.Image)

def test_export_trace_dataset_to_rlvr_embedded_image_cap_scales_annotation(tmp_path: Path) -> None:
    from io import BytesIO
    dataset_root, train_record = _write_trace_dataset(tmp_path)
    image_path = dataset_root / 'images' / 'geometry' / 'task_geometry__coordinate_plane__segment_relation_count' / '000000.png'
    Image.new('RGB', (20, 10), (255, 255, 255)).save(image_path)
    train_record['annotation_gt'] = {'type': 'point_set', 'value': [[2, 4], [10, 8]]}
    (dataset_root / 'train_instances.jsonl').write_text(json.dumps(train_record) + '\n', encoding='utf-8')
    parquet_path = tmp_path / 'exports' / 'trace_train_embedded_resized.parquet'
    result = export_trace_dataset_to_rlvr(
        dataset_root,
        parquet_path,
        output_format='parquet',
        prompt_variant='answer_and_annotation',
        image_storage_mode='embedded_bytes',
        parquet_cpu_count=1,
        max_embedded_image_pixels=50,
    )
    rows = pq.read_table(result.output_path).to_pylist()
    assert len(rows) == 1
    resized = Image.open(BytesIO(rows[0]['images'][0]['bytes']))
    assert resized.size == (10, 5)
    assert rows[0]['image_sizes_original'] == [{'width': 20, 'height': 10}]
    assert rows[0]['image_sizes_exported'] == [{'width': 10, 'height': 5}]
    assert json.loads(rows[0]['annotation_gt']) == {'type': 'point_set', 'value': [[1.0, 2.0], [5.0, 4.0]]}

def test_export_trace_dataset_to_rlvr_parquet_supports_mixed_trace_contract_types(tmp_path: Path) -> None:
    dataset_root = tmp_path / 'trace_dataset_mixed'
    image_dir = dataset_root / 'images'
    image_dir.mkdir(parents=True, exist_ok=True)
    image_a = image_dir / 'a.png'
    image_b = image_dir / 'b.png'
    image_a.write_bytes(b'a')
    image_b.write_bytes(b'b')
    records = [{'instance_id': 'inst-a', 'domain': 'geometry', 'scene_id': 'coordinate', 'task': 'task_geometry__coordinate_plane__segment_relation_count', 'scene_id': 'coordinate_plane', 'query_id': '', 'prompt': 'prompt a', 'images': [{'path': 'images/a.png'}], 'answer_gt': {'type': 'integer', 'value': 3}, 'annotation_gt': {'type': 'point_set', 'value': [[1, 2], [3, 4]]}, 'reward_contract': {'reward_contract_version': 'v0', 'answer': {'id': 'answer_exact_match_v0', 'type': 'integer'}, 'annotation': {'id': 'point_set_soft_distance_v0', 'type': 'point_set'}}, 'trace_ref': {'shard_id': 'trace', 'line_index': 0, 'trace_record_hash': 'ha'}}, {'instance_id': 'inst-b', 'domain': 'puzzles', 'scene_id': 'raven_matrix', 'task': 'task_puzzles__raven_matrix__raven_count_progression_label', 'query_id': 'single', 'prompt': 'prompt b', 'images': [{'path': 'images/b.png'}], 'answer_gt': {'type': 'option_letter', 'value': 'C'}, 'annotation_gt': {'type': 'bbox', 'value': [10, 10, 20, 20]}, 'reward_contract': {'reward_contract_version': 'v0', 'answer': {'id': 'answer_exact_match_v0', 'type': 'option_letter'}, 'annotation': {'id': 'bbox_soft_iou_v0', 'type': 'bbox'}}, 'trace_ref': {'shard_id': 'trace', 'line_index': 1, 'trace_record_hash': 'hb'}}]
    (dataset_root / 'train_instances.jsonl').write_text('\n'.join((json.dumps(record) for record in records)) + '\n', encoding='utf-8')
    result = export_trace_dataset_to_rlvr(dataset_root, tmp_path / 'mixed.parquet', output_format='parquet', parquet_cpu_count=1)
    rows = pq.read_table(result.output_path).to_pylist()
    assert len(rows) == 2
    assert json.loads(rows[0]['answer_gt'])['type'] == 'integer'
    assert json.loads(rows[1]['answer_gt'])['type'] == 'option_letter'
    assert json.loads(rows[1]['answer_gt'])['value'] == 'C'

def test_export_trace_dataset_to_rlvr_adds_task_local_curriculum_buckets(tmp_path: Path) -> None:
    dataset_root = tmp_path / 'trace_dataset_multi'
    dataset_root.mkdir(parents=True, exist_ok=True)
    image_dir = dataset_root / 'images'
    image_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(1, 7):
        image_path = image_dir / f'a_{index:02d}.png'
        image_path.write_bytes(b'img')
        records.append({'instance_id': f'task-a-{index}', 'domain': 'games', 'scene_id': 'cards', 'task': 'task_games__cards__same_suit_as_reference_count', 'scene_id': 'cards', 'query_id': '', 'prompt': f'prompt {index}', 'images': [{'path': f'images/{image_path.name}'}], 'answer_gt': {'type': 'integer', 'value': index}, 'annotation_gt': {'type': 'bbox_set', 'value': []}, 'reward_contract': {'reward_contract_version': 'v0', 'answer': {'id': 'answer_exact_match_v0', 'type': 'integer'}, 'annotation': {'id': 'bbox_set_soft_iou_v0', 'type': 'bbox_set'}}, 'trace_ref': {'shard_id': 'trace', 'line_index': index, 'trace_record_hash': f'h{index}'}})
    for index in range(1, 4):
        image_path = image_dir / f'b_{index:02d}.png'
        image_path.write_bytes(b'img')
        records.append({'instance_id': f'task-b-{index}', 'domain': 'games', 'scene_id': 'dominoes', 'task': 'task_games__dominoes__double_count', 'scene_id': 'dominoes', 'query_id': '', 'prompt': f'prompt-b {index}', 'images': [{'path': f'images/{image_path.name}'}], 'answer_gt': {'type': 'integer', 'value': index}, 'annotation_gt': {'type': 'bbox_set', 'value': []}, 'reward_contract': {'reward_contract_version': 'v0', 'answer': {'id': 'answer_exact_match_v0', 'type': 'integer'}, 'annotation': {'id': 'bbox_set_soft_iou_v0', 'type': 'bbox_set'}}, 'trace_ref': {'shard_id': 'trace', 'line_index': 100 + index, 'trace_record_hash': f'hb{index}'}})
    (dataset_root / 'train_instances.jsonl').write_text('\n'.join((json.dumps(record) for record in records)) + '\n', encoding='utf-8')
    result = export_trace_dataset_to_rlvr(dataset_root, tmp_path / 'out.jsonl')
    rows = [json.loads(line) for line in result.output_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    rows_by_id = {row['instance_id']: row for row in rows}
    assert {rows_by_id[f'task-a-{index}']['bucket_id_str'] for index in (1, 2)} == {'task_games__cards__same_suit_as_reference_count::q0'}
    assert {rows_by_id[f'task-a-{index}']['bucket_id_str'] for index in (3, 4, 5, 6)} == {'task_games__cards__same_suit_as_reference_count::q0'}
    assert rows_by_id['task-b-1']['bucket_id_str'] == 'task_games__dominoes__double_count::q0'
    assert rows_by_id['task-b-2']['bucket_id_str'] == 'task_games__dominoes__double_count::q0'
    assert rows_by_id['task-b-3']['bucket_id_str'] == 'task_games__dominoes__double_count::q0'
    assert rows_by_id['task-b-1']['difficulty_bin'] == 0
    assert rows_by_id['task-b-3']['difficulty_bin'] == 0
