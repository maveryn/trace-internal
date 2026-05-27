"""Tests for procedural named icon rendering."""

from __future__ import annotations

import pytest

from trace.tasks.icons.shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_DISPLAY_NAMES,
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    render_procedural_named_icon_rgba,
)


def test_procedural_named_icon_vocabulary_has_clear_shapes() -> None:
    assert len(PROCEDURAL_NAMED_ICON_SHAPES) == 100
    assert len(set(PROCEDURAL_NAMED_ICON_SHAPES)) == len(PROCEDURAL_NAMED_ICON_SHAPES)
    assert set(PROCEDURAL_NAMED_ICON_SHAPES) == set(PROCEDURAL_NAMED_ICON_DISPLAY_NAMES)
    assert procedural_named_icon_display_name("lightning_bolt") == "lightning bolt"
    assert procedural_named_icon_display_name("rocket") == "rocket"
    assert procedural_named_icon_display_name("magnifying_glass") == "magnifying glass"
    assert procedural_named_icon_display_name("shuriken") == "shuriken"
    assert procedural_named_icon_display_name("tree") == "tree"
    assert procedural_named_icon_display_name("rugby_ball") == "rugby ball"
    assert procedural_named_icon_display_name("broccoli") == "broccoli"
    assert procedural_named_icon_display_name("cactus") == "cactus"
    assert procedural_named_icon_display_name("guitar") == "guitar"
    assert procedural_named_icon_display_name("acorn") == "acorn"


def test_procedural_named_icon_renderer_outputs_nonempty_cropped_rgba() -> None:
    for shape_id in PROCEDURAL_NAMED_ICON_SHAPES:
        image = render_procedural_named_icon_rgba(
            shape_id=shape_id,
            size_px=80,
            tint_rgb=(20, 90, 180),
        )
        assert image.mode == "RGBA"
        assert 10 <= image.size[0] <= 80
        assert 10 <= image.size[1] <= 80
        assert image.getchannel("A").getbbox() is not None


def test_procedural_named_icon_renderer_outputs_supported_fill_styles() -> None:
    for fill_style in PROCEDURAL_NAMED_ICON_FILL_STYLES:
        image = render_procedural_named_icon_rgba(
            shape_id="star",
            size_px=96,
            tint_rgb=(20, 90, 180),
            fill_style=str(fill_style),
        )
        assert image.mode == "RGBA"
        assert image.getchannel("A").getbbox() is not None


def test_procedural_named_icon_renderer_rejects_unknown_shape() -> None:
    with pytest.raises(KeyError):
        render_procedural_named_icon_rgba(
            shape_id="not_a_shape",
            size_px=80,
            tint_rgb=(20, 90, 180),
        )
