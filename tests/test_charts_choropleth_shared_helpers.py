import random

from trace.tasks.charts.map import choropleth_assets
from trace.tasks.charts.map import choropleth_geometry
from trace.tasks.charts.map import choropleth_geography
from trace.tasks.charts.map import choropleth_region_label
from trace.tasks.charts.map import choropleth_style


def test_choropleth_task_uses_shared_asset_loader_aliases() -> None:
    assert choropleth_region_label._load_world_map_asset is choropleth_assets.load_world_map_asset
    assert choropleth_region_label._normalize_geographic_map_variant is choropleth_assets.normalize_geographic_map_variant
    assert choropleth_assets.normalize_geographic_map_variant(choropleth_assets.WORLD_MAP_ASSET_ID) == "world_countries"


def test_choropleth_task_uses_shared_geometry_aliases() -> None:
    assert choropleth_region_label._polygon_bbox is choropleth_geometry._polygon_bbox
    assert choropleth_region_label._grid_points is choropleth_geometry._grid_points
    assert choropleth_region_label._sample_connected_cells is choropleth_geometry._sample_connected_cells

    points = choropleth_geometry._grid_points(rows=2, cols=3, map_bbox=(0, 0, 300, 200), instance_seed=17)
    assert sorted(points) == [
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, 0),
        (2, 1),
        (2, 2),
        (3, 0),
        (3, 1),
        (3, 2),
    ]
    polygon = choropleth_geometry._region_polygon(row=0, col=1, grid_points=points)
    assert choropleth_geometry._polygon_bbox(polygon)[2] > choropleth_geometry._polygon_bbox(polygon)[0]

    connected = choropleth_geometry._sample_connected_cells(
        rows=4,
        cols=4,
        target_count=5,
        rng=random.Random(23),
    )
    connected_set = set(connected)
    assert len(connected_set) == 5
    assert all(
        any(neighbor in connected_set for neighbor in choropleth_geometry._neighbors(cell, rows=4, cols=4))
        for cell in connected_set
    )


def test_choropleth_task_uses_shared_geography_aliases() -> None:
    assert choropleth_region_label._centroid_lonlat_from_rings is choropleth_geography._centroid_lonlat_from_rings
    assert choropleth_region_label._world_filtered_region_candidates is choropleth_geography._world_filtered_region_candidates
    assert choropleth_region_label._geographic_shared_border_lengths is choropleth_geography._geographic_shared_border_lengths
    assert choropleth_region_label._synthetic_region_adjacency is choropleth_geography._synthetic_region_adjacency

    centroid = choropleth_geography._centroid_lonlat_from_rings([[[0, 0], [2, 0], [2, 2], [0, 2]]])
    assert centroid == [1.0, 1.0]

    filtered = choropleth_geography._world_filtered_region_candidates(
        [
            {"region_id": "a", "continent": "Africa"},
            {"region_id": "b", "continent": "Oceania"},
        ]
    )
    assert [region["region_id"] for region in filtered] == ["a"]

    adjacency = choropleth_geography._synthetic_region_adjacency(
        {
            "r0": {"row": 0, "col": 0},
            "r1": {"row": 0, "col": 1},
            "r2": {"row": 2, "col": 2},
        }
    )
    assert adjacency["r0"] == ["r1"]
    assert adjacency["r2"] == []


def test_choropleth_style_resolvers_cover_explicit_paths() -> None:
    palette_id, probabilities, palette = choropleth_style.resolve_choropleth_palette(
        {"map_palette_rgb": [(1, 2, 3), (4, 5, 6)]},
        render_defaults={},
        task_id="test_choropleth",
        style_seed=7,
        required_palette_count=4,
        categorical=False,
    )
    assert palette_id == "custom"
    assert probabilities == {"custom": 1.0}
    assert len(palette) == 4

    style_id, style_probabilities, style = choropleth_style.resolve_choropleth_world_map_style(
        {"world_map_style": "warm_print"},
        render_defaults={},
        task_id="test_choropleth",
        instance_seed=11,
    )
    assert style_id == "warm_print"
    assert style_probabilities["warm_print"] == 1.0
    assert "ocean_rgb" in style
