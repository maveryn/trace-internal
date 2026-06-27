from __future__ import annotations

from pathlib import Path

from scripts.audit_semantic_sampling_modulo import (
    group_findings,
    render_markdown,
    scan_source_text,
)


def _categories(source: str, path: str = "trace/tasks/demo_scene/task.py") -> list[str]:
    return [
        finding.category
        for finding in scan_source_text(Path(path), source)
    ]


def test_audit_flags_seed_modulo_semantic_sampling() -> None:
    source = """
RELATIONS = ("left", "right", "balanced")
target_relation = RELATIONS[int(instance_seed) % len(RELATIONS)]
answer = target_relation
"""

    assert _categories(source) == ["needs_refactor"]


def test_audit_flags_selection_index_modulo_when_semantic() -> None:
    source = """
support = ["A", "B", "C"]
selection_index = resolve_selection_index(params=params, support=support)
target = support[int(selection_index) % len(support)]
"""

    assert _categories(source) == [
        "needs_refactor",
        "needs_refactor",
    ]


def test_audit_allows_visual_cyclic_enumeration() -> None:
    source = """
COLORS = ["red", "blue", "green"]
color = COLORS[index % len(COLORS)]
"""

    assert _categories(source) == ["allowed_deterministic_enumeration"]


def test_audit_flags_correct_option_label_modulo() -> None:
    source = """
OPTION_LABELS = ("A", "B", "C", "D")
correct_option_index = int(instance_seed) % len(OPTION_LABELS)
answer_label = OPTION_LABELS[correct_option_index]
"""

    assert _categories(source) == ["needs_refactor"]


def test_audit_groups_selection_index_and_modulo_as_one_site() -> None:
    source = """
support = ["A", "B", "C"]
selection_index = resolve_selection_index(params=params, support=support)
target = support[int(selection_index) % len(support)]
"""

    sites = group_findings(scan_source_text(Path("trace/tasks/demo_scene/task.py"), source))

    assert len(sites) == 1
    assert sites[0].category == "needs_refactor"
    assert sites[0].kind == "resolve_selection_index_support_modulo"
    assert sites[0].raw_findings == 2


def test_audit_groups_same_line_selection_index_modulo_as_one_site() -> None:
    source = """
index = resolve_selection_index(params=params, instance_seed=seed, namespace="x") % len(support)
selected = support[index]
"""

    sites = group_findings(scan_source_text(Path("trace/tasks/demo_scene/task.py"), source))

    assert len(sites) == 1
    assert sites[0].category == "needs_refactor"
    assert sites[0].kind == "resolve_selection_index_support_modulo"
    assert sites[0].raw_findings == 2


def test_audit_separates_review_harness_round_robin() -> None:
    source = """
query_id_value = str(pending_query_ids[int(query_id_index) % len(pending_query_ids)])
"""

    assert _categories(source, "trace/core/task_review_sampling.py") == [
        "review_stratification_or_round_robin"
    ]


def test_audit_allows_known_review_overlay_paths() -> None:
    source = """
template = TEMPLATES[index % len(TEMPLATES)]
"""

    assert _categories(source, "trace/core/review_overlays.py") == [
        "allowed_deterministic_enumeration"
    ]


def test_audit_allows_part_whole_circular_category_traversal() -> None:
    source = """
target_index = (int(source_index) + int(step)) % len(categories)
"""

    assert _categories(source, "trace/tasks/charts/part_whole/shared/sampling.py") == [
        "allowed_deterministic_enumeration"
    ]


def test_audit_allows_surface_3d_palette_assignment() -> None:
    source = """
color_rgb=PALETTE[int(series_index) % len(PALETTE)]
"""

    assert _categories(source, "trace/tasks/charts/surface_3d/series_trend_label.py") == [
        "allowed_deterministic_enumeration"
    ]


def test_audit_allows_treemap_divisibility_validation() -> None:
    source = """
if total % len(matching) != 0:
    raise ValueError("not divisible")
"""

    assert _categories(source, "trace/tasks/charts/treemap/repeated_leaf_aggregate_value.py") == [
        "allowed_deterministic_enumeration"
    ]


def test_audit_allows_ludo_path_wraparound() -> None:
    source = """
target_index = (mover_index + distance) % len(MAIN_PATH)
"""

    assert _categories(source, "trace/tasks/games/ludo_board/capture_roll_option_label.py") == [
        "allowed_deterministic_enumeration"
    ]


def test_audit_allows_mancala_sowing_wraparound() -> None:
    source = """
source_index = (int(target_index) - int(source_seed_count)) % len(LABELS)
"""

    assert _categories(source, "trace/tasks/games/mancala_pit_board/sowing_landing_option_label.py") == [
        "allowed_deterministic_enumeration"
    ]


def test_render_markdown_summarizes_findings() -> None:
    findings = scan_source_text(
        Path("trace/tasks/demo_scene/task.py"),
        """
target_answer = ANSWERS[int(instance_seed) % len(ANSWERS)]
""",
    )

    report = render_markdown(findings)

    assert "Needs refactor: 1" in report
    assert "Grouped selection sites: 1" in report
    assert "task.py" in report
