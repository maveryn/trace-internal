from __future__ import annotations

from trace.core.seed import hash64
from trace.tasks import create_task


OBJECT_TASK_ID = "task_illustrations__pixel_village__object_type_count"
PATH_TASK_ID = "task_illustrations__pixel_village__person_path_count"
TERRITORY_TASK_ID = "task_illustrations__pixel_village__territory_object_count"
BUILDING_NEAR_PATH_TASK_ID = "task_illustrations__pixel_village__building_near_path_count"
TARGETS = ("building", "person", "tree", "crate", "lamp_post", "well", "pond")
TERRITORY_TARGETS = {
    "cemetery_grave_marker": ("cemetery_0", "grave marker"),
    "orchard_tree": ("orchard_0", "tree"),
    "farm_plot_crop_row": ("farm_plot_0", "crop row"),
    "farm_plot_vegetable_patch": ("farm_plot_0", "vegetable patch"),
}


def _footprint(tile_xywh: list[int]) -> set[tuple[int, int]]:
    x, y, w, h = [int(value) for value in tile_xywh]
    return {
        (xx, yy)
        for xx in range(x, x + w)
        for yy in range(y, y + h)
    }


def _expanded(tiles: set[tuple[int, int]], radius: int) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for x, y in tiles:
        for dx in range(-int(radius), int(radius) + 1):
            for dy in range(-int(radius), int(radius) + 1):
                out.add((x + dx, y + dy))
    return out


def _near_any_tile(tile_xywh: list[int], tiles: set[tuple[int, int]], distance: int) -> bool:
    x, y, w, h = [int(value) for value in tile_xywh]
    radius = int(distance)
    for tx, ty in tiles:
        nearest_x = min(max(int(tx), x), x + w - 1)
        nearest_y = min(max(int(ty), y), y + h - 1)
        if max(abs(int(tx) - nearest_x), abs(int(ty) - nearest_y)) <= radius:
            return True
    return False


def test_pixel_village_object_type_count_targets_are_metadata_grounded() -> None:
    task = create_task(OBJECT_TASK_ID)
    for index, target in enumerate(TARGETS):
        out = task.generate(
            hash64(20260609, OBJECT_TASK_ID, index),
            params={"target_object": target},
            max_attempts=80,
        )
        trace = out.trace_payload
        params = trace["query_spec"]["params"]
        counted_ids = trace["execution_trace"]["counted_entity_ids"]
        entity_bboxes = trace["render_map"]["entity_bboxes_px"]
        entities = {entity["entity_id"]: entity for entity in trace["scene_ir"]["entities"]}

        assert out.scene_id == "pixel_village"
        assert out.query_id == "object_type_count"
        assert params["target_object"] == target
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == len(counted_ids) == len(out.annotation_gt.value)
        assert int(out.answer_gt.value) > 0
        assert sorted(out.annotation_gt.value) == sorted(entity_bboxes[entity_id] for entity_id in counted_ids)
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert "villager" not in out.prompt.lower()
        if target == "tree":
            assert trace["query_spec"]["params"]["render_constraints"]["cemetery_mode"] == "none"
            assert trace["query_spec"]["params"]["renderer"]["cemetery_present"] is False
            assert all(entity["public_name"] != "dead tree" for entity in entities.values())

        for entity_id in counted_ids:
            entity = entities[entity_id]
            if target == "building":
                assert entity["category"] == "building"
            elif target == "person":
                assert entity["category"] == "person"
            else:
                assert entity["public_name"] == target.replace("_", " ")


def test_pixel_village_person_path_count_uses_path_tile_intersection() -> None:
    out = create_task(PATH_TASK_ID).generate(
        hash64(20260609, PATH_TASK_ID, 0),
        params={"path_person_count": 4},
        max_attempts=40,
    )
    trace = out.trace_payload
    counted_ids = trace["execution_trace"]["counted_entity_ids"]
    entity_bboxes = trace["render_map"]["entity_bboxes_px"]
    entities = {entity["entity_id"]: entity for entity in trace["scene_ir"]["entities"]}
    path_tiles = {tuple(int(value) for value in tile) for tile in trace["execution_trace"]["path_tiles"]}
    path_clearance = int(trace["execution_trace"]["background_person_path_clearance"])
    path_neighborhood = _expanded(path_tiles, path_clearance)

    assert out.scene_id == "pixel_village"
    assert out.query_id == "people_on_path_count"
    assert trace["query_spec"]["params"]["path_person_count"] == 4
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 4
    assert len(counted_ids) == 4
    assert path_clearance == 1
    assert sorted(out.annotation_gt.value) == sorted(entity_bboxes[entity_id] for entity_id in counted_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert "villager" not in out.prompt.lower()
    assert "path tiles" not in out.prompt.lower()

    for entity_id in counted_ids:
        entity = entities[entity_id]
        assert entity["category"] == "person"
        assert _footprint(entity["tile_xywh"]) & path_tiles

    for entity_id, entity in entities.items():
        if entity_id in set(counted_ids) or entity["category"] != "person":
            continue
        assert not (_footprint(entity["tile_xywh"]) & path_neighborhood)


def test_pixel_village_territory_object_count_targets_are_metadata_grounded() -> None:
    task = create_task(TERRITORY_TASK_ID)
    for index, (target, (territory_id, public_name)) in enumerate(TERRITORY_TARGETS.items()):
        out = task.generate(
            hash64(20260609, TERRITORY_TASK_ID, index),
            params={"territory_object": target},
            max_attempts=120,
        )
        trace = out.trace_payload
        params = trace["query_spec"]["params"]
        counted_ids = trace["execution_trace"]["counted_entity_ids"]
        entity_bboxes = trace["render_map"]["entity_bboxes_px"]
        entities = {entity["entity_id"]: entity for entity in trace["scene_ir"]["entities"]}

        assert out.scene_id == "pixel_village"
        assert out.query_id == "territory_object_count"
        assert params["territory_object"] == target
        assert params["territory_id"] == territory_id
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert 0 < int(out.answer_gt.value) <= 8
        assert int(out.answer_gt.value) == len(counted_ids) == len(out.annotation_gt.value)
        assert sorted(out.annotation_gt.value) == sorted(entity_bboxes[entity_id] for entity_id in counted_ids)
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value

        for entity_id in counted_ids:
            entity = entities[entity_id]
            assert entity["public_name"] == public_name
            assert entity["metadata"]["territory_id"] == territory_id


def test_pixel_village_building_near_path_count_uses_tile_distance() -> None:
    out = create_task(BUILDING_NEAR_PATH_TASK_ID).generate(
        hash64(20260609, BUILDING_NEAR_PATH_TASK_ID, 0),
        params={"near_path_tile_distance": 1},
        max_attempts=120,
    )
    trace = out.trace_payload
    counted_ids = trace["execution_trace"]["counted_entity_ids"]
    entity_bboxes = trace["render_map"]["entity_bboxes_px"]
    entities = {entity["entity_id"]: entity for entity in trace["scene_ir"]["entities"]}
    path_tiles = {tuple(int(value) for value in tile) for tile in trace["execution_trace"]["path_tiles"]}
    distance = int(trace["execution_trace"]["near_path_tile_distance"])

    assert out.scene_id == "pixel_village"
    assert out.query_id == "building_near_path_count"
    assert distance == 1
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert 0 < int(out.answer_gt.value) <= 8
    assert int(out.answer_gt.value) == len(counted_ids) == len(out.annotation_gt.value)
    assert sorted(out.annotation_gt.value) == sorted(entity_bboxes[entity_id] for entity_id in counted_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value

    for entity_id, entity in entities.items():
        if entity["category"] != "building":
            continue
        is_near = _near_any_tile(entity["tile_xywh"], path_tiles, distance)
        assert (entity_id in set(counted_ids)) == is_near
