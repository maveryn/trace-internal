"""Shared dataset builders and render defaults for annotated schematic tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.common import resolve_diagrams_axis_variant, resolve_diagrams_int_param, resolve_diagrams_rgb_triple


SUPPORTED_DIAGRAM_SCHEMATIC_SCENE_VARIANTS: Tuple[str, ...] = ("annotated_schematic",)
SUPPORTED_DIAGRAM_SCHEMATIC_TASK_VARIANTS: Tuple[str, ...] = (
    "callout_for_named_part",
    "callout_for_highlighted_part",
)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Annotated Schematic",
    "Component Diagram",
    "System Schematic",
    "Assembly Detail",
    "Module Layout",
)
_PART_LABELS: Tuple[str, ...] = (
    "Core",
    "Valve",
    "Rotor",
    "Sensor",
    "Intake",
    "Outlet",
    "Mixer",
    "Relay",
    "Filter",
    "Switch",
    "Coil",
    "Gauge",
    "Vent",
    "Pump",
    "Nozzle",
    "Servo",
    "Buffer",
    "Shield",
    "Socket",
    "Logic",
    "Driver",
    "Seal",
    "Port",
    "Gate",
    "Cell",
    "Drum",
    "Probe",
    "Panel",
    "Cable",
    "Clamp",
    "Latch",
    "Feeder",
)
_PART_FILL_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (213, 229, 247),
    (238, 216, 244),
    (247, 225, 208),
    (222, 238, 218),
    (244, 232, 203),
    (224, 233, 241),
    (232, 223, 246),
    (243, 218, 226),
)
_SHAPE_KINDS: Tuple[str, ...] = ("rounded_rect", "capsule", "ellipse", "hexagon")
_SLOT_SPECS: Dict[str, Dict[str, Tuple[float, float, float, float] | Tuple[float, float]]] = {
    "slot_0": {
        "part_bbox_norm": (0.10, 0.12, 0.30, 0.28),
        "callout_center_norm": (0.10, 0.16),
    },
    "slot_1": {
        "part_bbox_norm": (0.40, 0.08, 0.60, 0.23),
        "callout_center_norm": (0.50, 0.07),
    },
    "slot_2": {
        "part_bbox_norm": (0.70, 0.12, 0.90, 0.28),
        "callout_center_norm": (0.90, 0.16),
    },
    "slot_3": {
        "part_bbox_norm": (0.08, 0.40, 0.30, 0.56),
        "callout_center_norm": (0.06, 0.50),
    },
    "slot_4": {
        "part_bbox_norm": (0.70, 0.40, 0.92, 0.56),
        "callout_center_norm": (0.94, 0.50),
    },
    "slot_5": {
        "part_bbox_norm": (0.24, 0.70, 0.44, 0.84),
        "callout_center_norm": (0.24, 0.93),
    },
    "slot_6": {
        "part_bbox_norm": (0.56, 0.70, 0.76, 0.84),
        "callout_center_norm": (0.76, 0.93),
    },
}
_LAYOUTS_BY_COUNT: Dict[int, Tuple[Tuple[str, ...], ...]] = {
    5: (
        ("slot_0", "slot_1", "slot_2", "slot_5", "slot_6"),
        ("slot_0", "slot_1", "slot_2", "slot_3", "slot_4"),
    ),
    6: (
        ("slot_0", "slot_1", "slot_2", "slot_3", "slot_5", "slot_6"),
        ("slot_0", "slot_1", "slot_2", "slot_4", "slot_5", "slot_6"),
    ),
    7: (("slot_0", "slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6"),),
}


@dataclass(frozen=True)
class SchematicDefaults:
    """Default generation bounds for callout-target schematic tasks."""

    part_count_min: int = 5
    part_count_max: int = 7


@dataclass(frozen=True)
class SchematicRenderParams:
    """Resolved rendering knobs for annotated schematic scenes."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    title_font_size_px: int
    title_band_height_px: int
    chassis_corner_radius_px: int
    chassis_border_width_px: int
    chassis_fill_rgb: Tuple[int, int, int]
    chassis_border_rgb: Tuple[int, int, int]
    bus_width_px: int
    bus_color_rgb: Tuple[int, int, int]
    part_border_width_px: int
    part_corner_radius_px: int
    part_label_font_size_px: int
    part_border_rgb: Tuple[int, int, int]
    part_label_color_rgb: Tuple[int, int, int]
    part_label_stroke_rgb: Tuple[int, int, int]
    callout_diameter_px: int
    callout_border_width_px: int
    callout_font_size_px: int
    callout_fill_rgb: Tuple[int, int, int]
    callout_border_rgb: Tuple[int, int, int]
    callout_text_rgb: Tuple[int, int, int]
    leader_width_px: int
    leader_color_rgb: Tuple[int, int, int]
    highlight_fill_rgb: Tuple[int, int, int]
    highlight_border_rgb: Tuple[int, int, int]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]


def resolve_schematic_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active schematic scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_SCHEMATIC_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_schematic_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active semantic schematic query variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_SCHEMATIC_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_schematic_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> SchematicRenderParams:
    """Resolve rendering params for schematic scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(params, render_defaults, key, fallback)

    return SchematicRenderParams(
        canvas_width=int(resolve_diagrams_int_param(params, render_defaults, "canvas_width", 1280)),
        canvas_height=int(resolve_diagrams_int_param(params, render_defaults, "canvas_height", 900)),
        outer_margin_px=int(resolve_diagrams_int_param(params, render_defaults, "outer_margin_px", 52)),
        panel_padding_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_padding_px", 28)),
        panel_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_corner_radius_px", 30)),
        title_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "title_font_size_px", 32)),
        title_band_height_px=int(resolve_diagrams_int_param(params, render_defaults, "title_band_height_px", 78)),
        chassis_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "chassis_corner_radius_px", 28)),
        chassis_border_width_px=int(resolve_diagrams_int_param(params, render_defaults, "chassis_border_width_px", 3)),
        chassis_fill_rgb=_triple("chassis_fill_rgb", (246, 249, 253)),
        chassis_border_rgb=_triple("chassis_border_rgb", (191, 199, 210)),
        bus_width_px=int(resolve_diagrams_int_param(params, render_defaults, "bus_width_px", 4)),
        bus_color_rgb=_triple("bus_color_rgb", (205, 212, 221)),
        part_border_width_px=int(resolve_diagrams_int_param(params, render_defaults, "part_border_width_px", 3)),
        part_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "part_corner_radius_px", 20)),
        part_label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "part_label_font_size_px", 24)),
        part_border_rgb=_triple("part_border_rgb", (84, 94, 108)),
        part_label_color_rgb=_triple("part_label_color_rgb", (31, 37, 45)),
        part_label_stroke_rgb=_triple("part_label_stroke_rgb", (255, 255, 255)),
        callout_diameter_px=int(resolve_diagrams_int_param(params, render_defaults, "callout_diameter_px", 56)),
        callout_border_width_px=int(resolve_diagrams_int_param(params, render_defaults, "callout_border_width_px", 3)),
        callout_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "callout_font_size_px", 28)),
        callout_fill_rgb=_triple("callout_fill_rgb", (250, 251, 254)),
        callout_border_rgb=_triple("callout_border_rgb", (184, 191, 202)),
        callout_text_rgb=_triple("callout_text_rgb", (49, 57, 69)),
        leader_width_px=int(resolve_diagrams_int_param(params, render_defaults, "leader_width_px", 4)),
        leader_color_rgb=_triple("leader_color_rgb", (126, 135, 147)),
        highlight_fill_rgb=_triple("highlight_fill_rgb", (255, 236, 186)),
        highlight_border_rgb=_triple("highlight_border_rgb", (184, 128, 31)),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
    )


def resolve_schematic_slot_spec(slot_id: str) -> Dict[str, Tuple[float, float, float, float] | Tuple[float, float]]:
    """Return the normalized geometry contract for one schematic slot."""

    return dict(_SLOT_SPECS[str(slot_id)])


def _scene_title(*, rng) -> str:
    """Sample one short schematic scene title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def _sample_part_labels(*, count: int, rng) -> list[str]:
    """Sample unique short component labels for one schematic."""

    if int(count) > len(_PART_LABELS):
        raise ValueError("requested more schematic part labels than available")
    return [str(label) for label in rng.sample(list(_PART_LABELS), int(count))]


def _sample_part_colors(*, count: int, rng) -> list[Tuple[int, int, int]]:
    """Sample muted part fills for one schematic."""

    if int(count) > len(_PART_FILL_PALETTE):
        raise ValueError("requested more schematic part colors than available")
    sampled = rng.sample(list(_PART_FILL_PALETTE), int(count))
    return [tuple(int(channel) for channel in color) for color in sampled]


def _resolve_slot_ids(
    *,
    part_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> list[str]:
    """Resolve one active slot template for the requested part count."""

    options = _LAYOUTS_BY_COUNT[int(part_count)]
    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.schematic_layout.{int(part_count)}",
        )
        % len(options)
    )
    return [str(slot_id) for slot_id in options[selection_index]]


def build_schematic_callout_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    defaults: SchematicDefaults,
) -> Dict[str, Any]:
    """Build one annotated-schematic callout query instance."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    part_count_min, part_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="part_count_min",
        max_key="part_count_max",
        fallback_min=int(defaults.part_count_min),
        fallback_max=int(defaults.part_count_max),
        context=f"{task_id} part count",
    )
    part_count = int(rng.randint(int(part_count_min), int(part_count_max)))
    slot_ids = _resolve_slot_ids(
        part_count=int(part_count),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    part_labels = _sample_part_labels(count=int(part_count), rng=rng)
    callout_labels = [str(label) for label in rng.sample(list("ABCDEFG"), int(part_count))]
    fill_colors = _sample_part_colors(count=int(part_count), rng=rng)
    shape_kinds = [str(rng.choice(_SHAPE_KINDS)) for _ in range(int(part_count))]
    target_index = int(rng.randrange(int(part_count)))

    part_specs = []
    for index, slot_id in enumerate(slot_ids):
        part_id = f"part_{index}"
        callout_id = f"callout_{index}"
        part_specs.append(
            {
                "part_id": str(part_id),
                "part_label": str(part_labels[index]),
                "part_bbox_id": f"part_bbox_{index}",
                "part_label_bbox_id": f"part_label_bbox_{index}",
                "slot_id": str(slot_id),
                "shape_kind": str(shape_kinds[index]),
                "fill_rgb": list(fill_colors[index]),
                "callout_id": str(callout_id),
                "callout_label": str(callout_labels[index]),
                "callout_bbox_id": f"callout_bbox_{index}",
                "callout_label_bbox_id": f"callout_label_bbox_{index}",
                "leader_bbox_id": f"leader_bbox_{index}",
                "highlighted": bool(index == target_index and str(task_variant) == "callout_for_highlighted_part"),
            }
        )

    target_spec = dict(part_specs[target_index])
    question_text = (
        f"Which labeled callout points to {str(target_spec['part_label'])}?"
        if str(task_variant) == "callout_for_named_part"
        else "Which labeled callout points to the highlighted part?"
    )
    return {
        "task_variant": str(task_variant),
        "scene_variant": str(scene_variant),
        "question_format": "schematic_callout_target_label",
        "view_family": "annotated_schematic_diagram",
        "scene_title": str(_scene_title(rng=rng)),
        "question_text": str(question_text),
        "part_count": int(part_count),
        "part_specs": [dict(spec) for spec in part_specs],
        "answer_callout_label": str(target_spec["callout_label"]),
        "answer_part_id": str(target_spec["part_id"]),
        "answer_part_label": str(target_spec["part_label"]),
        "answer_part_bbox_id": str(target_spec["part_bbox_id"]),
        "answer_callout_bbox_id": str(target_spec["callout_bbox_id"]),
        "query_focus": "named_part" if str(task_variant) == "callout_for_named_part" else "highlighted_part",
        "query_part_label": str(target_spec["part_label"]) if str(task_variant) == "callout_for_named_part" else None,
        "highlight_part_id": str(target_spec["part_id"]) if str(task_variant) == "callout_for_highlighted_part" else None,
        "supporting_part_bbox_ids": [str(target_spec["part_bbox_id"])],
    }


__all__ = [
    "SUPPORTED_DIAGRAM_SCHEMATIC_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_SCHEMATIC_TASK_VARIANTS",
    "SchematicDefaults",
    "SchematicRenderParams",
    "build_schematic_callout_dataset",
    "resolve_schematic_render_params",
    "resolve_schematic_scene_variant",
    "resolve_schematic_slot_spec",
    "resolve_schematic_task_variant",
]
