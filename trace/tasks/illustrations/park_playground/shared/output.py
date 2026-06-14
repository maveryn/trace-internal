"""Output trace fragments shared by park/playground public tasks."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Mapping

from ....shared.config_defaults import required_group_defaults
from .annotations import park_decor_bbox_map, park_person_bbox_map, park_scene_entities, serialize_park_scene, sort_park_bboxes
from .state import ActivitySampleSpec, AreaSampleSpec, EquipmentSampleSpec, EquipmentUseSampleSpec, ParkCountBinding


def park_render_spec(scene: Any) -> Dict[str, Any]:
    """Return the common render-spec fragment for a park scene."""

    return {
        "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
        "coord_space": "pixel",
        "scene_id": "park_playground",
        "style": {
            "setting_id": str(scene.setting_id),
            "style_id": str(scene.style_id),
            "render_scale": int(scene.render_scale),
            "layout": dict(scene.layout),
        },
    }


def park_scene_ir(
    *,
    domain: str,
    scene_id: str,
    entities: list[dict[str, Any]],
    relations: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return the common scene-IR fragment for a park scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "entities": list(entities),
        "relations": dict(relations),
    }


def bind_activity_people(scene: Any, sample: ActivitySampleSpec, prompt_defaults: Mapping[str, Any], *, context: str) -> ParkCountBinding:
    """Bind activity-count answer, witnesses, prompt slots, and trace fragments."""

    serialized_scene, person_bboxes = serialize_park_scene(scene)
    counted_person_ids = tuple(
        str(person.person_id)
        for person in scene.persons
        if str(person.activity) == str(sample.target_activity)
    )
    if len(counted_person_ids) != int(sample.target_count):
        raise RuntimeError("rendered activity count did not match sampled target count")
    annotation_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
    required_defaults = required_group_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_person_activity",
            "annotation_hint_person_activity",
            "json_example_person_activity",
            "json_example_answer_only_person_activity",
        ],
        context=f"prompt defaults for {context}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "activity_phrase": str(sample.activity_phrase),
        "json_output_contract": str(required_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(required_defaults["answer_hint_person_activity"]).format(activity_phrase=str(sample.activity_phrase)),
        "annotation_hint": str(required_defaults["annotation_hint_person_activity"]).format(activity_phrase=str(sample.activity_phrase)),
        "json_example": str(required_defaults["json_example_person_activity"]),
        "json_example_answer_only": str(required_defaults["json_example_answer_only_person_activity"]),
    }
    return ParkCountBinding(
        prompt_defaults=required_defaults,
        slots=slots,
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"person_bboxes_px": person_bboxes, "counted_person_ids": list(counted_person_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_activity": str(sample.target_activity)},
        query_params={
            "query_id": str(sample.query_id),
            "target_activity": str(sample.target_activity),
            "activity_phrase": str(sample.activity_phrase),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_activity_probabilities": dict(sample.target_activity_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": "park_playground",
            "target_activity": str(sample.target_activity),
            "target_activity_phrase": str(sample.activity_phrase),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "activity_counts": dict(Counter(str(person.activity) for person in scene.persons)),
            "counted_person_ids": list(counted_person_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_person_ids": list(counted_person_ids), "target_activity": str(sample.target_activity), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


def bind_area_people(scene: Any, sample: AreaSampleSpec, prompt_defaults: Mapping[str, Any], *, context: str) -> ParkCountBinding:
    """Bind area-count answer, witnesses, prompt slots, and trace fragments."""

    serialized_scene, person_bboxes = serialize_park_scene(scene)
    counted_person_ids = tuple(
        str(person.person_id)
        for person in scene.persons
        if str(person.attributes.get("zone")) == str(sample.target_zone)
    )
    if len(counted_person_ids) != int(sample.target_count):
        raise RuntimeError("rendered area count did not match sampled target count")
    annotation_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
    required_defaults = required_group_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_person_in_park_zone",
            "annotation_hint_person_in_park_zone",
            "json_example_person_in_park_zone",
            "json_example_answer_only_person_in_park_zone",
        ],
        context=f"prompt defaults for {context}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "zone_name": str(sample.zone_name),
        "json_output_contract": str(required_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(required_defaults["answer_hint_person_in_park_zone"]).format(zone_name=str(sample.zone_name)),
        "annotation_hint": str(required_defaults["annotation_hint_person_in_park_zone"]).format(zone_name=str(sample.zone_name)),
        "json_example": str(required_defaults["json_example_person_in_park_zone"]),
        "json_example_answer_only": str(required_defaults["json_example_answer_only_person_in_park_zone"]),
    }
    return ParkCountBinding(
        prompt_defaults=required_defaults,
        slots=slots,
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"person_bboxes_px": person_bboxes, "counted_person_ids": list(counted_person_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_zone": str(sample.target_zone)},
        query_params={
            "query_id": str(sample.query_id),
            "target_zone": str(sample.target_zone),
            "zone_name": str(sample.zone_name),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_zone_probabilities": dict(sample.target_zone_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": "park_playground",
            "target_zone": str(sample.target_zone),
            "target_zone_name": str(sample.zone_name),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "zone_counts": dict(Counter(str(person.attributes.get("zone")) for person in scene.persons)),
            "counted_person_ids": list(counted_person_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_person_ids": list(counted_person_ids), "target_zone": str(sample.target_zone), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


def bind_equipment_users(scene: Any, sample: EquipmentUseSampleSpec, prompt_defaults: Mapping[str, Any], *, context: str) -> ParkCountBinding:
    """Bind equipment-use person-count answer, witnesses, prompt slots, and trace fragments."""

    serialized_scene, person_bboxes = serialize_park_scene(scene)
    decor_bboxes = park_decor_bbox_map(scene)
    counted_person_ids = tuple(
        str(person.person_id)
        for person in scene.persons
        if str(person.attributes.get("using_equipment_type", "")) == str(sample.target_equipment_type)
    )
    if len(counted_person_ids) != int(sample.target_count):
        raise RuntimeError("rendered equipment-use count did not match sampled target count")
    annotation_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
    required_defaults = required_group_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_person_using_equipment",
            "annotation_hint_person_using_equipment",
            "json_example_person_using_equipment",
            "json_example_answer_only_person_using_equipment",
        ],
        context=f"prompt defaults for {context}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "equipment_name": str(sample.equipment_name),
        "json_output_contract": str(required_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(required_defaults["answer_hint_person_using_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "annotation_hint": str(required_defaults["annotation_hint_person_using_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "json_example": str(required_defaults["json_example_person_using_equipment"]),
        "json_example_answer_only": str(required_defaults["json_example_answer_only_person_using_equipment"]),
    }
    equipment_counts = dict(Counter(str(item.decor_type) for item in scene.decor if str(item.decor_id).startswith("equipment_")))
    return ParkCountBinding(
        prompt_defaults=required_defaults,
        slots=slots,
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"person_bboxes_px": person_bboxes, "decor_bboxes_px": decor_bboxes, "counted_person_ids": list(counted_person_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_equipment_type": str(sample.target_equipment_type)},
        query_params={
            "query_id": str(sample.query_id),
            "target_equipment_type": str(sample.target_equipment_type),
            "equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_equipment_probabilities": dict(sample.target_equipment_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "equipment_count_probabilities": dict(sample.equipment_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": "park_playground",
            "target_equipment_type": str(sample.target_equipment_type),
            "target_equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "usage_counts": dict(Counter(str(person.attributes.get("using_equipment_type", "none")) for person in scene.persons)),
            "equipment_counts": equipment_counts,
            "counted_person_ids": list(counted_person_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_person_ids": list(counted_person_ids), "target_equipment_type": str(sample.target_equipment_type), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


def bind_equipment_items(scene: Any, sample: EquipmentSampleSpec, prompt_defaults: Mapping[str, Any], *, context: str) -> ParkCountBinding:
    """Bind equipment item-count answer, witnesses, prompt slots, and trace fragments."""

    serialized_scene, _person_bboxes = serialize_park_scene(scene)
    decor_bboxes = park_decor_bbox_map(scene)
    counted_equipment_ids = tuple(
        str(item.decor_id)
        for item in scene.decor
        if str(item.decor_id).startswith("equipment_") and str(item.decor_type) == str(sample.target_equipment_type)
    )
    if len(counted_equipment_ids) != int(sample.target_count):
        raise RuntimeError("rendered equipment count did not match sampled target count")
    annotation_value = sort_park_bboxes(decor_bboxes, counted_equipment_ids)
    required_defaults = required_group_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_playground_equipment",
            "annotation_hint_playground_equipment",
            "json_example_playground_equipment",
            "json_example_answer_only_playground_equipment",
        ],
        context=f"prompt defaults for {context}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "equipment_name": str(sample.equipment_name),
        "json_output_contract": str(required_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(required_defaults["answer_hint_playground_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "annotation_hint": str(required_defaults["annotation_hint_playground_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "json_example": str(required_defaults["json_example_playground_equipment"]),
        "json_example_answer_only": str(required_defaults["json_example_answer_only_playground_equipment"]),
    }
    return ParkCountBinding(
        prompt_defaults=required_defaults,
        slots=slots,
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"decor_bboxes_px": decor_bboxes, "counted_equipment_ids": list(counted_equipment_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_equipment_type": str(sample.target_equipment_type)},
        query_params={
            "query_id": str(sample.query_id),
            "target_equipment_type": str(sample.target_equipment_type),
            "equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_equipment_probabilities": dict(sample.target_equipment_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "equipment_count_probabilities": dict(sample.equipment_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": "park_playground",
            "target_equipment_type": str(sample.target_equipment_type),
            "target_equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "equipment_counts": dict(Counter(str(item.decor_type) for item in scene.decor if str(item.decor_id).startswith("equipment_"))),
            "counted_equipment_ids": list(counted_equipment_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_equipment_ids": list(counted_equipment_ids), "target_equipment_type": str(sample.target_equipment_type), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


__all__ = [
    "bind_activity_people",
    "bind_area_people",
    "bind_equipment_items",
    "bind_equipment_users",
    "park_render_spec",
    "park_scene_ir",
]
