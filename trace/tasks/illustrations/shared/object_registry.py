"""Global illustration object taxonomy and normalized record helpers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from .object_catalog import canonical_entry_for_object_type
from .object_library import OBJECT_TEMPLATES, display_name_for_object_type
from .object_schema import BBox, ObjectAttributeDef, ObjectRecord, ObjectTypeDef


def _attrs(*names: str, public: bool = True) -> Tuple[ObjectAttributeDef, ...]:
    return tuple(ObjectAttributeDef(str(name), public=bool(public)) for name in names)


def _base_object_defs() -> Dict[str, ObjectTypeDef]:
    return {
        str(object_type): ObjectTypeDef(
            object_type=str(object_type),
            public_name=display_name_for_object_type(str(object_type)),
            family=str(template.family),
            visual_attributes=_attrs("primary_color_rgb", "accent_color_rgb", "style_id"),
        )
        for object_type, template in sorted(OBJECT_TEMPLATES.items())
    }


_SCENE_OBJECT_DEFS: Dict[str, ObjectTypeDef] = {
    "boarding_area": ObjectTypeDef(
        "boarding_area",
        "boarding area",
        "scene_region",
        semantic_attributes=_attrs("area_id", "display_name"),
    ),
    "book": ObjectTypeDef(
        "book",
        "book",
        "object",
        semantic_attributes=_attrs("section_id", "section_key", "section_name", "color_name", "color_label", "orientation"),
        visual_attributes=_attrs("primary_color_rgb", "accent_color_rgb", "style_id", "color_rgb"),
    ),
    "building": ObjectTypeDef(
        "building",
        "building",
        "structure",
        semantic_attributes=_attrs("roof_type", "window_count", "lit_window_count"),
    ),
    "construction_equipment": ObjectTypeDef(
        "construction_equipment",
        "construction equipment",
        "equipment",
        semantic_attributes=_attrs("equipment_type", "equipment_label", "zone_id"),
        visual_attributes=_attrs("style_id"),
    ),
    "construction_material": ObjectTypeDef(
        "construction_material",
        "construction material",
        "material",
        semantic_attributes=_attrs("material_type", "material_label"),
        visual_attributes=_attrs("style_id"),
    ),
    "container": ObjectTypeDef(
        "container",
        "container",
        "fixture",
        semantic_attributes=_attrs("container_type", "label"),
    ),
    "decor": ObjectTypeDef(
        "decor",
        "decor",
        "support",
        semantic_attributes=_attrs("decor_type"),
    ),
    "environment_feature": ObjectTypeDef(
        "environment_feature",
        "environment feature",
        "scene_region",
        semantic_attributes=_attrs("feature_type"),
    ),
    "furniture": ObjectTypeDef(
        "furniture",
        "furniture",
        "fixture",
        semantic_attributes=_attrs("furniture_type", "label"),
    ),
    "library_section": ObjectTypeDef(
        "library_section",
        "library section",
        "scene_region",
        semantic_attributes=_attrs("section_key", "section_name", "label"),
    ),
    "luggage": ObjectTypeDef(
        "luggage",
        "luggage",
        "object",
        semantic_attributes=_attrs("luggage_type", "area_id"),
        visual_attributes=_attrs("primary_color_rgb"),
    ),
    "market_item": ObjectTypeDef(
        "market_item",
        "market item",
        "object",
        semantic_attributes=_attrs("item_type", "item_name", "shop_id", "slot_index"),
        visual_attributes=_attrs("color_rgb", "accent_color_rgb"),
    ),
    "person": ObjectTypeDef(
        "person",
        "person",
        "person",
        semantic_attributes=_attrs("activity", "activity_label", "area_id", "pose_id", "zone", "near_shop_id", "near_shop_type"),
        visual_attributes=_attrs("primary_color_rgb", "accent_color_rgb", "skin_color_rgb", "style_id", "gender_id"),
    ),
    "pedestrian_with_bag": ObjectTypeDef(
        "pedestrian_with_bag",
        "pedestrian with bag",
        "person",
        semantic_attributes=_attrs("activity", "activity_label", "area_id", "pose_id", "zone", "near_shop_id", "near_shop_type"),
        visual_attributes=_attrs("primary_color_rgb", "accent_color_rgb", "skin_color_rgb", "style_id", "gender_id"),
    ),
    "playground_equipment": ObjectTypeDef(
        "playground_equipment",
        "playground equipment",
        "equipment",
        semantic_attributes=_attrs("equipment_type", "equipment_label", "zone"),
    ),
    "service_point": ObjectTypeDef(
        "service_point",
        "service point",
        "fixture",
        semantic_attributes=_attrs("service_point_id", "display_name"),
    ),
    "shop": ObjectTypeDef(
        "shop",
        "shop",
        "structure",
        semantic_attributes=_attrs("shop_type", "shop_name", "item_types"),
        visual_attributes=_attrs("signboard_color_rgb", "awning_color_rgb", "facade_color_rgb"),
    ),
    "surface": ObjectTypeDef(
        "surface",
        "surface",
        "fixture",
        semantic_attributes=_attrs("surface_type", "label", "furniture_id"),
    ),
    "worker": ObjectTypeDef(
        "worker",
        "worker",
        "person",
        semantic_attributes=_attrs("hard_hat_color", "vest_color", "tool_type"),
        visual_attributes=_attrs("style_id", "gender_id"),
    ),
    "zone": ObjectTypeDef(
        "zone",
        "zone",
        "scene_region",
        semantic_attributes=_attrs("zone_id", "label", "zone_type"),
        visual_attributes=_attrs("fill_rgb", "outline_rgb"),
    ),
}

def _with_catalog_defaults(definition: ObjectTypeDef) -> ObjectTypeDef:
    entry = canonical_entry_for_object_type(str(definition.object_type))
    if entry is None:
        return definition
    return ObjectTypeDef(
        object_type=str(definition.object_type),
        public_name=str(definition.public_name),
        family=str(definition.family),
        render_layer=str(entry.render_layer),
        size_class=str(entry.size_class),
        placement_tags=tuple(entry.placement_tags),
        scene_tags=tuple(entry.scene_tags),
        semantic_attributes=tuple(definition.semantic_attributes),
        visual_attributes=tuple(definition.visual_attributes),
        aliases=tuple(definition.aliases),
    )


_OBJECT_DEFS: Dict[str, ObjectTypeDef] = {
    key: _with_catalog_defaults(value)
    for key, value in {**_base_object_defs(), **_SCENE_OBJECT_DEFS}.items()
}


def registered_object_types() -> Tuple[str, ...]:
    """Return all globally registered illustration object type ids."""

    return tuple(sorted(_OBJECT_DEFS))


def object_type_definition(object_type: str) -> ObjectTypeDef:
    """Return a registered object type, falling back to a generic support object."""

    key = str(object_type)
    if key in _OBJECT_DEFS:
        return _OBJECT_DEFS[key]
    return ObjectTypeDef(key, key.replace("_", " "), "support", semantic_attributes=_attrs("source_type"))


def public_name_for_object_type(object_type: str) -> str:
    """Return the public display name for an object type."""

    return str(object_type_definition(str(object_type)).public_name)


def family_for_object_type(object_type: str) -> str:
    """Return the public object family for an object type."""

    return str(object_type_definition(str(object_type)).family)


def make_object_record(
    *,
    object_id: str,
    object_type: str,
    bbox_xyxy: Sequence[float] | None,
    semantic_attributes: Mapping[str, Any] | None = None,
    visual_attributes: Mapping[str, Any] | None = None,
    public_name: str | None = None,
    family: str | None = None,
    role: str = "distractor",
    source_entity_type: str = "",
    parts: Sequence[Mapping[str, Any]] = (),
) -> ObjectRecord:
    """Build a normalized object record from scene-specific metadata."""

    definition = object_type_definition(str(object_type))
    bbox: BBox | None = None
    if bbox_xyxy is not None:
        values = tuple(float(value) for value in bbox_xyxy)
        if len(values) != 4:
            raise ValueError("bbox_xyxy must contain exactly four values")
        bbox = values  # type: ignore[assignment]
    return ObjectRecord(
        object_id=str(object_id),
        object_type=str(object_type),
        public_name=str(public_name if public_name is not None else definition.public_name),
        family=str(family if family is not None else definition.family),
        bbox_xyxy=bbox,
        semantic_attributes=dict(semantic_attributes or {}),
        visual_attributes=dict(visual_attributes or {}),
        role=str(role),
        source_entity_type=str(source_entity_type),
        parts=tuple(dict(part) for part in parts),
    )


__all__ = [
    "family_for_object_type",
    "make_object_record",
    "object_type_definition",
    "public_name_for_object_type",
    "registered_object_types",
]
