"""Contract tests for illustration counterfactual visible-part counting."""
from __future__ import annotations
from collections import Counter
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.illustrations.single_object_figure.visible_part_count import AIRPLANE_VARIANT, BACKGROUND_STYLES, BICYCLE_VARIANT, BIRD_VARIANT, BUTTERFLY_VARIANT, CHAIR_VARIANT, CLOVER_VARIANT, FORK_VARIANT, GLOVE_VARIANT, OBJECT_TYPE_BY_QUERY_ID, QUADRUPED_VARIANT, SNOWFLAKE_VARIANT, STAR_VARIANT, SUPPORTED_QUERY_IDS, TASK_ID, TRAFFIC_LIGHT_VARIANT

def test_illustrations_counterfactual_visible_part_count_is_registered() -> None:
    task = TASK_REGISTRY[TASK_ID]()
    assert task.domain == 'illustrations'
    assert not hasattr(task, 'scene_id')
    assert task.default_dataset_enabled is True

def test_illustrations_counterfactual_visible_part_count_contracts_match_trace() -> None:
    cases = [(BIRD_VARIANT, 5, 2, 'leg'), (QUADRUPED_VARIANT, 6, 4, 'leg'), (AIRPLANE_VARIANT, 4, 2, 'wing'), (BUTTERFLY_VARIANT, 6, 4, 'wing'), (BICYCLE_VARIANT, 5, 2, 'wheel'), (TRAFFIC_LIGHT_VARIANT, 5, 3, 'lens'), (CLOVER_VARIANT, 6, 3, 'leaf'), (STAR_VARIANT, 8, 5, 'point'), (GLOVE_VARIANT, 7, 5, 'finger'), (FORK_VARIANT, 6, 4, 'tine'), (SNOWFLAKE_VARIANT, 8, 6, 'arm'), (CHAIR_VARIANT, 6, 4, 'leg')]
    task = create_task(TASK_ID)

def test_illustrations_counterfactual_visible_part_count_sampling_balances_variants() -> None:
    task = create_task(TASK_ID)
    variants = Counter()
    answers = Counter()
    for index in range(240):
        out = task.generate(2026052700 + index, params={}, max_attempts=20)
        variants[str(out.query_id)] += 1
        answers[int(out.answer_gt.value)] += 1
    assert set(variants) == set(SUPPORTED_QUERY_IDS)
    assert min(variants.values()) >= 8
    assert max(variants.values()) <= 32
    assert set(answers) == {1, 2, 3, 4, 5, 6, 7, 8}
    assert max(answers.values()) <= 70
