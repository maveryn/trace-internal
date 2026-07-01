from __future__ import annotations

import sys
from pathlib import Path

from scripts.inventory_scalar_annotations import (
    TaskRef,
    build_inventory,
    classify_annotation_contract,
    classify_scalar_annotation_task_docs,
    parse_active_inventory,
    parse_doc_annotation_type,
    scalar_annotation_review_failures_for_tasks,
)


def test_parse_active_inventory_extracts_domain_scene_tasks() -> None:
    text = """# Active Task Inventory

## Tasks By Domain And Scene

### charts

#### error_interval (2)

- `task_charts__error_interval__interval_width_rank_label`
- `task_charts__error_interval__reference_containment_count`

### games

#### 2048 (1)

- `task_games__2048__max_tile_value`
"""

    assert parse_active_inventory(text) == [
        TaskRef("charts", "error_interval", "task_charts__error_interval__interval_width_rank_label"),
        TaskRef("charts", "error_interval", "task_charts__error_interval__reference_containment_count"),
        TaskRef("games", "2048", "task_games__2048__max_tile_value"),
    ]


def test_classify_scalar_point_candidate_from_one_witness_point_set() -> None:
    doc_text = """
Answer schema: `string_label`
Annotation schema: `point_set`

The annotation marks one pixel point at the selected interval center.

## Program Contract
annotation_gt = point_set(selected_interval_center)
"""

    classification, rationale, sources = classify_annotation_contract(
        task_id="task_charts__error_interval__interval_width_rank_label",
        annotation_type="point_set",
        doc_text=doc_text,
    )

    assert classification == "scalar_point_candidate"
    assert "migrate to `point`" in rationale
    assert sources == ["doc"]


def test_classify_count_task_stays_set() -> None:
    doc_text = """
Answer schema: `integer`
Annotation schema: `bbox_set`

The annotation marks every qualifying bar.

## Program Contract
answer = count(filter(bars, above_threshold))
annotation_gt = bbox_set(matching_bars)
"""

    classification, _, _ = classify_annotation_contract(
        task_id="task_charts__bar_3d__category_threshold_count",
        annotation_type="bbox_set",
        doc_text=doc_text,
    )

    assert classification == "stay_set_or_sequence"


def test_classify_scalar_segment_candidate_from_one_witness_segment_set() -> None:
    doc_text = """
Answer schema: `string_label`
Annotation schema: `segment_set`

The annotation marks exactly one visual edge segment for the selected path.

## Program Contract
annotation_gt = segment_set(selected_path_edge)
"""

    classification, rationale, sources = classify_annotation_contract(
        task_id="task_graph__node_link__selected_edge_label",
        annotation_type="segment_set",
        doc_text=doc_text,
    )

    assert classification == "scalar_segment_candidate"
    assert "migrate to `segment`" in rationale
    assert sources == ["doc"]


def test_classify_scalar_segment_is_already_scalar() -> None:
    classification, rationale, sources = classify_annotation_contract(
        task_id="task_charts__dumbbell__gap_rank_row_label",
        annotation_type="segment",
        doc_text="Annotation schema: `segment`\n",
    )

    assert classification == "already_scalar"
    assert "scalar `segment`" in rationale
    assert sources == ["doc"]


def test_classify_multi_witness_doc_stays_set_even_with_unique_answer() -> None:
    doc_text = """
Answer schema: `label_string`
Annotation schema: `point_set`

The scene has exactly one matching answer column.
Annotation marks the centers of every disc in the selected column.
"""

    classification, rationale, _ = classify_annotation_contract(
        task_id="task_games__connect_four__column_disc_profile_label",
        annotation_type="point_set",
        doc_text=doc_text,
    )

    assert classification == "stay_set_or_sequence"
    assert "multiple annotation witnesses" in rationale


def test_parse_doc_annotation_type_prefers_backticked_registry_type() -> None:
    doc_text = """
- Annotation type: one-box `bbox_set`

## Annotation Contract
Annotation is a `bbox_set` containing the selected object.
"""

    assert parse_doc_annotation_type(doc_text) == "bbox_set"


def test_classify_single_keyed_map_needs_manual_decision_without_role_hints() -> None:
    doc_text = """
Answer schema: `string_label`
Annotation schema: `point_map`

The annotation marks the selected boxplot midpoint.

## Program Contract
annotation_gt = point_map(answer_boxplot)
"""

    classification, rationale, _ = classify_annotation_contract(
        task_id="task_charts__boxplot__iqr_extremum_label",
        annotation_type="point_map",
        doc_text=doc_text,
    )

    assert classification == "needs_manual_decision"


def test_scalar_annotation_review_helper_reports_remaining_scalar_candidate(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "tasks"
    task_id = "task_charts__error_interval__interval_width_rank_label"
    doc_path = docs_root / "charts" / "error_interval" / f"{task_id}.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text(
        """
Answer schema: `string_label`
Annotation schema: `point_set`

The annotation marks one pixel point at the selected interval center.

## Program Contract
annotation_gt = point_set(selected_interval_center); scene=error_interval; scope=interval_width_rank_label
""",
        encoding="utf-8",
    )

    records = classify_scalar_annotation_task_docs(
        domain="charts",
        scene_id="error_interval",
        task_ids=[task_id],
        docs_root=docs_root,
    )
    failures = scalar_annotation_review_failures_for_tasks(
        domain="charts",
        scene_id="error_interval",
        task_ids=[task_id],
        docs_root=docs_root,
    )

    assert records[0]["classification"] == "scalar_point_candidate"
    assert "migrate to `point`" in records[0]["rationale"]
    assert len(failures) == 1
    assert "scalar_point_candidate" in failures[0]


def test_build_inventory_static_path_does_not_import_global_tasks(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    docs_root = Path("docs")
    task_doc_dir = docs_root / "tasks" / "charts" / "error_interval"
    task_doc_dir.mkdir(parents=True)
    inventory_path = docs_root / "ACTIVE_TASK_INVENTORY.md"
    task_id = "task_charts__error_interval__interval_width_rank_label"
    inventory_path.write_text(
        f"""# Active Task Inventory

## Tasks By Domain And Scene

### charts

#### error_interval (1)

- `{task_id}`
""",
        encoding="utf-8",
    )
    (task_doc_dir / f"{task_id}.md").write_text(
        """# Task

Answer schema: `string_label`
Annotation schema: `point_set`

The annotation marks one pixel point at the selected interval center.
""",
        encoding="utf-8",
    )

    for module_name in list(sys.modules):
        if module_name == "trace.tasks" or module_name.startswith("trace.tasks."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)

    class PoisonedTraceTasks:
        pass

    monkeypatch.setitem(sys.modules, "trace.tasks", PoisonedTraceTasks())

    inventory = build_inventory(active_inventory_path=inventory_path, smoke_samples=0)

    assert inventory["total_tasks"] == 1
    [record] = inventory["records"]
    assert record["generated_ok"] is None
    assert record["classification"] == "scalar_point_candidate"
