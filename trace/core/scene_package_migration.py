"""Scene-package migration rollout helpers.

This module tracks source-routed scene-package candidates. It deliberately does
not expose a source-code "complete" registry: human review status belongs in the
review workspace, not in a Python allowlist that can be mistaken for acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re

MIGRATED_SCENE_PACKAGE_DOMAINS: frozenset[str] = frozenset()
MIGRATED_SCENE_PACKAGE_SCENES: dict[str, frozenset[str]] = {
    "charts": frozenset(
        {
            "annotated_series",
            "area",
            "bar_3d",
            "boxplot",
            "candlestick",
            "combo_mark",
            "composition_panels",
            "contour_density",
            "curve_panels",
            "dashboard",
            "density_curve",
            "dumbbell",
            "error_interval",
            "errorbar_series",
            "heatmap",
            "hexbin_density",
            "histogram",
            "matrix",
            "multiseries",
            "parallel_coords",
            "part_whole",
            "pictogram",
            "population_pyramid",
            "radar",
            "radial_progress",
            "radial_sankey",
            "region_map",
            "sankey",
            "scatter_cluster",
            "scatter_points",
            "scatter_readout",
            "scientific_axis_frame",
            "single_series",
            "size_encoding",
            "style_legend",
            "sunburst",
            "surface_3d",
            "table",
            "treemap",
            "uncertainty_band",
            "violin",
            "waterfall",
        }
    ),
    "games": frozenset(
        {
            "2048",
            "backgammon",
            "battleship",
            "bingo",
            "bowling",
            "brick_breaker",
            "bubble_shooter",
            "cards",
            "checkers",
            "chess",
            "chess_variant",
            "circular_chess",
            "connect_four",
            "crossing",
            "darts",
            "dominoes",
            "dots_and_boxes",
            "go",
            "hex",
            "irregular_link_board",
            "lane_runner",
            "ludo_board",
            "mancala_pit_board",
            "marble_chain",
            "match3",
            "minecraft",
            "minesweeper",
            "minigolf",
            "nine_mens_morris",
            "pacman",
            "pinball_table",
            "platformer",
            "pool",
            "racing_track",
            "radial_hunt_board",
            "reversi",
            "rhythm",
            "rule_override_board",
            "sixteen_soldiers",
            "sliding_block",
            "slot_machine",
            "snake",
            "snakes_ladders",
            "sokoban",
            "solitaire",
            "space_shooter",
            "tetris",
            "tic_tac_toe_3d",
            "tower_defense",
            "tower_draughts_board",
            "ultimate_tictactoe",
        }
    ),
    "geometry": frozenset(
        {
            "angle_relations",
            "area_partition",
            "bearing_route",
            "circle_centerline_overlap",
            "circle_pair_tangents",
            "circle_polygon_composite",
            "circle_theorem",
            "composite_shape",
            "concentric_chord",
            "cone_net",
            "container_volume_transfer",
            "coordinate_composite",
            "coordinate_conversion",
            "coordinate_panels",
            "coordinate_plane",
            "cuboid_views",
            "cylinder_wrap",
            "function_graph",
            "function_panels",
            "graph_paper",
            "incircle_tangents",
            "measuring_tools",
            "paper_fold",
            "polygon_equation_diagram",
            "pythagorean_dissection",
            "pythagorean_tree",
            "rectangular_solid",
            "regular_polygon_decomposition",
            "sector",
            "shape_gallery",
            "similar_figure_measure_transfer",
            "solid_cross_section",
            "solid_formula",
            "solid_revolution",
            "special_quadrilateral",
            "survey_traverse",
            "tangent_packing",
            "trapezoid_extension",
            "triangle_congruence_correspondence",
            "triangle_relations",
            "volume_equivalence_conversion",
            "wire_shape_conversion",
        }
    ),
    "graph": frozenset(
        {
            "adjacency",
            "automaton",
            "binary_tree",
            "flow_network",
            "graph_options",
            "metro",
            "node_link",
            "pedigree_chart",
            "phylogeny_tree",
            "pipe_network",
        }
    ),
    "icons": frozenset(
        {
            "icon_cutout",
            "icon_field",
            "mirror_grid",
            "named_field",
            "named_grid",
            "named_path",
            "named_ring",
            "named_strip",
            "overlap_grid",
            "pair_grid",
            "paired_canvas",
            "reference_canvas",
            "sequence_strip",
            "single_transform_options",
            "venn_field",
            "wallpaper_panels",
        }
    ),
    "illustrations": frozenset(
        {
            "construction_site",
            "environment",
            "indoor_room",
            "isometric_farmstead",
            "isometric_harbor",
            "isometric_quarry",
            "library",
            "park_playground",
            "pixel_village",
            "rpg_dungeon",
            "rpg_house",
            "rpg_tactical_map",
        }
    ),
    "pages": frozenset(
        {
            "calendar",
            "calendar_event_grid",
            "category_grid",
            "command_matrix",
            "concept_map",
            "control_board",
            "cycle",
            "form_section",
            "hero_callout_infographic",
            "hierarchy",
            "infographic",
            "instruction_panel",
            "map",
            "mixed_infographic_page",
            "navigation_flow",
            "paired_forms",
            "process_flow",
            "profile_card_grid",
            "ranked_list",
            "record_table",
            "schedule",
            "schema",
            "sectioned_infographic",
            "step_list",
            "timeline",
            "web_action",
            "workspace",
        }
    ),
    "physics": frozenset(
        {
            "analog_meter",
            "bridge_circuit",
            "buoyancy_density",
            "bulb_circuit",
            "circuit_equivalent",
            "circuit_state_change",
            "collision",
            "electromagnetic_induction",
            "electrostatic_field",
            "fluid_flow",
            "free_body_forces",
            "gear_train",
            "graduated_cylinder",
            "hydraulic",
            "lens_optics",
            "lever",
            "magnetic_force",
            "manometer",
            "motion_graph",
            "orbital_motion",
            "piston_cylinder",
            "pulley",
            "pv_diagram",
            "ray_optics",
            "refraction_layers",
            "shadow_cause",
            "signal_transform",
            "spring",
            "stack_stability",
            "switch_circuit",
            "thermal_mixing",
            "thermometer",
            "vernier_caliper",
            "wave_interference",
            "waveform_panel",
            "wire_magnetism",
        }
    ),
    "puzzles": frozenset(
        {
            "arithmetic_panel",
            "balance_scale",
            "cell_board",
            "code_grid",
            "color_gradient",
            "counterfactual_board",
            "cube_net",
            "cyclic_order",
            "logic_grid",
            "matchstick",
            "maze",
            "nonogram",
            "overlay",
            "paper_fold",
            "paper_fold_cut",
            "pipe_flow",
            "polyomino_missing",
            "raven_matrix",
            "rubiks_net",
            "star_battle",
            "string_topology",
            "sudoku",
            "tangram",
            "tents",
            "toggle_grid",
            "voxel_cube",
            "voxel_ladder",
            "word_search",
        }
    ),
    "symbolic": frozenset(
        {
            "abacus",
            "agent_automaton",
            "braille_cell",
            "clock",
            "dice",
            "life_automaton",
            "logic_gate_circuit",
            "morse_code",
            "music_staff",
            "organic_structure",
            "radial_code_wheel",
            "spinner",
            "turing_tape",
        }
    ),
    "three_d": frozenset(
        {
            "carousel",
            "conveyor",
            "object_cluster",
            "object_scene",
            "room",
            "street",
            "surface_fixture",
            "warehouse",
        }
    ),
}
SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES: dict[str, frozenset[str]] = {
    "charts": frozenset(
        {
            "annotated_series",
            "area",
            "bar_3d",
            "boxplot",
            "candlestick",
            "combo_mark",
            "composition_panels",
            "contour_density",
            "curve_panels",
            "dashboard",
            "density_curve",
            "dumbbell",
            "error_interval",
            "errorbar_series",
            "heatmap",
            "hexbin_density",
            "histogram",
            "matrix",
            "multiseries",
            "parallel_coords",
            "part_whole",
            "pictogram",
            "population_pyramid",
            "radar",
            "radial_progress",
            "radial_sankey",
            "region_map",
            "sankey",
            "scatter_cluster",
            "scatter_points",
            "scatter_readout",
            "scientific_axis_frame",
            "single_series",
            "size_encoding",
            "style_legend",
            "sunburst",
            "surface_3d",
            "table",
            "treemap",
            "uncertainty_band",
            "violin",
            "waterfall",
        }
    ),
    "games": frozenset(
        {
            "2048",
            "backgammon",
            "battleship",
            "bingo",
            "bowling",
            "brick_breaker",
            "bubble_shooter",
            "cards",
            "checkers",
            "chess",
            "chess_variant",
            "circular_chess",
            "connect_four",
            "crossing",
            "darts",
            "dominoes",
            "dots_and_boxes",
            "go",
            "hex",
            "irregular_link_board",
            "lane_runner",
            "ludo_board",
            "mancala_pit_board",
            "marble_chain",
            "match3",
            "minecraft",
            "minesweeper",
            "minigolf",
            "nine_mens_morris",
            "pacman",
            "pinball_table",
            "platformer",
            "pool",
            "racing_track",
            "radial_hunt_board",
            "reversi",
            "rhythm",
            "rule_override_board",
            "sixteen_soldiers",
            "sliding_block",
            "slot_machine",
            "snake",
            "snakes_ladders",
            "sokoban",
            "solitaire",
            "space_shooter",
            "tetris",
            "tic_tac_toe_3d",
            "tower_defense",
            "tower_draughts_board",
            "ultimate_tictactoe",
        }
    ),
    "geometry": frozenset(
        {
            "angle_relations",
            "area_partition",
            "bearing_route",
            "circle_centerline_overlap",
            "circle_pair_tangents",
            "circle_polygon_composite",
            "circle_theorem",
            "composite_shape",
            "concentric_chord",
            "cone_net",
            "container_volume_transfer",
            "coordinate_composite",
            "coordinate_conversion",
            "coordinate_panels",
            "coordinate_plane",
            "cuboid_views",
            "cylinder_wrap",
            "function_graph",
            "function_panels",
            "graph_paper",
            "incircle_tangents",
            "measuring_tools",
            "paper_fold",
            "polygon_equation_diagram",
            "pythagorean_dissection",
            "pythagorean_tree",
            "rectangular_solid",
            "regular_polygon_decomposition",
            "sector",
            "shape_gallery",
            "similar_figure_measure_transfer",
            "solid_cross_section",
            "solid_formula",
            "solid_revolution",
            "special_quadrilateral",
            "survey_traverse",
            "tangent_packing",
            "trapezoid_extension",
            "triangle_congruence_correspondence",
            "triangle_relations",
            "volume_equivalence_conversion",
            "wire_shape_conversion",
        }
    ),
    "graph": frozenset(
        {
            "adjacency",
            "automaton",
            "binary_tree",
            "flow_network",
            "graph_options",
            "metro",
            "node_link",
            "pedigree_chart",
            "phylogeny_tree",
            "pipe_network",
        }
    ),
    "icons": frozenset(
        {
            "icon_cutout",
            "icon_field",
            "mirror_grid",
            "named_field",
            "named_grid",
            "named_path",
            "named_ring",
            "named_strip",
            "overlap_grid",
            "pair_grid",
            "paired_canvas",
            "reference_canvas",
            "sequence_strip",
            "single_transform_options",
            "venn_field",
            "wallpaper_panels",
        }
    ),
    "illustrations": frozenset(
        {
            "construction_site",
            "environment",
            "indoor_room",
            "isometric_farmstead",
            "isometric_harbor",
            "isometric_quarry",
            "library",
            "park_playground",
            "pixel_village",
            "rpg_dungeon",
            "rpg_house",
            "rpg_tactical_map",
        }
    ),
    "pages": frozenset(
        {
            "calendar",
            "calendar_event_grid",
            "category_grid",
            "command_matrix",
            "concept_map",
            "control_board",
            "cycle",
            "form_section",
            "hero_callout_infographic",
            "hierarchy",
            "infographic",
            "instruction_panel",
            "map",
            "mixed_infographic_page",
            "navigation_flow",
            "paired_forms",
            "process_flow",
            "profile_card_grid",
            "ranked_list",
            "record_table",
            "schedule",
            "schema",
            "sectioned_infographic",
            "step_list",
            "timeline",
            "web_action",
            "workspace",
        }
    ),
    "physics": frozenset(
        {
            "analog_meter",
            "bridge_circuit",
            "buoyancy_density",
            "bulb_circuit",
            "circuit_equivalent",
            "circuit_state_change",
            "collision",
            "electromagnetic_induction",
            "electrostatic_field",
            "fluid_flow",
            "free_body_forces",
            "gear_train",
            "graduated_cylinder",
            "hydraulic",
            "lens_optics",
            "lever",
            "magnetic_force",
            "manometer",
            "motion_graph",
            "orbital_motion",
            "piston_cylinder",
            "pulley",
            "pv_diagram",
            "ray_optics",
            "refraction_layers",
            "shadow_cause",
            "signal_transform",
            "spring",
            "stack_stability",
            "switch_circuit",
            "thermal_mixing",
            "thermometer",
            "vernier_caliper",
            "wave_interference",
            "waveform_panel",
            "wire_magnetism",
        }
    ),
    "puzzles": frozenset(
        {
            "arithmetic_panel",
            "balance_scale",
            "cell_board",
            "code_grid",
            "color_gradient",
            "counterfactual_board",
            "cube_net",
            "cyclic_order",
            "logic_grid",
            "matchstick",
            "maze",
            "nonogram",
            "overlay",
            "paper_fold",
            "paper_fold_cut",
            "pipe_flow",
            "polyomino_missing",
            "raven_matrix",
            "rubiks_net",
            "star_battle",
            "string_topology",
            "sudoku",
            "tangram",
            "tents",
            "toggle_grid",
            "voxel_cube",
            "voxel_ladder",
            "word_search",
        }
    ),
    "symbolic": frozenset(
        {
            "abacus",
            "agent_automaton",
            "braille_cell",
            "clock",
            "dice",
            "life_automaton",
            "logic_gate_circuit",
            "morse_code",
            "music_staff",
            "organic_structure",
            "radial_code_wheel",
            "spinner",
            "turing_tape",
        }
    ),
    "three_d": frozenset(
        {
            "carousel",
            "conveyor",
            "object_cluster",
            "object_scene",
            "room",
            "street",
            "surface_fixture",
            "warehouse",
        }
    ),
}
SCENE_PACKAGE_PILOT_TASK_IDS: frozenset[str] = frozenset()

_V0_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9_]+)__(?P<scene_id>[a-z0-9_]+)__(?P<objective_contract>[a-z0-9_]+)$"
)
_REVIEW_SCENE_ENV = "TRACE_SCENE_PACKAGE_REVIEW_SCENE"


@dataclass(frozen=True)
class PublicTaskIdParts:
    """Parsed taxonomy-v0 public task id components."""

    domain: str
    scene_id: str
    objective_contract: str


def is_scene_package_migrated_domain(domain: str) -> bool:
    """Return whether ``domain`` must obey scene-package invariants."""

    return str(domain) in MIGRATED_SCENE_PACKAGE_DOMAINS


def is_scene_package_migrated_scene(domain: str, scene_id: str) -> bool:
    """Return whether one domain/scene pair must obey scene-package invariants."""

    return str(scene_id) in MIGRATED_SCENE_PACKAGE_SCENES.get(str(domain), frozenset())


def is_scene_package_review_target_scene(domain: str, scene_id: str) -> bool:
    """Return whether one scene may appear in the migration review app."""

    resolved_domain = str(domain)
    resolved_scene = str(scene_id)
    selected = os.environ.get(_REVIEW_SCENE_ENV, "").strip()
    if selected:
        if "/" not in selected:
            raise ValueError(f"{_REVIEW_SCENE_ENV} must use '<domain>/<scene_id>'")
        selected_domain, selected_scene = (
            part.strip() for part in selected.split("/", 1)
        )
        if not selected_domain or not selected_scene:
            raise ValueError(f"{_REVIEW_SCENE_ENV} must use '<domain>/<scene_id>'")
        return resolved_domain == selected_domain and resolved_scene == selected_scene
    return resolved_scene in SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES.get(
        resolved_domain, frozenset()
    )


def scene_package_review_target_scenes() -> dict[str, frozenset[str]]:
    """Return centrally registered review-candidate scenes visible to reviewers."""

    selected = os.environ.get(_REVIEW_SCENE_ENV, "").strip()
    if selected:
        if "/" not in selected:
            raise ValueError(f"{_REVIEW_SCENE_ENV} must use '<domain>/<scene_id>'")
        domain, scene_id = (part.strip() for part in selected.split("/", 1))
        if not domain or not scene_id:
            raise ValueError(f"{_REVIEW_SCENE_ENV} must use '<domain>/<scene_id>'")
        registered = SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES.get(str(domain), frozenset())
        if str(scene_id) not in registered:
            raise ValueError(
                f"{_REVIEW_SCENE_ENV}={selected!r} is not a registered review-candidate scene"
            )
        return {str(domain): frozenset({str(scene_id)})}

    return {
        str(domain): frozenset(sorted(str(scene_id) for scene_id in scene_ids))
        for domain, scene_ids in sorted(SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES.items())
    }


def is_scene_package_task(task_id: str, *, domain: str | None = None) -> bool:
    """Return whether one task should use scene-package migration behavior."""

    if str(task_id) in SCENE_PACKAGE_PILOT_TASK_IDS:
        return True
    scene_id = ""
    try:
        parts = parse_public_task_id(str(task_id))
        scene_id = parts.scene_id
        if domain is None:
            domain = parts.domain
    except ValueError:
        pass
    if domain is None:
        domain = ""
    return is_scene_package_migrated_domain(
        str(domain)
    ) or is_scene_package_migrated_scene(str(domain), str(scene_id))


def parse_public_task_id(task_id: str) -> PublicTaskIdParts:
    """Parse a taxonomy-v0 public task id.

    Raises:
        ValueError: if ``task_id`` does not match
            ``task_<domain>__<scene_id>__<objective_contract>``.
    """

    match = _V0_TASK_ID_PATTERN.match(str(task_id))
    if match is None:
        raise ValueError(
            "task_id must follow taxonomy-v0 public form "
            "'task_<domain>__<scene_id>__<objective_contract>' "
            f"(got: {task_id})"
        )
    return PublicTaskIdParts(
        domain=str(match.group("domain")),
        scene_id=str(match.group("scene_id")),
        objective_contract=str(match.group("objective_contract")),
    )
