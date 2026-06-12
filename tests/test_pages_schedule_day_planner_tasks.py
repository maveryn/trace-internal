"""Behavior tests for the day-planner schedule task."""
from __future__ import annotations
from collections import Counter, defaultdict
from itertools import combinations
from trace.core.seed import hash64
from trace.tasks.pages.schedule.day_planner import PagesScheduleLongerThanReferenceCountTask, PagesScheduleMaximumNonOverlappingCountTask, PagesScheduleOverlapCountTask
from trace.tasks.shared.time_artifact_style import SUPPORTED_TIME_ARTIFACT_COLOR_NAMES, SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS
from tests.helpers import extract_prompt_json_example

def _intervals_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    """Return whether two half-open slot intervals overlap."""
    return bool(int(left[0]) < int(right[1]) and int(right[0]) < int(left[1]))

def _maximum_non_overlapping_subsets(events: list[dict[str, object]]) -> tuple[int, list[tuple[str, ...]]]:
    """Return the maximum compatible subset size and every optimum subset."""
    event_ids = [str(event['event_id']) for event in events]
    intervals = {str(event['event_id']): (int(event['start_slot']), int(event['end_slot'])) for event in events}
    best_size = 0
    best_subsets: list[tuple[str, ...]] = []
    for subset_size in range(1, len(event_ids) + 1):
        for subset in combinations(event_ids, subset_size):
            if any((_intervals_overlap(intervals[left], intervals[right]) for left, right in combinations(subset, 2))):
                continue
            if int(subset_size) > int(best_size):
                best_size = int(subset_size)
                best_subsets = [tuple(sorted(subset))]
            elif int(subset_size) == int(best_size):
                best_subsets.append(tuple(sorted(subset)))
    return (int(best_size), sorted(set((tuple(subset) for subset in best_subsets))))

def test_pages_schedule_day_planner_contract_matches_trace() -> None:
    task_cases = ((PagesScheduleOverlapCountTask(), 'overlap_count'), (PagesScheduleLongerThanReferenceCountTask(), 'longer_than_reference_count'), (PagesScheduleMaximumNonOverlappingCountTask(), 'maximum_non_overlapping_count'))
    scene_variants = ('classic', 'outline')
    style_variants = ('studio', 'marker')
    accent_colors = ('blue', 'orange')

def test_pages_schedule_day_planner_prompt_examples_match_variants() -> None:
    expected = ((PagesScheduleOverlapCountTask(), 'overlap_count', ({'annotation': [[250, 276, 396, 366], [404, 318, 550, 438]], 'answer': 2}, {'answer': 2})), (PagesScheduleLongerThanReferenceCountTask(), 'longer_than_reference_count', ({'annotation': [[250, 240, 396, 408], [404, 430, 550, 634], [558, 352, 704, 568]], 'answer': 3}, {'answer': 3})), (PagesScheduleMaximumNonOverlappingCountTask(), 'maximum_non_overlapping_count', ({'annotation': [[250, 220, 396, 316], [404, 316, 550, 412], [558, 412, 704, 508], [250, 508, 396, 604]], 'answer': 4}, {'answer': 4})))
    for index, (task, query_id, (expected_answer_and_annotation, expected_answer_only)) in enumerate(expected, start=22110):
        out = task.generate(index, params={'query_id': query_id}, max_attempts=20)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants['answer_and_annotation'])
        answer_only = extract_prompt_json_example(out.prompt_variants['answer_only'])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only

def test_pages_schedule_day_planner_balanced_sampling_defaults_cover_axes() -> None:
    tasks = (PagesScheduleOverlapCountTask(), PagesScheduleLongerThanReferenceCountTask(), PagesScheduleMaximumNonOverlappingCountTask())
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    lane_counts: Counter[int] = Counter()
    scenes_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    styles_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    answers_by_query_id: defaultdict[str, Counter[int]] = defaultdict(Counter)
    for task in tasks:
        for index in range(90):
            out = task.generate(hash64(22140, task.task_id, index), params={}, max_attempts=20)
            execution = out.trace_payload['execution_trace']
            query_id = str(execution['source_query_id'])
            scene_variant = str(execution['scene_variant'])
            style_variant = str(execution['style_variant'])
            query_ids[query_id] += 1
            scene_variants[str(execution['scene_variant'])] += 1
            style_variants[style_variant] += 1
            accent_color_names[str(execution['accent_color_name'])] += 1
            lane_counts[int(execution['lane_count'])] += 1
            scenes_by_query_id[query_id][scene_variant] += 1
            styles_by_query_id[query_id][style_variant] += 1
            answers_by_query_id[query_id][int(out.answer_gt.value)] += 1
    assert set(query_ids.keys()) == {'overlap_count', 'longer_than_reference_count', 'maximum_non_overlapping_count'}
    assert set(scene_variants.keys()) == {'classic', 'minimal', 'outline'}
    assert set(style_variants.keys()) == set(SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TIME_ARTIFACT_COLOR_NAMES)
    assert set(lane_counts.keys()).issubset({1, 2, 3, 4, 5})
    for query_id in query_ids:
        assert set(scenes_by_query_id[query_id].keys()) == {'classic', 'minimal', 'outline'}
        assert set(styles_by_query_id[query_id].keys()) == set(SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS)
        assert len(answers_by_query_id[query_id]) >= 5
