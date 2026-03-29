"""Shared config, generation, and render helpers for spatial cube-view puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from .common import resolve_puzzle_axis_variant
from .cube_scene import PuzzleCubeRenderParams, SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS
from .symbol_rendering import PUZZLE_OBJECT_TYPES


@dataclass(frozen=True)
class PuzzleSpatialDefaults:
    """Stable fallback defaults shared by cube-view spatial puzzle tasks."""

    option_count: int = 6
    canvas_width: int = 1200
    canvas_height: int = 880
    scene_margin_left_px: int = 64
    scene_margin_right_px: int = 64
    scene_margin_top_px: int = 56
    scene_margin_bottom_px: int = 56
    reference_cube_box_size_px: int = 300
    reference_panel_padding_px: int = 28
    reference_to_pairs_gap_px: int = 36
    pair_group_gap_px: int = 28
    pair_box_size_px: int = 78
    pair_token_gap_px: int = 14
    pairs_to_options_gap_px: int = 56
    option_panel_width_px: int = 144
    option_panel_height_px: int = 186
    option_gap_px: int = 20
    option_cube_box_size_px: int = 92
    option_label_gap_px: int = 18
    slot_corner_radius_px: int = 18
    border_width_px: int = 3
    panel_corner_radius_px: int = 28
    option_label_font_size_px: int = 30
    balanced_task_variant_sampling: bool = True
    balanced_scene_variant_sampling: bool = True


def resolve_spatial_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: PuzzleSpatialDefaults,
) -> PuzzleCubeRenderParams:
    """Resolve one reusable cube-view render-parameter record."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleCubeRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", int(defaults.canvas_width)))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", int(defaults.canvas_height)))),
        scene_margin_left_px=int(params.get("scene_margin_left_px", group_default(render_defaults, "scene_margin_left_px", int(defaults.scene_margin_left_px)))),
        scene_margin_right_px=int(params.get("scene_margin_right_px", group_default(render_defaults, "scene_margin_right_px", int(defaults.scene_margin_right_px)))),
        scene_margin_top_px=int(params.get("scene_margin_top_px", group_default(render_defaults, "scene_margin_top_px", int(defaults.scene_margin_top_px)))),
        scene_margin_bottom_px=int(params.get("scene_margin_bottom_px", group_default(render_defaults, "scene_margin_bottom_px", int(defaults.scene_margin_bottom_px)))),
        reference_cube_box_size_px=int(params.get("reference_cube_box_size_px", group_default(render_defaults, "reference_cube_box_size_px", int(defaults.reference_cube_box_size_px)))),
        reference_panel_padding_px=int(params.get("reference_panel_padding_px", group_default(render_defaults, "reference_panel_padding_px", int(defaults.reference_panel_padding_px)))),
        reference_to_pairs_gap_px=int(params.get("reference_to_pairs_gap_px", group_default(render_defaults, "reference_to_pairs_gap_px", int(defaults.reference_to_pairs_gap_px)))),
        pair_group_gap_px=int(params.get("pair_group_gap_px", group_default(render_defaults, "pair_group_gap_px", int(defaults.pair_group_gap_px)))),
        pair_box_size_px=int(params.get("pair_box_size_px", group_default(render_defaults, "pair_box_size_px", int(defaults.pair_box_size_px)))),
        pair_token_gap_px=int(params.get("pair_token_gap_px", group_default(render_defaults, "pair_token_gap_px", int(defaults.pair_token_gap_px)))),
        pairs_to_options_gap_px=int(params.get("pairs_to_options_gap_px", group_default(render_defaults, "pairs_to_options_gap_px", int(defaults.pairs_to_options_gap_px)))),
        option_panel_width_px=int(params.get("option_panel_width_px", group_default(render_defaults, "option_panel_width_px", int(defaults.option_panel_width_px)))),
        option_panel_height_px=int(params.get("option_panel_height_px", group_default(render_defaults, "option_panel_height_px", int(defaults.option_panel_height_px)))),
        option_gap_px=int(params.get("option_gap_px", group_default(render_defaults, "option_gap_px", int(defaults.option_gap_px)))),
        option_cube_box_size_px=int(params.get("option_cube_box_size_px", group_default(render_defaults, "option_cube_box_size_px", int(defaults.option_cube_box_size_px)))),
        option_label_gap_px=int(params.get("option_label_gap_px", group_default(render_defaults, "option_label_gap_px", int(defaults.option_label_gap_px)))),
        slot_corner_radius_px=int(params.get("slot_corner_radius_px", group_default(render_defaults, "slot_corner_radius_px", int(defaults.slot_corner_radius_px)))),
        border_width_px=int(params.get("border_width_px", group_default(render_defaults, "border_width_px", int(defaults.border_width_px)))),
        panel_corner_radius_px=int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", int(defaults.panel_corner_radius_px)))),
        option_label_font_size_px=int(params.get("option_label_font_size_px", group_default(render_defaults, "option_label_font_size_px", int(defaults.option_label_font_size_px)))),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        option_panel_fill_rgb=_triple("option_panel_fill_rgb", (251, 251, 255)),
        option_cube_fill_rgb=_triple("option_cube_fill_rgb", (252, 252, 255)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        accent_color_rgb=_triple("accent_color_rgb", (54, 102, 180)),
    )


def resolve_spatial_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one visual cube-view scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS,
        task_id=task_id,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_option_count(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleSpatialDefaults,
    task_id: str,
) -> int:
    """Resolve the fixed option count for the cube-view task."""

    option_count = int(params.get("option_count", group_default(gen_defaults, "option_count", int(defaults.option_count))))
    if int(option_count) != 6:
        raise ValueError(f"{task_id} currently requires exactly 6 options for stable option-letter coverage")
    return int(option_count)


_FACE_NORMALS: Dict[str, Tuple[int, int, int]] = {
    "U": (0, 0, 1),
    "D": (0, 0, -1),
    "F": (0, 1, 0),
    "B": (0, -1, 0),
    "R": (1, 0, 0),
    "L": (-1, 0, 0),
}
_NORMAL_TO_FACE = {tuple(value): key for key, value in _FACE_NORMALS.items()}
_OPPOSITE_FACE = {
    "U": "D",
    "D": "U",
    "F": "B",
    "B": "F",
    "R": "L",
    "L": "R",
}


def _dot(lhs: Sequence[int], rhs: Sequence[int]) -> int:
    """Return one integer dot product for axis-aligned face normals."""

    return int(sum(int(a) * int(b) for a, b in zip(lhs, rhs)))


def _cross(lhs: Sequence[int], rhs: Sequence[int]) -> Tuple[int, int, int]:
    """Return one integer cross product for axis-aligned face normals."""

    lx, ly, lz = [int(value) for value in lhs]
    rx, ry, rz = [int(value) for value in rhs]
    return (
        int((ly * rz) - (lz * ry)),
        int((lz * rx) - (lx * rz)),
        int((lx * ry) - (ly * rx)),
    )


def _enumerate_valid_views(face_object_types: Mapping[str, str]) -> List[Dict[str, Any]]:
    """Enumerate every visible `(top, front, right)` cube view for one labeled cube."""

    views: List[Dict[str, Any]] = []
    for top_face, top_normal in _FACE_NORMALS.items():
        for front_face, front_normal in _FACE_NORMALS.items():
            if int(_dot(top_normal, front_normal)) != 0:
                continue
            right_face = str(_NORMAL_TO_FACE[_cross(front_normal, top_normal)])
            views.append(
                {
                    "top_face": str(top_face),
                    "front_face": str(front_face),
                    "right_face": str(right_face),
                    "top_object_type": str(face_object_types[str(top_face)]),
                    "front_object_type": str(face_object_types[str(front_face)]),
                    "right_object_type": str(face_object_types[str(right_face)]),
                    "visible_triplet": [
                        str(face_object_types[str(top_face)]),
                        str(face_object_types[str(front_face)]),
                        str(face_object_types[str(right_face)]),
                    ],
                }
            )
    return views


def _shared_symbol_count(candidate_triplet: Sequence[str], reference_triplet: Sequence[str]) -> int:
    """Return how many visible symbols two triplets share, ignoring position."""

    return int(len(set(str(value) for value in candidate_triplet) & set(str(value) for value in reference_triplet)))


def _position_match_count(candidate_triplet: Sequence[str], reference_triplet: Sequence[str]) -> int:
    """Return how many visible symbols stay in the same face position."""

    return int(sum(1 for lhs, rhs in zip(candidate_triplet, reference_triplet) if str(lhs) == str(rhs)))


def _rank_triplets(
    triplets: Sequence[Tuple[str, str, str]],
    *,
    reference_triplet: Sequence[str],
    rng,
) -> List[Tuple[str, str, str]]:
    """Rank triplets from harder/closer distractors to easier/farther ones."""

    candidates = [tuple(str(value) for value in triplet) for triplet in triplets]
    rng.shuffle(candidates)
    candidates.sort(
        key=lambda triplet: (
            int(_shared_symbol_count(triplet, reference_triplet)),
            int(_position_match_count(triplet, reference_triplet)),
        ),
        reverse=True,
    )
    return candidates


def build_cube_view_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleSpatialDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic cube-view puzzle dataset with explicit opposite-face hints."""

    selected_variant = str(task_variant)
    supported = {
        "same_cube_view",
        "impossible_cube_view",
    }
    if selected_variant not in supported:
        raise ValueError(f"unsupported spatial cube-view variant: {task_variant}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    option_count = _resolve_option_count(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )

    symbol_pool = list(PUZZLE_OBJECT_TYPES)
    rng.shuffle(symbol_pool)
    face_object_types = {
        face_name: str(symbol_pool[index])
        for index, face_name in enumerate(("U", "D", "F", "B", "R", "L"))
    }
    valid_views = _enumerate_valid_views(face_object_types)
    reference_view = dict(valid_views[int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:reference_view",
        )
        % len(valid_views)
    )])
    reference_triplet = tuple(str(value) for value in reference_view["visible_triplet"])
    valid_triples = [tuple(str(value) for value in view["visible_triplet"]) for view in valid_views]
    valid_triplet_set = set(valid_triples)
    invalid_triples = [
        tuple(str(value) for value in triplet)
        for triplet in permutations([str(value) for value in face_object_types.values()], 3)
        if tuple(str(value) for value in triplet) not in valid_triplet_set
    ]
    opposite_pair_specs = []
    for pair_index, anchor_face in enumerate(
        (
            str(reference_view["top_face"]),
            str(reference_view["front_face"]),
            str(reference_view["right_face"]),
        )
    ):
        opposite_face = str(_OPPOSITE_FACE[str(anchor_face)])
        opposite_pair_specs.append(
            {
                "pair_id": f"pair_{pair_index}",
                "anchor_face": str(anchor_face),
                "opposite_face": str(opposite_face),
                "left_box_id": f"pair_{pair_index}_left",
                "right_box_id": f"pair_{pair_index}_right",
                "left_object_type": str(face_object_types[str(anchor_face)]),
                "right_object_type": str(face_object_types[str(opposite_face)]),
            }
        )

    correct_option_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:correct_option_index",
        )
        % int(option_count)
    )
    if selected_variant == "same_cube_view":
        ranked_valid = _rank_triplets(
            [triplet for triplet in valid_triples if tuple(triplet) != tuple(reference_triplet)],
            reference_triplet=reference_triplet,
            rng=rng,
        )
        ranked_invalid = _rank_triplets(
            invalid_triples,
            reference_triplet=reference_triplet,
            rng=rng,
        )
        correct_choice = tuple(ranked_valid[0])
        distractor_triples = [tuple(triplet) for triplet in ranked_invalid[: int(option_count) - 1]]
        option_triplets = list(distractor_triples)
        option_triplets.insert(int(correct_option_index), tuple(correct_choice))
        option_valid_flags = [False] * (int(option_count) - 1)
        option_valid_flags.insert(int(correct_option_index), True)
    else:
        ranked_valid = _rank_triplets(
            [triplet for triplet in valid_triples if tuple(triplet) != tuple(reference_triplet)],
            reference_triplet=reference_triplet,
            rng=rng,
        )
        ranked_invalid = _rank_triplets(
            invalid_triples,
            reference_triplet=reference_triplet,
            rng=rng,
        )
        correct_choice = tuple(ranked_invalid[0])
        valid_option_triples = [tuple(triplet) for triplet in ranked_valid[: int(option_count) - 1]]
        option_triplets = list(valid_option_triples)
        option_triplets.insert(int(correct_option_index), tuple(correct_choice))
        option_valid_flags = [True] * (int(option_count) - 1)
        option_valid_flags.insert(int(correct_option_index), False)

    option_specs: List[Dict[str, Any]] = []
    option_labels: List[str] = []
    for option_index, (triplet, is_valid_view) in enumerate(zip(option_triplets, option_valid_flags)):
        option_label = str(option_label_for_index(int(option_index)))
        option_labels.append(option_label)
        if bool(is_valid_view):
            matching_view = next(
                view
                for view in valid_views
                if tuple(str(value) for value in view["visible_triplet"]) == tuple(triplet)
            )
            top_face = str(matching_view["top_face"])
            front_face = str(matching_view["front_face"])
            right_face = str(matching_view["right_face"])
        else:
            top_face = "?"
            front_face = "?"
            right_face = "?"
        option_specs.append(
            {
                "option_panel_id": f"option_{option_label}",
                "option_index": int(option_index),
                "option_label": str(option_label),
                "top_object_type": str(triplet[0]),
                "front_object_type": str(triplet[1]),
                "right_object_type": str(triplet[2]),
                "top_face": str(top_face),
                "front_face": str(front_face),
                "right_face": str(right_face),
                "visible_triplet": [str(value) for value in triplet],
                "is_valid_view": bool(is_valid_view),
                "is_correct": bool(option_index == correct_option_index),
            }
        )
    if len(option_specs) != int(option_count):
        raise ValueError(f"{task_id} expected exactly {option_count} option specs")

    return {
        "reference_view": dict(reference_view),
        "face_object_types": dict(face_object_types),
        "reference_triplet": [str(value) for value in reference_triplet],
        "opposite_pair_specs": [dict(item) for item in opposite_pair_specs],
        "valid_triplets": [[str(value) for value in triplet] for triplet in valid_triples],
        "invalid_triplets": [[str(value) for value in triplet] for triplet in invalid_triples],
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "visible_face_count": 3,
        "solver_trace": {
            "view_family": "cube_view_with_opposite_face_hints",
            "reference_triplet": [str(value) for value in reference_triplet],
            "face_object_types": dict(face_object_types),
            "valid_triplets": [[str(value) for value in triplet] for triplet in valid_triples],
            "invalid_triplets": [[str(value) for value in triplet] for triplet in invalid_triples],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
            "correct_visible_triplet": [str(value) for value in correct_choice],
            "options_are_valid_views": [bool(spec["is_valid_view"]) for spec in option_specs],
        },
    }


__all__ = [
    "PuzzleSpatialDefaults",
    "PuzzleCubeRenderParams",
    "SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS",
    "build_cube_view_dataset_for_variant",
    "resolve_spatial_render_params",
    "resolve_spatial_scene_variant",
]
