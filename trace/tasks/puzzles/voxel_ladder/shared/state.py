"""Passive state for voxel-ladder puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

DOMAIN = "puzzles"
SCENE_ID = "voxel_ladder"
SCENE_VARIANTS: tuple[str, ...] = (
    "clean_isometric_voxels",
    "worksheet_voxel_maze",
    "game_board_voxel_maze",
)
OPTION_LABELS: tuple[str, ...] = tuple("ABCDEF")

Color = tuple[int, int, int]
Node = tuple[int, int, int]
BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class Checkpoint:
    """One colored checkpoint cube in the voxel-ladder scene."""

    color_name: str
    color_rgb: Color
    node: Node
    reachable: bool
    on_goal_route: bool


@dataclass(frozen=True)
class Ladder:
    """A vertical ladder connecting two cube tops."""

    ladder_id: str
    lower: Node
    upper: Node
    on_goal_route: bool


@dataclass(frozen=True)
class OptionSpec:
    """One rendered route-sequence option card."""

    option_label: str
    sequence_items: tuple[str, ...]
    sequence_text: str
    sequence_rgb: tuple[Color, ...]
    is_correct: bool


@dataclass(frozen=True)
class VoxelLadderDataset:
    """Generated voxel-ladder scene plus task-neutral solver metadata."""

    scene_variant: str
    cubes: tuple[Node, ...]
    route_nodes: tuple[Node, ...]
    route_edges: tuple[tuple[Node, Node], ...]
    start_node: Node
    goal_node: Node
    checkpoints: tuple[Checkpoint, ...]
    ladders: tuple[Ladder, ...]
    graph_edges: tuple[tuple[Node, Node], ...]
    option_specs: tuple[OptionSpec, ...]
    route_checkpoint_sequence: tuple[str, ...]
    reachable_checkpoint_count: int
    semantic_params: dict[str, Any]

    @property
    def answer_support(self) -> tuple[str, ...]:
        """Return rendered option labels when the scene has option cards."""

        return tuple(option.option_label for option in self.option_specs)


@dataclass(frozen=True)
class RenderParams:
    """Resolved canvas, cube, and color parameters."""

    canvas_width: int
    canvas_height: int
    board_left_px: int
    board_top_px: int
    board_width_px: int
    board_height_px: int
    option_panel_width_px: int
    cube_width_px: int
    cube_height_px: int
    cube_depth_px: int
    label_font_size_px: int
    option_font_size_px: int
    panel_fill_rgb: Color
    panel_border_rgb: Color
    text_rgb: Color
    text_stroke_rgb: Color
    neutral_top_rgb: Color
    start_top_rgb: Color
    goal_top_rgb: Color
    checkpoint_top_rgb: Color
    ladder_rgb: Color
    shadow_rgb: Color
    unit_size_scale: float
    unit_size_jitter: dict[str, Any]


@dataclass(frozen=True)
class RenderedVoxelLadder:
    """Rendered image and item-to-bbox projection map."""

    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    item_bbox_map: dict[str, BBox]
    scene_bbox_px: BBox
