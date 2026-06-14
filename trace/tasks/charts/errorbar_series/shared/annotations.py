"""Annotation projection helpers for error-bar series scenes."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.charts.errorbar_series.shared.state import ErrorbarDataset, ErrorbarRendered


def annotation_payload(
    *,
    dataset: ErrorbarDataset,
    rendered: ErrorbarRendered,
) -> tuple[str, Any, dict[str, Any], list[dict[str, Any]]]:
    """Project task-bound symbolic mark keys into pixel annotation payloads."""

    if str(dataset.query.annotation_kind) == "bbox_set":
        boxes = []
        refs = []
        for key in dataset.query.annotation_item_keys:
            if str(key) not in rendered.errorbar_bboxes_px:
                raise RuntimeError(f"missing errorbar bbox for {key}")
            boxes.append(list(rendered.errorbar_bboxes_px[str(key)]))
            refs.append({"key": str(key), "bbox_px": list(rendered.errorbar_bboxes_px[str(key)])})
        projected = {"type": "bbox_set", "bbox_set": list(boxes), "pixel_bbox_set": list(boxes), "annotation_refs": list(refs)}
        return "bbox_set", list(boxes), dict(projected), [dict(ref) for ref in refs]

    if str(dataset.query.annotation_kind) == "keyed_point_map":
        key = str(dataset.query.annotation_item_keys[0])
        series_label, x_label = key.split(":", 1)
        bound_kind = str(dataset.query.params["bound_kind"])
        point = list(rendered.point_map_px[str(series_label)][str(x_label)][f"{bound_kind}_bound"])
        value = {"selected_bound_endpoint": list(point)}
        refs = [{"key": str(key), "series_label": str(series_label), "x_label": str(x_label), "point_xy": list(point)}]
        projected = {
            "type": "keyed_point_map",
            "keyed_point_map": dict(value),
            "pixel_keyed_point_map": dict(value),
            "annotation_refs": list(refs),
        }
        return "keyed_point_map", dict(value), dict(projected), [dict(ref) for ref in refs]

    if str(dataset.query.annotation_kind) == "keyed_bbox_map":
        mapping: Dict[str, list[float]] = {}
        refs = []
        for index, key in enumerate(dataset.query.annotation_item_keys):
            if str(key) not in rendered.errorbar_bboxes_px:
                raise RuntimeError(f"missing errorbar bbox for {key}")
            role = "target_errorbar" if int(index) == 0 else str(key).split(":", 1)[0]
            mapping[str(role)] = list(rendered.errorbar_bboxes_px[str(key)])
            refs.append({"key": str(key), "role": str(role), "bbox_px": list(rendered.errorbar_bboxes_px[str(key)])})
        projected = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(mapping),
            "pixel_keyed_bbox_map": dict(mapping),
            "annotation_refs": list(refs),
        }
        return "keyed_bbox_map", dict(mapping), dict(projected), [dict(ref) for ref in refs]

    raise ValueError(f"unsupported annotation kind: {dataset.query.annotation_kind}")


__all__ = ["annotation_payload"]
