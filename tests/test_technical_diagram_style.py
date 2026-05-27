"""Tests for shared technical-diagram visual styling."""

from __future__ import annotations

from trace.tasks.physics.shared.diagram_style import (
    PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
    physics_electrostatics_theme_from_diagram_style,
    resolve_physics_diagram_style,
)
from trace.tasks.shared.visual_style.technical_diagram import (
    TECHNICAL_DIAGRAM_PALETTES,
    TECHNICAL_DIAGRAM_TREATMENTS,
    make_technical_diagram_background,
    resolve_technical_diagram_style,
)


def test_technical_diagram_registry_breadth_and_metadata() -> None:
    style, metadata = resolve_technical_diagram_style(
        instance_seed=12001,
        namespace="tests.technical_diagram",
        allow_dark=False,
        protected_colors=PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
    )

    assert len(TECHNICAL_DIAGRAM_TREATMENTS) == 20
    assert len(TECHNICAL_DIAGRAM_PALETTES) == 20
    assert metadata["kind"] == "technical_diagram_style"
    assert metadata["treatment"] == style.treatment
    assert metadata["palette_id"] == style.palette_id
    assert metadata["roles_rgb"]["axis"] == list(style.axis_rgb)
    assert metadata["grid_style"]["kind"] == style.grid_kind
    assert metadata["frame_style"]["mode"] == style.frame_mode
    assert set(metadata["frame_style"]["default_mode_weights"]) == {"none", "plain_outline", "matching_outline"}
    assert metadata["stroke_widths"]["axis_px"] == style.axis_stroke_width_px
    assert metadata["protected_colors_rgb"]
    assert metadata["contrast_checks"]["min_paper_ink_lab_distance"] > 0


def test_technical_diagram_background_is_deterministic() -> None:
    style, _ = resolve_technical_diagram_style(
        instance_seed=12002,
        namespace="tests.technical_diagram.background",
        treatments=("subtle_scan_sheet",),
        palettes=("neutral_ink",),
        frame_modes=("matching_outline",),
    )
    image_a, meta_a = make_technical_diagram_background(
        canvas_width=320,
        canvas_height=220,
        style=style,
        instance_seed=12002,
        namespace="tests.technical_diagram.background",
    )
    image_b, meta_b = make_technical_diagram_background(
        canvas_width=320,
        canvas_height=220,
        style=style,
        instance_seed=12002,
        namespace="tests.technical_diagram.background",
    )

    assert image_a.size == (320, 220)
    assert meta_a == meta_b
    assert image_a.tobytes() == image_b.tobytes()
    assert meta_a["style_spec"]["kind"] == "technical_diagram_style"
    assert meta_a["style_spec"]["frame_mode"] == "matching_outline"


def test_physics_diagram_adapter_preserves_electrostatics_semantic_colors() -> None:
    style, metadata = resolve_physics_diagram_style(
        instance_seed=12003,
        params={},
        scene_id="electrostatics_field_map",
        task_group="electrostatics",
        protected_colors=PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
        allow_dark=False,
    )
    theme = physics_electrostatics_theme_from_diagram_style(style, accent_color_name="blue")

    assert theme.positive_outline_rgb == (187, 58, 46)
    assert theme.negative_outline_rgb == (55, 91, 172)
    assert theme.axis_rgb == style.axis_rgb
    assert theme.grid_rgb == style.grid_minor_rgb
    assert metadata["selection"]["allow_dark"] is False
