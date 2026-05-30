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
    (AGENT_FINAL_TASK_ID, PuzzlesAutomatonAgentFinalPoseLabelTask, AGENT_SCENE_ID, set(AGENT_FINAL_QUERY_IDS), "option_letter", "keyed_bbox_map"),
    (AGENT_FLIP_TASK_ID, PuzzlesAutomatonAgentCellFlipCountTask, AGENT_SCENE_ID, set(AGENT_FLIP_QUERY_IDS), "integer", "bbox_set"),
    (LIFE_GRID_TASK_ID, PuzzlesAutomatonLifeFutureGridLabelTask, LIFE_SCENE_ID, set(LIFE_GRID_QUERY_IDS), "option_letter", "keyed_bbox_map"),
    (LIFE_POP_TASK_ID, PuzzlesAutomatonLifePopulationCountTask, LIFE_SCENE_ID, set(LIFE_POP_QUERY_IDS), "integer", "bbox_set"),
    (TURING_SYMBOL_COUNT_TASK_ID, PuzzlesAutomatonTuringWrittenSymbolCountTask, TURING_SCENE_ID, set(TURING_QUERY_IDS), "integer", "bbox_set"),
)


def test_automaton_tasks_are_registered() -> None:
    for task_id, task_cls, _scene_id, _queries, _answer_type, _evidence_type in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "automaton"


def test_automaton_tasks_emit_contracts() -> None:
    for index, (_task_id, task_cls, scene_id, queries, answer_type, evidence_type) in enumerate(TASKS):
        out = task_cls().generate(2026052200 + index, params={}, max_attempts=30)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == scene_id
        assert out.query_id in queries
        assert out.answer_gt.type == answer_type
        assert out.evidence_gt.type == evidence_type
        assert trace["query_spec"]["params"]["query_id"] == out.query_id
        assert trace["render_spec"]["scene_id"] == scene_id
        assert trace["render_map"]["evidence_source"] == "item_bboxes_px"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["projected_evidence"][evidence_type] == out.evidence_gt.value
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )
        assert execution["query_id"] == out.query_id
        assert execution["scene_id"] == scene_id
        assert execution["supporting_item_ids"]
        assert len(out.evidence_gt.value) == len(execution["supporting_item_ids"])
        if _task_id == AGENT_FINAL_TASK_ID:
            assert execution["supporting_item_ids_by_role"]["start_marker"] == "initial_agent"
            assert execution["supporting_item_ids_by_role"]["selected_option"].startswith("option_")
            assert set(out.evidence_gt.value) == {"start_marker", "selected_option"}
        if _task_id == LIFE_GRID_TASK_ID:
            assert execution["supporting_item_ids_by_role"]["source_grid"] == "source_grid"
            assert execution["supporting_item_ids_by_role"]["selected_option"].startswith("option_")
            assert set(out.evidence_gt.value) == {"source_grid", "selected_option"}
            render_params = trace["render_spec"]["render_params"]
            assert int(render_params["option_grid_cell_px"]) == int(render_params["cell_size_px"])
        if _task_id == AGENT_FLIP_TASK_ID:
            assert execution["supporting_item_ids"] == ["marked_region"]
        if scene_id in {AGENT_SCENE_ID, LIFE_SCENE_ID}:
            assert trace["render_spec"]["scene_style"]["font"]["source"] == "global_font_pool"
            assert trace["render_spec"]["scene_style"]["font"]["font_family"]
        if scene_id == AGENT_SCENE_ID:
            agent_board = trace["render_spec"]["scene_style"]["agent_board"]
            assert agent_board["board_style"] in {
                "classic_grid",
                "rounded_tiles",
                "inset_cells",
                "lab_matrix",
                "notebook_cells",
            }
            assert agent_board["semantic_color_policy"]["state_colors_preserved_from_scene_style"] is True
        if scene_id == LIFE_SCENE_ID:
            assert trace["render_spec"]["layout_jitter"]["enabled"] is True
            life_board = trace["render_spec"]["scene_style"]["life_board"]
            assert life_board["board_style"] in {
                "classic_grid",
                "rounded_tiles",
                "inset_tiles",
                "lab_matrix",
                "notebook_cells",
                "terminal_cells",
            }
            assert life_board["cell_palette_id"]
            assert life_board["semantic_color_policy"]["alive_cells_remain_dark"] is True
            assert life_board["semantic_color_policy"]["empty_cells_remain_light"] is True
            assert life_board["contrast_checks"]["alive_dead_pass"] is True
            assert life_board["contrast_checks"]["mark_pass"] is True
        bboxes = out.evidence_gt.value.values() if evidence_type == "keyed_bbox_map" else out.evidence_gt.value
        for bbox in bboxes:
            assert len(bbox) == 4
            assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
            assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_automaton_generation_is_deterministic() -> None:
    task = PuzzlesAutomatonAgentCellFlipCountTask()
    params = {
        "scene_variant": "lab_panel",
        "query_id": "marked_region_flip_count",
        "rule_variant": "three_state_rule",
    }
    out_a = task.generate(2026052299, params=params, max_attempts=30)
    out_b = task.generate(2026052299, params=params, max_attempts=30)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
