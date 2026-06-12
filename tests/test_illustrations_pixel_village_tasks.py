from __future__ import annotations

from inspect import getsourcefile
from pathlib import Path

from trace.core.seed import hash64
from trace.tasks import create_task


OBJECT_TASK_ID = "task_illustrations__pixel_village__object_type_count"
PATH_TASK_ID = "task_illustrations__pixel_village__person_path_count"
TERRITORY_TASK_ID = "task_illustrations__pixel_village__territory_object_count"
RIVER_SIDE_TASK_ID = "task_illustrations__pixel_village__river_side_object_count"
TARGETS = ("building", "person", "tree", "lamp_post", "well", "pond")
RIVER_SIDE_TARGETS = ("building", "person", "tree")
RIVER_SIDES = ("left", "right", "above", "below")
RIVER_SIDE_ORIENTATION = {
    "left": "vertical",
    "right": "vertical",
    "above": "horizontal",
    "below": "horizontal",
}
TERRITORY_TARGETS = {
    "cemetery_grave_marker": ("cemetery_0", "grave marker"),
    "orchard_tree": ("orchard_0", "tree"),
}
TASK_SOURCE_STEMS = {
    OBJECT_TASK_ID: "object_type_count.py",
    PATH_TASK_ID: "person_path_count.py",
    TERRITORY_TASK_ID: "territory_object_count.py",
    RIVER_SIDE_TASK_ID: "river_side_object_count.py",
}


def _assert_scene_packaged_task(task_id: str) -> None:
    task = create_task(task_id)
    assert not hasattr(task, "scene_id")
    assert Path(getsourcefile(task.__class__) or "").as_posix().endswith(
        f"trace/tasks/illustrations/pixel_village/{TASK_SOURCE_STEMS[task_id]}"
    )


def _assert_scene_prompt_metadata(trace: dict) -> None:
    prompt_variant = trace["query_spec"]["prompt_variant"]
    assert prompt_variant["prompt_bundle_id"] == "illustrations_pixel_village_v0"
    assert prompt_variant["prompt_scene_id"] == "pixel_village"
    assert "prompt_scene_id" not in prompt_variant


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


def _strictly_on_river_side(entity: dict, *, side: str, river_bounds: dict) -> bool:
    footprint = _footprint(entity["tile_xywh"])
    xs = [x for x, _ in footprint]
    ys = [y for _, y in footprint]
    if side == "left":
        return max(xs) < int(river_bounds["min_x"])
    if side == "right":
        return min(xs) > int(river_bounds["max_x"])
    if side == "above":
        return max(ys) < int(river_bounds["min_y"])
    if side == "below":
        return min(ys) > int(river_bounds["max_y"])
    raise AssertionError(f"unexpected side: {side}")


def _matches_target(entity: dict, target: str) -> bool:
    if target == "building":
        return entity["category"] == "building"
    if target == "person":
        return entity["category"] == "person"
    return entity["public_name"] == target.replace("_", " ")


def test_pixel_village_object_type_count_targets_are_metadata_grounded() -> None:
    _assert_scene_packaged_task(OBJECT_TASK_ID)
    task = create_task(OBJECT_TASK_ID)
    for index, target in enumerate(TARGETS):
        out = task.generate(
            hash64(20260609, OBJECT_TASK_ID, index),
            params={"target_object": target},
            max_attempts=80,
        )
        trace = out.trace_payload
        _assert_scene_prompt_metadata(trace)
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
    _assert_scene_packaged_task(PATH_TASK_ID)
    out = create_task(PATH_TASK_ID).generate(
        hash64(20260609, PATH_TASK_ID, 0),
        params={"path_person_count": 4},
        max_attempts=40,
    )
    trace = out.trace_payload
    _assert_scene_prompt_metadata(trace)
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
    _assert_scene_packaged_task(TERRITORY_TASK_ID)
    task = create_task(TERRITORY_TASK_ID)
    for index, (target, (territory_id, public_name)) in enumerate(TERRITORY_TARGETS.items()):
        out = task.generate(
            hash64(20260609, TERRITORY_TASK_ID, index),
            params={"territory_object": target},
            max_attempts=120,
        )
        trace = out.trace_payload
        _assert_scene_prompt_metadata(trace)
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


def test_pixel_village_river_side_object_count_uses_strict_tile_side_membership() -> None:
    _assert_scene_packaged_task(RIVER_SIDE_TASK_ID)
    task = create_task(RIVER_SIDE_TASK_ID)
    cases = [(target, side) for target in RIVER_SIDE_TARGETS for side in RIVER_SIDES]
    for index, (target, side) in enumerate(cases):
        out = task.generate(
            hash64(20260610, RIVER_SIDE_TASK_ID, index),
            params={"target_object": target, "river_side": side},
            max_attempts=200,
        )
        trace = out.trace_payload
        _assert_scene_prompt_metadata(trace)
        params = trace["query_spec"]["params"]
        counted_ids = trace["execution_trace"]["counted_entity_ids"]
        entity_bboxes = trace["render_map"]["entity_bboxes_px"]
        entities = {entity["entity_id"]: entity for entity in trace["scene_ir"]["entities"]}
        river_bounds = trace["execution_trace"]["river_bounds"]

        assert out.scene_id == "pixel_village"
        assert out.query_id == "river_side_object_count"
        assert params["target_object"] == target
        assert params["river_side"] == side
        assert params["river_orientation"] == RIVER_SIDE_ORIENTATION[side]
        assert params["render_constraints"]["river_mode"] == "force"
        assert params["render_constraints"]["river_placement"] == "balanced"
        assert trace["query_spec"]["params"]["renderer"]["river_present"] is True
        assert trace["query_spec"]["params"]["renderer"]["river_orientation"] == RIVER_SIDE_ORIENTATION[side]
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert 0 < int(out.answer_gt.value) <= 8
        assert int(out.answer_gt.value) == len(counted_ids) == len(out.annotation_gt.value)
        assert sorted(out.annotation_gt.value) == sorted(entity_bboxes[entity_id] for entity_id in counted_ids)
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert "villager" not in out.prompt.lower()
        assert "tile" not in out.prompt.lower()
        assert "water" not in out.prompt.lower()

        expected_ids = sorted(
            entity_id
            for entity_id, entity in entities.items()
            if _matches_target(entity, target)
            and _strictly_on_river_side(entity, side=side, river_bounds=river_bounds)
        )
        assert counted_ids == expected_ids

        if target == "tree":
            assert params["render_constraints"]["cemetery_mode"] == "none"
            assert params["renderer"]["cemetery_present"] is False
            assert all(entity["public_name"] != "dead tree" for entity in entities.values())
