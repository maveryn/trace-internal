"""Contract tests for automaton puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.automaton.cellular_automaton import (
    AGENT_FINAL_QUERY_IDS,
    AGENT_FINAL_TASK_ID,
    AGENT_FLIP_QUERY_IDS,
    AGENT_FLIP_TASK_ID,
    AGENT_SCENE_ID,
    LIFE_GRID_QUERY_IDS,
    LIFE_GRID_TASK_ID,
    LIFE_POP_QUERY_IDS,
    LIFE_POP_TASK_ID,
    LIFE_SCENE_ID,
    TURING_QUERY_IDS,
    TURING_SCENE_ID,
    TURING_SYMBOL_COUNT_TASK_ID,
    PuzzlesAutomatonAgentCellFlipCountTask,
    PuzzlesAutomatonAgentFinalPoseLabelTask,
    PuzzlesAutomatonLifeFutureGridLabelTask,
    PuzzlesAutomatonLifePopulationCountTask,
    PuzzlesAutomatonTuringWrittenSymbolCountTask,
)


TASKS = (
    (AGENT_FINAL_TASK_ID, PuzzlesAutomatonAgentFinalPoseLabelTask, AGENT_SCENE_ID, set(AGENT_FINAL_QUERY_IDS), "option_letter"),
    (AGENT_FLIP_TASK_ID, PuzzlesAutomatonAgentCellFlipCountTask, AGENT_SCENE_ID, set(AGENT_FLIP_QUERY_IDS), "integer"),
    (LIFE_GRID_TASK_ID, PuzzlesAutomatonLifeFutureGridLabelTask, LIFE_SCENE_ID, set(LIFE_GRID_QUERY_IDS), "option_letter"),
    (LIFE_POP_TASK_ID, PuzzlesAutomatonLifePopulationCountTask, LIFE_SCENE_ID, set(LIFE_POP_QUERY_IDS), "integer"),
    (TURING_SYMBOL_COUNT_TASK_ID, PuzzlesAutomatonTuringWrittenSymbolCountTask, TURING_SCENE_ID, set(TURING_QUERY_IDS), "integer"),
)


def test_automaton_tasks_are_registered() -> None:
    for task_id, task_cls, _scene_id, _queries, _answer_type in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "automaton"


def test_automaton_tasks_emit_contracts() -> None:
    for index, (_task_id, task_cls, scene_id, queries, answer_type) in enumerate(TASKS):
        out = task_cls().generate(2026052200 + index, params={}, max_attempts=30)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == scene_id
        assert out.query_variant == "default"
        assert out.query_id in queries
        assert out.answer_gt.type == answer_type
        assert out.evidence_gt.type == "bbox_set"
        assert trace["query_spec"]["params"]["query_variant"] == "default"
        assert trace["query_spec"]["params"]["query_id"] == out.query_id
        assert trace["render_spec"]["scene_id"] == scene_id
        assert trace["render_map"]["evidence_source"] == "item_bboxes_px"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )
        assert execution["query_variant"] == "default"
        assert execution["query_id"] == out.query_id
        assert execution["scene_id"] == scene_id
        assert execution["supporting_item_ids"]
        assert len(out.evidence_gt.value) == len(execution["supporting_item_ids"])
        for bbox in out.evidence_gt.value:
            assert len(bbox) == 4
            assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
            assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_automaton_generation_is_deterministic() -> None:
    task = PuzzlesAutomatonAgentCellFlipCountTask()
    params = {
        "scene_variant": "lab_panel",
        "query_variant": "marked_region_flip_count",
        "rule_variant": "three_state_rule",
    }
    out_a = task.generate(2026052299, params=params, max_attempts=30)
    out_b = task.generate(2026052299, params=params, max_attempts=30)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
