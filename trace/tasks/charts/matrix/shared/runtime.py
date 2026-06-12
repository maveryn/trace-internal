"""Rendering runtime helpers for matrix chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.font_assets import font_asset_version
from .cell_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _MatrixRenderParams,
    _RenderedMatrix,
    _resolve_render_params,
)
from .cell_rendering import _render_matrix


@dataclass(frozen=True)
class MatrixRenderResult:
    image: Image.Image
    rendered_scene: _RenderedMatrix
    render_params: _MatrixRenderParams
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]


def render_matrix_scene(
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    palette_variant: str,
    header_layout: str,
    grid_style: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> MatrixRenderResult:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered_scene = _render_matrix(
        background,
        scene_title=str(dataset["scene_title"]),
        scene_variant=str(scene_variant),
        palette_variant=str(palette_variant),
        header_layout=str(header_layout),
        grid_style=str(grid_style),
        row_labels=list(dataset["row_labels"]),
        column_labels=list(dataset["column_labels"]),
        cells=list(dataset["cells"]),
        value_min=int(dataset["value_min"]),
        value_max=int(dataset["value_max"]),
        scene_meta=dict(dataset["scene_meta"]),
        render_params=render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return MatrixRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
    )


def font_assets_payload(render_params: _MatrixRenderParams) -> Dict[str, str]:
    return {
        "asset_version": font_asset_version(),
        "chart_font_family": str(render_params.font_family),
    }


def annotation_bboxes(
    *,
    rendered_scene: _RenderedMatrix,
    annotation_cell_ids: Sequence[str],
) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
    bboxes: List[List[float]] = []
    entries: List[Dict[str, Any]] = []
    for cell_id in annotation_cell_ids:
        bbox = list(rendered_scene.cell_bbox_map[str(cell_id)])
        bboxes.append(list(bbox))
        entries.append({"role": "cell", "id": str(cell_id), "bbox": list(bbox)})
    return bboxes, entries


__all__ = ["MatrixRenderResult", "annotation_bboxes", "font_assets_payload", "render_matrix_scene"]
