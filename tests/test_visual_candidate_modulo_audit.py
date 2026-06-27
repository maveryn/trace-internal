from __future__ import annotations

from pathlib import Path

from scripts.audit_visual_candidate_modulo import scan_source_text


def _categories(source: str, path: str) -> list[str]:
    return [site.category for site in scan_source_text(Path(path), source)]


def test_audit_flags_seed_based_visual_candidate_selection() -> None:
    source = """
accent_rgb = accent_palette[int(hash64(int(instance_seed), "needle", 0) % len(accent_palette))]
"""

    assert _categories(source, "trace/tasks/physics/meter/shared/rendering.py") == [
        "random_candidate_selection_needs_refactor"
    ]


def test_audit_flags_rng_plus_modulo_visual_candidate_selection() -> None:
    source = """
kind = OBSTACLE_KINDS[int((index + rng.randrange(len(OBSTACLE_KINDS))) % len(OBSTACLE_KINDS))]
"""

    assert _categories(source, "trace/tasks/games/minigolf/shared/sampling.py") == [
        "random_candidate_selection_needs_refactor"
    ]


def test_audit_does_not_treat_neighboring_rng_setup_as_modulo_sampling() -> None:
    source = """
rng = spawn_rng(instance_seed, "scene.palette")
palette = [
    _as_rgb(item, DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)])
    for index, item in enumerate(raw_palette)
]
rng.shuffle(palette)
"""

    assert _categories(source, "trace/tasks/charts/area/shared/rendering.py") == [
        "likely_safe_deterministic_assignment"
    ]


def test_audit_marks_sampling_time_assignment_for_review() -> None:
    source = """
color_name = str(color_names[index % len(color_names)])
"""

    assert _categories(source, "trace/tasks/three_d/carousel/shared/sampling.py") == [
        "sampling_assignment_needs_review"
    ]


def test_audit_allows_rendering_assignment_cycle() -> None:
    source = """
fill = theme.brick_palette_rgb[int(brick.color_index) % len(theme.brick_palette_rgb)]
"""

    assert _categories(source, "trace/tasks/games/brick_breaker/shared/rendering.py") == [
        "likely_safe_deterministic_assignment"
    ]


def test_audit_ignores_part_whole_circular_category_traversal() -> None:
    source = """
target_index = (int(source_index) + int(step)) % len(categories)
"""

    assert _categories(source, "trace/tasks/charts/part_whole/shared/sampling.py") == []


def test_audit_allows_surface_3d_palette_assignment() -> None:
    source = """
color_rgb=PALETTE[int(series_index) % len(PALETTE)]
"""

    assert _categories(source, "trace/tasks/charts/surface_3d/series_trend_label.py") == [
        "likely_safe_deterministic_assignment"
    ]


def test_audit_ignores_treemap_divisibility_validation() -> None:
    source = """
if total % len(matching) != 0:
    raise ValueError("not divisible")
"""

    assert _categories(source, "trace/tasks/charts/treemap/repeated_leaf_aggregate_value.py") == []


def test_audit_ignores_ludo_path_wraparound() -> None:
    source = """
target_index = (mover_index + distance) % len(MAIN_PATH)
"""

    assert _categories(source, "trace/tasks/games/ludo_board/capture_roll_option_label.py") == []


def test_audit_ignores_mancala_sowing_wraparound() -> None:
    source = """
source_index = (int(target_index) - int(source_seed_count)) % len(LABELS)
"""

    assert _categories(source, "trace/tasks/games/mancala_pit_board/sowing_landing_option_label.py") == []


def test_audit_ignores_mancala_pit_label_topology() -> None:
    source = """
return str(LABELS[int(index) % len(LABELS)])
"""

    assert _categories(source, "trace/tasks/games/mancala_pit_board/shared/rules.py") == []
