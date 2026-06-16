"""Scene-neutral patch membership option mechanics for illustrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

from .canvas_profiles import resize_to_max_pixels, scale_bbox, scale_bbox_map
from .cutouts import DEFAULT_OPTION_LABELS, FRAMELESS_ILLUSTRATION_PATCH_STYLE, option_grid_shape, patch_difference_score, rgb
from .option_rendering import bbox_list, draw_label_badge, image_detail_score


EXACT_SOURCE_PATCH_QUERY_ID = "exact_source_patch_label"
ALTERED_PATCH_QUERY_ID = "altered_patch_label"
PATCH_MEMBERSHIP_QUERY_IDS: Tuple[str, ...] = (EXACT_SOURCE_PATCH_QUERY_ID, ALTERED_PATCH_QUERY_ID)
PATCH_PROVENANCE_EXACT = "exact"
PATCH_PROVENANCE_ALTERED = "altered"


@dataclass(frozen=True)
class EditablePatchObject:
    """One source-scene object that can safely drive local patch edits."""

    object_id: str
    object_type: str
    bbox_xyxy: Tuple[float, float, float, float]
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PatchAlterationRecord:
    """Trace record for one applied patch alteration family."""

    family: str
    action: str
    object_ids: Tuple[str, ...]
    source_bboxes: Tuple[Tuple[int, int, int, int], ...]
    target_bboxes: Tuple[Tuple[int, int, int, int], ...]
    changed_fraction: float
    difference_score: float
    details: Mapping[str, Any] = field(default_factory=dict)

    def trace(self) -> Dict[str, Any]:
        return {
            "family": str(self.family),
            "action": str(self.action),
            "object_ids": [str(value) for value in self.object_ids],
            "source_bboxes": [[int(coord) for coord in box] for box in self.source_bboxes],
            "target_bboxes": [[int(coord) for coord in box] for box in self.target_bboxes],
            "changed_fraction": round(float(self.changed_fraction), 5),
            "difference_score": round(float(self.difference_score), 3),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class PatchMembershipArtifacts:
    """Composed source-plus-options image and verifier metadata."""

    image: Image.Image
    option_bboxes: Dict[str, list[float]]
    selected_option_bbox: list[float]
    selected_label: str
    selected_index: int
    source_image_bbox: list[float]
    option_source_crop_boxes: Dict[str, Tuple[int, int, int, int]]
    option_provenance: Dict[str, str]
    option_alterations: Dict[str, Tuple[PatchAlterationRecord, ...]]
    option_grid_shape: Tuple[int, int]
    candidate_crop_count: int
    output_scale_xy: Tuple[float, float] = (1.0, 1.0)
    pre_downscale_canvas_size: Tuple[int, int] = (0, 0)


PatchObjectDrawCallback = Callable[[ImageDraw.ImageDraw, Any, Tuple[int, int, int, int], int], Mapping[str, Any]]


def _bbox_tuple(box: Sequence[float]) -> Tuple[float, float, float, float]:
    return tuple(float(value) for value in box[:4])  # type: ignore[return-value]


def _box_area(box: Sequence[float]) -> float:
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def _object_inside_crop(
    obj: EditablePatchObject,
    crop_box: Sequence[int],
    *,
    padding: int,
    patch_area: float,
) -> bool:
    x0, y0, x1, y1 = _bbox_tuple(obj.bbox_xyxy)
    cx0, cy0, cx1, cy1 = [float(value) for value in crop_box[:4]]
    w = x1 - x0
    h = y1 - y0
    if w < 10.0 or h < 10.0:
        return False
    if _box_area((x0, y0, x1, y1)) > float(patch_area) * 0.34:
        return False
    return (
        x0 >= cx0 + float(padding)
        and y0 >= cy0 + float(padding)
        and x1 <= cx1 - float(padding)
        and y1 <= cy1 - float(padding)
    )


def _objects_inside_crop(
    objects: Sequence[EditablePatchObject],
    crop_box: Sequence[int],
    *,
    padding: int,
) -> Tuple[EditablePatchObject, ...]:
    patch_area = float(max(1, int(crop_box[2]) - int(crop_box[0])) * max(1, int(crop_box[3]) - int(crop_box[1])))
    return tuple(
        obj
        for obj in objects
        if _object_inside_crop(obj, crop_box, padding=int(padding), patch_area=float(patch_area))
    )


def _local_box(obj: EditablePatchObject, crop_box: Sequence[int]) -> Tuple[int, int, int, int]:
    cx0, cy0 = int(crop_box[0]), int(crop_box[1])
    x0, y0, x1, y1 = _bbox_tuple(obj.bbox_xyxy)
    return (
        int(round(x0 - cx0)),
        int(round(y0 - cy0)),
        int(round(x1 - cx0)),
        int(round(y1 - cy0)),
    )


def _global_from_local(local_box: Sequence[int], crop_box: Sequence[int]) -> Tuple[int, int, int, int]:
    cx0, cy0 = int(crop_box[0]), int(crop_box[1])
    return (
        int(local_box[0]) + cx0,
        int(local_box[1]) + cy0,
        int(local_box[2]) + cx0,
        int(local_box[3]) + cy0,
    )


def _mean_rgb(image: Image.Image, box: Sequence[int] | None = None) -> Tuple[int, int, int]:
    sample = image.crop(tuple(int(v) for v in box[:4])) if box is not None else image
    stat = ImageStat.Stat(sample.convert("RGB"))
    mean = stat.mean or [242.0, 242.0, 242.0]
    return tuple(max(0, min(255, int(round(value)))) for value in mean[:3])  # type: ignore[return-value]


def _fill_rgb_for_box(image: Image.Image, box: Sequence[int]) -> Tuple[int, int, int]:
    x0, y0, x1, y1 = [int(value) for value in box[:4]]
    pad = max(8, int(round(min(max(1, x1 - x0), max(1, y1 - y0)) * 0.28)))
    ex0 = max(0, x0 - pad)
    ey0 = max(0, y0 - pad)
    ex1 = min(int(image.width), x1 + pad)
    ey1 = min(int(image.height), y1 + pad)
    return _mean_rgb(image, (ex0, ey0, ex1, ey1))


def _object_mask_for_box(image: Image.Image, box: Sequence[int]) -> Image.Image:
    x0, y0, x1, y1 = [int(value) for value in box[:4]]
    crop = image.crop((x0, y0, x1, y1)).convert("RGB")
    fill = _fill_rgb_for_box(image, box)
    background = Image.new("RGB", crop.size, fill)
    diff = ImageChops.difference(crop, background).convert("L")
    mask = diff.point(lambda value: 255 if int(value) >= 18 else 0)
    return mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))


def _changed_fraction(left: Image.Image, right: Image.Image) -> float:
    diff = ImageChops.difference(left.convert("RGB"), right.convert("RGB")).convert("L")
    hist = diff.histogram()
    changed = sum(count for value, count in enumerate(hist) if value >= 14)
    return float(changed) / float(max(1, int(diff.width) * int(diff.height)))


def _patch_delta(left: Image.Image, right: Image.Image) -> Tuple[float, float]:
    return patch_difference_score(left, right), _changed_fraction(left, right)


def _shuffle(values: Sequence[Any], rng: Any) -> list[Any]:
    items = list(values)
    rng.shuffle(items)
    return items


def _choose_targets(
    targets: Sequence[EditablePatchObject],
    rng: Any,
    *,
    min_count: int,
    max_count: int,
) -> Tuple[EditablePatchObject, ...]:
    if len(targets) < int(min_count):
        return tuple()
    items = _shuffle(targets, rng)
    count = int(rng.randint(int(min_count), min(int(max_count), len(items))))
    return tuple(items[:count])


def _non_overlapping_add_boxes(
    *,
    rng: Any,
    patch_size: Tuple[int, int],
    existing_boxes: Sequence[Sequence[int]],
    count: int,
) -> Tuple[Tuple[int, int, int, int], ...]:
    patch_w, patch_h = int(patch_size[0]), int(patch_size[1])
    boxes: list[Tuple[int, int, int, int]] = []
    occupied = [tuple(int(v) for v in box[:4]) for box in existing_boxes]
    for _attempt in range(180):
        if len(boxes) >= int(count):
            break
        side = int(rng.randint(18, 34))
        x0 = int(rng.randint(8, max(8, patch_w - side - 8)))
        y0 = int(rng.randint(8, max(8, patch_h - side - 8)))
        box = (x0, y0, x0 + side, y0 + side)
        if any(_boxes_overlap(box, other, gap=5) for other in [*occupied, *boxes]):
            continue
        boxes.append(box)
    return tuple(boxes)


def _boxes_overlap(a: Sequence[int], b: Sequence[int], *, gap: int = 0) -> bool:
    return not (
        int(a[2]) + int(gap) <= int(b[0])
        or int(b[2]) + int(gap) <= int(a[0])
        or int(a[3]) + int(gap) <= int(b[1])
        or int(b[3]) + int(gap) <= int(a[1])
    )


def _draw_generic_added_object(draw: ImageDraw.ImageDraw, rng: Any, box: Tuple[int, int, int, int], index: int) -> Mapping[str, Any]:
    palette = ((230, 82, 73), (72, 139, 221), (244, 183, 63), (86, 171, 105), (173, 100, 198))
    fill = tuple(int(v) for v in rng.choice(palette))
    outline = (45, 54, 66)
    x0, y0, x1, y1 = [int(v) for v in box]
    if int(index) % 3 == 0:
        draw.ellipse((x0, y0, x1, y1), fill=fill, outline=outline, width=2)
        return {"object_type": "added_ball", "fill_rgb": list(fill)}
    if int(index) % 3 == 1:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=max(2, (x1 - x0) // 5), fill=fill, outline=outline, width=2)
        return {"object_type": "added_block", "fill_rgb": list(fill)}
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    draw.polygon(((cx, y0), (x1, cy), (cx, y1), (x0, cy)), fill=fill, outline=outline)
    return {"object_type": "added_marker", "fill_rgb": list(fill)}


def _apply_recolor(
    patch: Image.Image,
    original: Image.Image,
    *,
    crop_box: Sequence[int],
    targets: Sequence[EditablePatchObject],
    rng: Any,
    min_edit_objects: int,
    max_edit_objects: int,
) -> Tuple[Image.Image, PatchAlterationRecord] | None:
    selected = _choose_targets(targets, rng, min_count=int(min_edit_objects), max_count=int(max_edit_objects))
    if not selected:
        return None
    before = patch.copy()
    overlay = Image.new("RGBA", patch.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    palette = ((230, 76, 68), (50, 144, 221), (244, 177, 64), (80, 169, 99), (172, 96, 201))
    local_boxes = []
    global_boxes = []
    for index, obj in enumerate(selected):
        box = _local_box(obj, crop_box)
        local_boxes.append(box)
        global_boxes.append(_global_from_local(box, crop_box))
        color = tuple(int(v) for v in palette[(int(rng.randint(0, len(palette) - 1)) + index) % len(palette)])
        mask = _object_mask_for_box(patch, box)
        local_crop = patch.crop(box).convert("RGB")
        color_crop = Image.new("RGB", local_crop.size, color)
        recolored = Image.blend(local_crop, color_crop, 0.58)
        overlay.paste(recolored.convert("RGBA"), (box[0], box[1]), mask)
    edited = patch.copy()
    edited.paste(Image.alpha_composite(patch.convert("RGBA"), overlay).convert("RGB"))
    score, changed = _patch_delta(original, edited)
    return (
        edited,
        PatchAlterationRecord(
            family="object_recolor",
            action="recolor",
            object_ids=tuple(str(obj.object_id) for obj in selected),
            source_bboxes=tuple(global_boxes),
            target_bboxes=tuple(global_boxes),
            changed_fraction=float(changed),
            difference_score=float(score),
            details={"local_bboxes": [[int(v) for v in box] for box in local_boxes]},
        ),
    )


def _apply_remove(
    patch: Image.Image,
    original: Image.Image,
    *,
    crop_box: Sequence[int],
    targets: Sequence[EditablePatchObject],
    rng: Any,
    min_edit_objects: int,
    max_edit_objects: int,
) -> Tuple[Image.Image, PatchAlterationRecord] | None:
    selected = _choose_targets(targets, rng, min_count=int(min_edit_objects), max_count=int(max_edit_objects))
    if not selected:
        return None
    edited = patch.copy()
    draw = ImageDraw.Draw(edited)
    global_boxes = []
    local_boxes = []
    for obj in selected:
        box = _local_box(obj, crop_box)
        local_boxes.append(box)
        global_boxes.append(_global_from_local(box, crop_box))
        fill = _fill_rgb_for_box(edited, box)
        fill_image = Image.new("RGB", (max(1, box[2] - box[0]), max(1, box[3] - box[1])), fill)
        edited.paste(fill_image, (box[0], box[1]), _object_mask_for_box(edited, box))
    score, changed = _patch_delta(original, edited)
    return (
        edited,
        PatchAlterationRecord(
            family="small_object_presence_edit",
            action="remove",
            object_ids=tuple(str(obj.object_id) for obj in selected),
            source_bboxes=tuple(global_boxes),
            target_bboxes=tuple(),
            changed_fraction=float(changed),
            difference_score=float(score),
            details={"local_bboxes": [[int(v) for v in box] for box in local_boxes]},
        ),
    )


def _apply_add(
    patch: Image.Image,
    original: Image.Image,
    *,
    crop_box: Sequence[int],
    targets: Sequence[EditablePatchObject],
    rng: Any,
    min_edit_objects: int,
    max_edit_objects: int,
    draw_added_object: PatchObjectDrawCallback | None,
) -> Tuple[Image.Image, PatchAlterationRecord] | None:
    count = int(rng.randint(int(min_edit_objects), int(max_edit_objects)))
    existing = [_local_box(obj, crop_box) for obj in targets]
    add_boxes = _non_overlapping_add_boxes(rng=rng, patch_size=patch.size, existing_boxes=existing, count=count)
    if len(add_boxes) < int(min_edit_objects):
        return None
    edited = patch.copy()
    draw = ImageDraw.Draw(edited)
    records = []
    global_boxes = []
    callback = draw_added_object or _draw_generic_added_object
    for index, box in enumerate(add_boxes[:count]):
        records.append(dict(callback(draw, rng, box, index)))
        global_boxes.append(_global_from_local(box, crop_box))
    score, changed = _patch_delta(original, edited)
    return (
        edited,
        PatchAlterationRecord(
            family="small_object_presence_edit",
            action="add",
            object_ids=tuple(f"added_{index}" for index in range(len(global_boxes))),
            source_bboxes=tuple(),
            target_bboxes=tuple(global_boxes),
            changed_fraction=float(changed),
            difference_score=float(score),
            details={"added_objects": records},
        ),
    )


def _apply_shift(
    patch: Image.Image,
    original: Image.Image,
    *,
    crop_box: Sequence[int],
    targets: Sequence[EditablePatchObject],
    rng: Any,
    min_edit_objects: int,
    max_edit_objects: int,
) -> Tuple[Image.Image, PatchAlterationRecord] | None:
    selected = _choose_targets(targets, rng, min_count=int(min_edit_objects), max_count=int(max_edit_objects))
    if not selected:
        return None
    edited = patch.copy()
    draw = ImageDraw.Draw(edited)
    source_boxes = []
    target_boxes = []
    object_ids = []
    for obj in selected:
        box = _local_box(obj, crop_box)
        w = int(box[2] - box[0])
        h = int(box[3] - box[1])
        min_delta = max(12, int(round(min(w, h) * 0.35)))
        candidates = []
        for _attempt in range(24):
            dx = int(rng.choice((-1, 1)) * rng.randint(min_delta, max(min_delta, min(46, max(min_delta, patch.width // 4)))))
            dy = int(rng.choice((-1, 1)) * rng.randint(min_delta, max(min_delta, min(40, max(min_delta, patch.height // 4)))))
            target = (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)
            if target[0] >= 3 and target[1] >= 3 and target[2] <= patch.width - 3 and target[3] <= patch.height - 3:
                candidates.append(target)
        if not candidates:
            continue
        target_box = candidates[int(rng.randint(0, len(candidates) - 1))]
        object_crop = edited.crop(box)
        mask = _object_mask_for_box(edited, box)
        fill_image = Image.new("RGB", (max(1, box[2] - box[0]), max(1, box[3] - box[1])), _fill_rgb_for_box(edited, box))
        edited.paste(fill_image, (box[0], box[1]), mask)
        edited.paste(object_crop, (target_box[0], target_box[1]), mask)
        source_boxes.append(_global_from_local(box, crop_box))
        target_boxes.append(_global_from_local(target_box, crop_box))
        object_ids.append(str(obj.object_id))
    if len(source_boxes) < int(min_edit_objects):
        return None
    score, changed = _patch_delta(original, edited)
    return (
        edited,
        PatchAlterationRecord(
            family="object_placement_change",
            action="move",
            object_ids=tuple(object_ids),
            source_bboxes=tuple(source_boxes),
            target_bboxes=tuple(target_boxes),
            changed_fraction=float(changed),
            difference_score=float(score),
        ),
    )


def _alter_patch(
    patch: Image.Image,
    *,
    crop_box: Sequence[int],
    targets: Sequence[EditablePatchObject],
    rng: Any,
    edit_family_count_support: Sequence[int],
    min_edit_objects: int,
    max_edit_objects: int,
    min_changed_fraction: float,
    max_changed_fraction: float,
    min_difference_score: float,
    draw_added_object: PatchObjectDrawCallback | None,
) -> Tuple[Image.Image, Tuple[PatchAlterationRecord, ...]]:
    support = tuple(int(value) for value in edit_family_count_support if int(value) > 0)
    if not support:
        support = (1,)
    family_count = int(rng.choice(support))
    families = _shuffle(
        ("small_object_presence_edit", "object_recolor", "object_placement_change"),
        rng,
    )[:family_count]
    edited = patch.copy()
    records: list[PatchAlterationRecord] = []
    for family in families:
        if family == "small_object_presence_edit":
            action = str(rng.choice(("add", "remove")))
            result = (
                _apply_add(
                    edited,
                    patch,
                    crop_box=crop_box,
                    targets=targets,
                    rng=rng,
                    min_edit_objects=int(min_edit_objects),
                    max_edit_objects=int(max_edit_objects),
                    draw_added_object=draw_added_object,
                )
                if action == "add"
                else _apply_remove(
                    edited,
                    patch,
                    crop_box=crop_box,
                    targets=targets,
                    rng=rng,
                    min_edit_objects=int(min_edit_objects),
                    max_edit_objects=int(max_edit_objects),
                )
            )
        elif family == "object_recolor":
            result = _apply_recolor(
                edited,
                patch,
                crop_box=crop_box,
                targets=targets,
                rng=rng,
                min_edit_objects=int(min_edit_objects),
                max_edit_objects=int(max_edit_objects),
            )
        else:
            result = _apply_shift(
                edited,
                patch,
                crop_box=crop_box,
                targets=targets,
                rng=rng,
                min_edit_objects=int(min_edit_objects),
                max_edit_objects=int(max_edit_objects),
            )
        if result is None:
            continue
        edited, record = result
        records.append(record)
    score, changed = _patch_delta(patch, edited)
    if not records:
        raise ValueError("no patch alteration could be applied")
    if score < float(min_difference_score) or changed < float(min_changed_fraction) or changed > float(max_changed_fraction):
        raise ValueError("patch alteration failed visual delta constraints")
    return edited, tuple(records)


def _select_crop_box_with_detail(
    source: Image.Image,
    rng: Any,
    *,
    patch_w: int,
    patch_h: int,
    crop_margin_px: int,
    edit_objects: Sequence[EditablePatchObject],
    used_crop_boxes: Sequence[Sequence[int]],
    require_editable: bool,
    min_crop_detail_score: float,
    min_edit_objects: int,
    crop_padding_px: int,
) -> Tuple[Tuple[int, int, int, int], Tuple[EditablePatchObject, ...], int]:
    source_w, source_h = source.size
    margin = int(crop_margin_px)
    max_x0 = int(source_w) - int(patch_w) - margin
    max_y0 = int(source_h) - int(patch_h) - margin
    if max_x0 < margin or max_y0 < margin:
        raise ValueError("crop_margin_px leaves no feasible source crop area")
    used = {tuple(int(v) for v in box[:4]) for box in used_crop_boxes}
    best: Tuple[float, Tuple[int, int, int, int], Tuple[EditablePatchObject, ...]] | None = None
    attempts = 0
    for attempts in range(1, 421):
        if edit_objects and (bool(require_editable) or float(rng.random()) < 0.78):
            obj = edit_objects[int(rng.randint(0, len(edit_objects) - 1))]
            ox0, oy0, ox1, oy1 = _bbox_tuple(obj.bbox_xyxy)
            min_x = max(margin, int(math_floor(ox1 - patch_w + crop_padding_px)))
            max_x = min(max_x0, int(math_ceil(ox0 - crop_padding_px)))
            min_y = max(margin, int(math_floor(oy1 - patch_h + crop_padding_px)))
            max_y = min(max_y0, int(math_ceil(oy0 - crop_padding_px)))
            if min_x > max_x or min_y > max_y:
                continue
            x0 = int(rng.randint(min_x, max_x))
            y0 = int(rng.randint(min_y, max_y))
        else:
            x0 = int(rng.randint(margin, max_x0))
            y0 = int(rng.randint(margin, max_y0))
        box = (x0, y0, x0 + int(patch_w), y0 + int(patch_h))
        if tuple(box) in used:
            continue
        patch = source.crop(box)
        score = float(image_detail_score(patch))
        targets = _objects_inside_crop(edit_objects, box, padding=int(crop_padding_px))
        if require_editable and len(targets) < int(min_edit_objects):
            continue
        if best is None or score > best[0]:
            best = (score, box, targets)
        if score >= float(min_crop_detail_score):
            return box, targets, attempts
    if best is not None and (not bool(require_editable) or len(best[2]) >= int(min_edit_objects)):
        return best[1], best[2], attempts
    raise ValueError("could not select a sufficiently detailed source patch")


def math_floor(value: float) -> int:
    return int(value // 1)


def math_ceil(value: float) -> int:
    return int(-(-float(value) // 1))


def compose_source_patch_membership_options(
    *,
    source_image: Image.Image,
    rng: Any,
    query_id: str,
    correct_index: int,
    option_count: int,
    patch_size: Tuple[int, int],
    crop_margin_px: int,
    edit_objects: Sequence[EditablePatchObject],
    frame_style: Mapping[str, Any] | None = None,
    label_font_family: str | None = None,
    labels: Sequence[str] = DEFAULT_OPTION_LABELS,
    render_margin: int = 24,
    option_gap: int = 24,
    source_option_gap: int = 34,
    option_label_height: int = 30,
    draw_option_outlines: bool = True,
    min_crop_detail_score: float = 220.0,
    min_patch_difference_score: float = 8.0,
    min_changed_fraction: float = 0.03,
    max_changed_fraction: float = 0.55,
    min_edit_objects: int = 2,
    max_edit_objects: int = 4,
    crop_padding_px: int = 7,
    edit_family_count_support: Sequence[int] = (1, 2),
    draw_added_object: PatchObjectDrawCallback | None = None,
) -> PatchMembershipArtifacts:
    """Compose an intact source illustration plus exact/altered crop options."""

    if str(query_id) not in set(PATCH_MEMBERSHIP_QUERY_IDS):
        raise ValueError(f"query_id must be one of {PATCH_MEMBERSHIP_QUERY_IDS}")
    if int(option_count) < 2 or int(option_count) > len(labels):
        raise ValueError("option_count outside label support")
    if int(correct_index) < 0 or int(correct_index) >= int(option_count):
        raise ValueError("correct_index outside option range")

    style = dict(frame_style or FRAMELESS_ILLUSTRATION_PATCH_STYLE)
    source_rgb = source_image.convert("RGB")
    patch_w, patch_h = int(patch_size[0]), int(patch_size[1])
    label_values = tuple(str(label) for label in labels[: int(option_count)])
    selected_exact = str(query_id) == EXACT_SOURCE_PATCH_QUERY_ID

    options: list[Image.Image] = []
    option_source_crop_boxes: Dict[str, Tuple[int, int, int, int]] = {}
    option_provenance: Dict[str, str] = {}
    option_alterations: Dict[str, Tuple[PatchAlterationRecord, ...]] = {}
    used_crop_boxes: list[Tuple[int, int, int, int]] = []
    candidate_crop_count = 0

    for index, label in enumerate(label_values):
        provenance = PATCH_PROVENANCE_EXACT
        if (selected_exact and index != int(correct_index)) or (not selected_exact and index == int(correct_index)):
            provenance = PATCH_PROVENANCE_ALTERED
        for _attempt in range(80):
            crop_box, targets, attempts = _select_crop_box_with_detail(
                source_rgb,
                rng,
                patch_w=patch_w,
                patch_h=patch_h,
                crop_margin_px=int(crop_margin_px),
                edit_objects=edit_objects,
                used_crop_boxes=used_crop_boxes,
                require_editable=provenance == PATCH_PROVENANCE_ALTERED,
                min_crop_detail_score=float(min_crop_detail_score),
                min_edit_objects=int(min_edit_objects),
                crop_padding_px=int(crop_padding_px),
            )
            candidate_crop_count += int(attempts)
            patch = source_rgb.crop(crop_box).convert("RGB")
            alterations: Tuple[PatchAlterationRecord, ...] = tuple()
            if provenance == PATCH_PROVENANCE_ALTERED:
                try:
                    patch, alterations = _alter_patch(
                        patch,
                        crop_box=crop_box,
                        targets=targets,
                        rng=rng,
                        edit_family_count_support=edit_family_count_support,
                        min_edit_objects=int(min_edit_objects),
                        max_edit_objects=int(max_edit_objects),
                        min_changed_fraction=float(min_changed_fraction),
                        max_changed_fraction=float(max_changed_fraction),
                        min_difference_score=float(min_patch_difference_score),
                        draw_added_object=draw_added_object,
                    )
                except ValueError:
                    continue
            used_crop_boxes.append(tuple(int(value) for value in crop_box))
            options.append(patch)
            option_source_crop_boxes[str(label)] = tuple(int(value) for value in crop_box)
            option_provenance[str(label)] = str(provenance)
            option_alterations[str(label)] = alterations
            break
        else:
            raise ValueError("could not build enough exact/altered patch options")

    margin = int(render_margin)
    source_w, source_h = source_rgb.size
    option_rows, row_capacity = option_grid_shape(int(option_count))
    full_w = max(
        source_w + 2 * margin,
        row_capacity * patch_w + (row_capacity - 1) * int(option_gap) + 2 * margin,
    )
    top_y = margin
    options_y = top_y + source_h + int(source_option_gap)
    full_h = options_y + option_rows * (patch_h + int(option_label_height) + 18) + margin
    canvas = Image.new("RGB", (int(full_w), int(full_h)), rgb(style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    source_x = int((full_w - source_w) // 2)
    canvas.paste(source_rgb, (source_x, top_y))
    source_image_bbox = bbox_list((source_x, top_y, source_x + source_w, top_y + source_h))

    option_bboxes: Dict[str, list[float]] = {}
    for index, option in enumerate(options):
        row = index // row_capacity
        col = index % row_capacity
        actual_cols = row_capacity if row < option_rows - 1 else int(option_count) - row * row_capacity
        row_width = actual_cols * patch_w + (actual_cols - 1) * int(option_gap)
        x = int((full_w - row_width) // 2 + col * (patch_w + int(option_gap)))
        y = int(options_y + row * (patch_h + int(option_label_height) + 18))
        patch_x = x
        patch_y = y + int(option_label_height)
        if int(option.width) != patch_w or int(option.height) != patch_h:
            option = ImageOps.fit(option.convert("RGB"), (patch_w, patch_h), method=Image.Resampling.LANCZOS)
        canvas.paste(option.convert("RGB"), (patch_x, patch_y))
        if bool(draw_option_outlines):
            draw.rectangle(
                (patch_x, patch_y, patch_x + patch_w, patch_y + patch_h),
                outline=rgb(style, "panel_outline_rgb"),
                width=2,
            )
        label = str(label_values[index])
        draw_label_badge(
            draw,
            label,
            (x, y, x + 42, y + 24),
            font_family=label_font_family,
            fill=rgb(style, "badge_fill_rgb"),
            outline=rgb(style, "badge_outline_rgb"),
        )
        option_bboxes[label] = bbox_list((patch_x, patch_y, patch_x + patch_w, patch_y + patch_h))

    selected_label = str(label_values[int(correct_index)])
    return PatchMembershipArtifacts(
        image=canvas,
        option_bboxes=option_bboxes,
        selected_option_bbox=list(option_bboxes[selected_label]),
        selected_label=selected_label,
        selected_index=int(correct_index),
        source_image_bbox=source_image_bbox,
        option_source_crop_boxes=dict(option_source_crop_boxes),
        option_provenance=dict(option_provenance),
        option_alterations=dict(option_alterations),
        option_grid_shape=(int(option_rows), int(row_capacity)),
        candidate_crop_count=int(candidate_crop_count),
    )


def downscale_patch_membership_artifacts(
    artifacts: PatchMembershipArtifacts,
    *,
    max_pixels: int,
) -> PatchMembershipArtifacts:
    """Return patch-membership artifacts scaled under a final pixel cap."""

    image, scale_x, scale_y = resize_to_max_pixels(artifacts.image, max_pixels=int(max_pixels))
    if scale_x == 1.0 and scale_y == 1.0:
        return PatchMembershipArtifacts(
            image=artifacts.image,
            option_bboxes=dict(artifacts.option_bboxes),
            selected_option_bbox=list(artifacts.selected_option_bbox),
            selected_label=str(artifacts.selected_label),
            selected_index=int(artifacts.selected_index),
            source_image_bbox=list(artifacts.source_image_bbox),
            option_source_crop_boxes=dict(artifacts.option_source_crop_boxes),
            option_provenance=dict(artifacts.option_provenance),
            option_alterations=dict(artifacts.option_alterations),
            option_grid_shape=tuple(int(value) for value in artifacts.option_grid_shape),
            candidate_crop_count=int(artifacts.candidate_crop_count),
            output_scale_xy=(1.0, 1.0),
            pre_downscale_canvas_size=(int(artifacts.image.width), int(artifacts.image.height)),
        )
    return PatchMembershipArtifacts(
        image=image,
        option_bboxes=scale_bbox_map(artifacts.option_bboxes, scale_x=scale_x, scale_y=scale_y),
        selected_option_bbox=scale_bbox(artifacts.selected_option_bbox, scale_x=scale_x, scale_y=scale_y),
        selected_label=str(artifacts.selected_label),
        selected_index=int(artifacts.selected_index),
        source_image_bbox=scale_bbox(artifacts.source_image_bbox, scale_x=scale_x, scale_y=scale_y),
        option_source_crop_boxes=dict(artifacts.option_source_crop_boxes),
        option_provenance=dict(artifacts.option_provenance),
        option_alterations=dict(artifacts.option_alterations),
        option_grid_shape=tuple(int(value) for value in artifacts.option_grid_shape),
        candidate_crop_count=int(artifacts.candidate_crop_count),
        output_scale_xy=(float(scale_x), float(scale_y)),
        pre_downscale_canvas_size=(int(artifacts.image.width), int(artifacts.image.height)),
    )


def alteration_trace(records: Mapping[str, Sequence[PatchAlterationRecord]]) -> Dict[str, list[Dict[str, Any]]]:
    """Serialize option-keyed alteration records for trace payloads."""

    return {
        str(label): [record.trace() for record in option_records]
        for label, option_records in records.items()
    }


__all__ = [
    "ALTERED_PATCH_QUERY_ID",
    "EXACT_SOURCE_PATCH_QUERY_ID",
    "PATCH_MEMBERSHIP_QUERY_IDS",
    "PATCH_PROVENANCE_ALTERED",
    "PATCH_PROVENANCE_EXACT",
    "EditablePatchObject",
    "PatchAlterationRecord",
    "PatchMembershipArtifacts",
    "alteration_trace",
    "compose_source_patch_membership_options",
    "downscale_patch_membership_artifacts",
]
