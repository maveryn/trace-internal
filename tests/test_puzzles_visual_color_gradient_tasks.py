from __future__ import annotations

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.visual.color_gradient_violation import (
    COMPLETION_QUERY_ID,
    COMPLETION_TASK_ID,
    QUERY_ID,
    SCENE_ID,
    TASK_ID,
    PuzzlesVisualColorGradientCompletionLabelTask,
    PuzzlesVisualColorGradientViolationCellLabelTask,
)


def test_color_gradient_violation_task_is_registered() -> None:
    assert TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(TASK_ID)
    assert taxonomy.domain == "puzzles"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "visual"


def test_color_gradient_violation_contract() -> None:
    task = PuzzlesVisualColorGradientViolationCellLabelTask()
    out = task.generate(
        int(hash64(20260521, TASK_ID, 0)),
        params={"grid_size_variant": "4x4", "answer_label": "K", "rule_variant": "column_hue_row_lightness"},
        max_attempts=20,
    )

    assert out.query_variant == "default"
    assert out.scene_id == SCENE_ID
    assert out.query_id == QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "K"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1

    trace = out.trace_payload["execution_trace"]
    assert trace["violation_cell_id"] == "cell_K"
    assert trace["answer_label"] == "K"
    assert trace["question_format"] == QUERY_ID
    assert len([cell for cell in trace["cells"] if cell["is_violation"]]) == 1
    assert trace["cells"][trace["violation_index"]]["expected_rgb"] != trace["cells"][trace["violation_index"]]["observed_rgb"]

    bbox = out.trace_payload["render_map"]["item_bboxes_px"]["cell_K"]
    assert out.evidence_gt.value == [[float(value) for value in bbox]]


def test_color_gradient_violation_is_deterministic() -> None:
    task = PuzzlesVisualColorGradientViolationCellLabelTask()
    seed = int(hash64(20260521, TASK_ID, 1))
    params = {
        "grid_size_variant": "3x3",
        "answer_label": "E",
        "rule_variant": "row_hue_column_lightness",
        "scene_variant": "swatch_notebook",
    }
    left = task.generate(seed, params=params, max_attempts=20)
    right = task.generate(seed, params=params, max_attempts=20)

    assert left.prompt == right.prompt
    assert left.answer_gt == right.answer_gt
    assert left.evidence_gt == right.evidence_gt
    assert left.trace_payload["execution_trace"] == right.trace_payload["execution_trace"]
    assert left.image.tobytes() == right.image.tobytes()


def test_color_gradient_completion_task_is_registered() -> None:
    assert COMPLETION_TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(COMPLETION_TASK_ID)
    assert taxonomy.domain == "puzzles"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "visual"


def test_color_gradient_completion_contract() -> None:
    task = PuzzlesVisualColorGradientCompletionLabelTask()
    out = task.generate(
        int(hash64(20260521, COMPLETION_TASK_ID, 0)),
        params={
            "sequence_length_variant": "6_cell",
            "option_count_variant": "5_options",
            "answer_label": "D",
            "missing_index": 3,
            "rule_variant": "hue_gradient",
        },
        max_attempts=20,
    )

    assert out.query_variant == "default"
    assert out.scene_id == SCENE_ID
    assert out.query_id == COMPLETION_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 2

    trace = out.trace_payload["execution_trace"]
    assert trace["missing_index"] == 3
    assert trace["answer_label"] == "D"
    assert trace["correct_option_id"] == "option_D"
    assert trace["question_format"] == COMPLETION_QUERY_ID
    assert len([option for option in trace["options"] if option["is_correct"]]) == 1

    item_bboxes = out.trace_payload["render_map"]["item_bboxes_px"]
    assert out.evidence_gt.value == [
        [float(value) for value in item_bboxes["sequence_cell_3"]],
        [float(value) for value in item_bboxes["option_D"]],
    ]


def test_color_gradient_completion_is_deterministic() -> None:
    task = PuzzlesVisualColorGradientCompletionLabelTask()
    seed = int(hash64(20260521, COMPLETION_TASK_ID, 1))
    params = {
        "sequence_length_variant": "7_cell",
        "option_count_variant": "6_options",
        "answer_label": "F",
        "rule_variant": "hue_lightness_gradient",
        "scene_variant": "swatch_card",
    }
    left = task.generate(seed, params=params, max_attempts=20)
    right = task.generate(seed, params=params, max_attempts=20)

    assert left.prompt == right.prompt
    assert left.answer_gt == right.answer_gt
    assert left.evidence_gt == right.evidence_gt
    assert left.trace_payload["execution_trace"] == right.trace_payload["execution_trace"]
    assert left.image.tobytes() == right.image.tobytes()
