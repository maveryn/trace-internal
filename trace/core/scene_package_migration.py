"""Scene-package migration rollout helpers.

This module centralizes temporary per-domain, per-scene, and first-slice
switches used while TRACE retires legacy routing. The migrated scene/domain
switches are runtime structural switches: they allow active tasks that have
moved to scene-package source paths to omit legacy routing metadata.

A scene-package migration is not objective-complete until the scene is listed
in ``SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_COMPLETE_SCENES``. Pending-scene
tracking is only an in-progress marker for structurally routed scenes that
still need the final source/config/prompt/docs audit.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


MIGRATED_SCENE_PACKAGE_DOMAINS: frozenset[str] = frozenset({"charts", "graph"})
MIGRATED_SCENE_PACKAGE_SCENES: dict[str, frozenset[str]] = {
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
            "coordinate_panels",
            "coordinate_plane",
            "cuboid_views",
            "cylinder_wrap",
            "function_graph",
            "function_panels",
            "graph_paper",
            "incircle_tangents",
            "marked_polygon_equation",
            "measuring_tools",
            "paper_fold",
            "parallel_segment_proportion",
            "polygon_angle_chase",
            "pythagorean_dissection",
            "pythagorean_tree",
            "rectangular_solid",
            "regular_polygon_decomposition",
            "right_triangle_altitude_theorem",
            "sector",
            "shape_gallery",
            "similar_figure_measure_transfer",
            "solid_cross_section",
            "solid_formula",
            "solid_revolution",
            "special_quadrilateral",
            "split_triangle_angle_chase",
            "split_triangle_trig_chain",
            "survey_traverse",
            "tangent_packing",
            "trapezoid_extension",
            "triangle_congruence_correspondence",
            "triangle_relations",
            "volume_equivalence_conversion",
            "wire_shape_conversion",
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
    "icons": frozenset({"pair_grid", "paired_canvas", "reference_canvas", "single_transform_options"}),
    "illustrations": frozenset(
        {
            "image_cutout_board",
            "indoor_room",
            "missing_patch",
            "pixel_village",
            "single_object_figure",
            "source_scene_edit",
        }
    ),
    "pages": frozenset({"mixed_infographic_page"}),
    "three_d": frozenset({"object_cluster", "object_scene", "surface_fixture"}),
}

SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES: dict[str, frozenset[str]] = {
    "games": MIGRATED_SCENE_PACKAGE_SCENES["games"],
    "geometry": MIGRATED_SCENE_PACKAGE_SCENES["geometry"],
}

# Explicit registry for scenes that have passed the final objective-ownership
# migration audit. Start empty: scenes completed under older, weaker migration
# policy must be re-audited before entering this registry.
SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_COMPLETE_SCENES: dict[str, frozenset[str]] = {}

# Temporary first-slice rollout: allow individual pilot tasks to exercise the
# scene-package path before their whole domains are migrated.
SCENE_PACKAGE_PILOT_TASK_IDS: frozenset[str] = frozenset(
    {
        "task_pages__calendar_event_grid__category_slot_day_count",
        "task_pages__calendar_event_grid__date_for_category_slot_label",
        "task_pages__calendar_event_grid__date_slot_category_label",
        "task_pages__category_grid__category_item_count",
        "task_pages__category_grid__category_slot_item_label",
        "task_pages__comparison_panel__side_attribute_value_label",
        "task_pages__cycle__offset_stage_label",
        "task_pages__map__destination_after_directions_label",
        "task_pages__map__landmark_after_route_step_label",
    }
)

_V0_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9_]+)__(?P<scene_id>[a-z0-9_]+)__(?P<objective_contract>[a-z0-9_]+)$"
)


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


def is_scene_package_objective_ownership_complete_scene(domain: str, scene_id: str) -> bool:
    """Return whether one domain/scene pair passed final objective-ownership gates."""

    return str(scene_id) in SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_COMPLETE_SCENES.get(str(domain), frozenset())


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
    return is_scene_package_migrated_domain(str(domain)) or is_scene_package_migrated_scene(str(domain), str(scene_id))


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
