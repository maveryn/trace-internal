"""Pedigree-chart sampling and rendering for graph-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.bbox_projection import round_bbox
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from .graph_scene import GraphRenderParams


Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]

SUPPORTED_PEDIGREE_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic_pedigree",
    "row_guided_pedigree",
    "paper_pedigree",
)
SUPPORTED_PEDIGREE_RELATIONSHIP_QUERY_IDS: Tuple[str, ...] = (
    "relationship_label_between_two_people",
)
SUPPORTED_PEDIGREE_RELATEDNESS_QUERY_IDS: Tuple[str, ...] = (
    "relatedness_coefficient_between_two_people",
)
PEDIGREE_RELATIONSHIP_LABELS: Tuple[str, ...] = (
    "parent",
    "child",
    "sibling",
    "partner",
    "grandparent",
    "grandchild",
)
PEDIGREE_RELATEDNESS_LABELS: Tuple[str, ...] = ("0", "1/8", "1/4", "3/8", "1/2")
PEDIGREE_RELATEDNESS_OPTION_LABELS: Tuple[str, ...] = (
    "0",
    "1/16",
    "1/8",
    "1/4",
    "3/8",
    "1/2",
    "5/8",
    "3/4",
    "1",
)
PEDIGREE_SEX_LABELS: Mapping[str, str] = {
    "male": "male",
    "female": "female",
}
GENERATION_LABELS: Tuple[str, ...] = ("I", "II", "III", "IV")


@dataclass(frozen=True)
class PedigreePerson:
    """One person in a pedigree chart."""

    person_id: str
    generation_index: int
    sex: str
    affected: bool
    label: str

    @property
    def generation_label(self) -> str:
        return GENERATION_LABELS[int(self.generation_index)]


@dataclass(frozen=True)
class PedigreeFamily:
    """One couple and its children in a pedigree chart."""

    family_id: str
    parent_ids: Tuple[str, str]
    child_ids: Tuple[str, ...]


@dataclass(frozen=True)
class PedigreeSample:
    """Trace-ready pedigree sample."""

    people: Tuple[PedigreePerson, ...]
    families: Tuple[PedigreeFamily, ...]
    query_id: str
    target_count: int
    target_generation_index: int | None
    target_sex: str | None
    counted_person_ids: Tuple[str, ...]
    template_name: str


@dataclass(frozen=True)
class RenderedPedigreePerson:
    """Rendered projection for one pedigree person."""

    person_id: str
    label: str
    generation_index: int
    generation_label: str
    sex: str
    affected: bool
    center_xy: Point
    symbol_bbox_xyxy: BBox
    label_bbox_xyxy: BBox


@dataclass(frozen=True)
class RenderedPedigreeFamily:
    """Rendered connector projection for one pedigree family."""

    family_id: str
    parent_ids: Tuple[str, str]
    child_ids: Tuple[str, ...]
    spouse_segment_px: Tuple[Point, Point]
    descent_segments_px: Tuple[Tuple[Point, Point], ...]


@dataclass(frozen=True)
class RenderedPedigreeScene:
    """Full render output for one pedigree scene."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    people: Tuple[RenderedPedigreePerson, ...]
    families: Tuple[RenderedPedigreeFamily, ...]
    scene_variant: str
    resolved_label_font_size_px: int
    resolved_label_stroke_width_px: int
    generation_label_bboxes: Dict[str, BBox]


@dataclass(frozen=True)
class PedigreeRelationshipQuerySample:
    """One relationship-label query over a pedigree."""

    sample: PedigreeSample
    query_id: str
    answer: str
    person_a_id: str
    person_b_id: str
    annotation_roles: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class PedigreeRelatednessQuerySample:
    """One coefficient-of-relatedness query over a pedigree."""

    sample: PedigreeSample
    query_id: str
    answer: str
    person_a_id: str
    person_b_id: str
    annotation_roles: Tuple[Tuple[str, str], ...]
    contributing_paths: Tuple[Dict[str, Any], ...]


@dataclass(frozen=True)
class _TemplatePerson:
    """Template person before labels and affected-state assignment."""

    person_id: str
    generation_index: int
    sex: str


@dataclass(frozen=True)
class _Template:
    """Static pedigree topology template."""

    name: str
    people: Tuple[_TemplatePerson, ...]
    families: Tuple[PedigreeFamily, ...]


def _template_compact_three() -> _Template:
    people = (
        _TemplatePerson("p0", 0, "male"),
        _TemplatePerson("p1", 0, "female"),
        _TemplatePerson("p2", 1, "male"),
        _TemplatePerson("p3", 1, "female"),
        _TemplatePerson("p4", 1, "male"),
        _TemplatePerson("p5", 1, "male"),
        _TemplatePerson("p6", 1, "female"),
        _TemplatePerson("p7", 2, "female"),
        _TemplatePerson("p8", 2, "male"),
        _TemplatePerson("p9", 2, "male"),
        _TemplatePerson("p10", 2, "female"),
    )
    families = (
        PedigreeFamily("f0", ("p0", "p1"), ("p2", "p3", "p5")),
        PedigreeFamily("f1", ("p3", "p4"), ("p7", "p8")),
        PedigreeFamily("f2", ("p5", "p6"), ("p9", "p10")),
    )
    return _Template("compact_three_generation", people, families)


def _template_wide_three() -> _Template:
    people = (
        _TemplatePerson("p0", 0, "male"),
        _TemplatePerson("p1", 0, "female"),
        _TemplatePerson("p2", 1, "male"),
        _TemplatePerson("p3", 1, "female"),
        _TemplatePerson("p4", 1, "female"),
        _TemplatePerson("p5", 1, "male"),
        _TemplatePerson("p6", 1, "male"),
        _TemplatePerson("p7", 1, "female"),
        _TemplatePerson("p8", 1, "female"),
        _TemplatePerson("p9", 1, "male"),
        _TemplatePerson("p10", 2, "male"),
        _TemplatePerson("p11", 2, "female"),
        _TemplatePerson("p12", 2, "female"),
        _TemplatePerson("p13", 2, "male"),
        _TemplatePerson("p14", 2, "male"),
        _TemplatePerson("p15", 2, "female"),
    )
    families = (
        PedigreeFamily("f0", ("p0", "p1"), ("p2", "p4", "p6", "p8")),
        PedigreeFamily("f1", ("p2", "p3"), ("p10", "p11")),
        PedigreeFamily("f2", ("p4", "p5"), ("p12", "p13")),
        PedigreeFamily("f3", ("p6", "p7"), ("p14", "p15")),
        PedigreeFamily("f4", ("p8", "p9"), ()),
    )
    return _Template("wide_three_generation", people, families)


def _template_four_generation() -> _Template:
    people = (
        _TemplatePerson("p0", 0, "male"),
        _TemplatePerson("p1", 0, "female"),
        _TemplatePerson("p2", 1, "female"),
        _TemplatePerson("p3", 1, "male"),
        _TemplatePerson("p4", 1, "male"),
        _TemplatePerson("p5", 1, "female"),
        _TemplatePerson("p6", 2, "male"),
        _TemplatePerson("p7", 2, "female"),
        _TemplatePerson("p8", 2, "female"),
        _TemplatePerson("p9", 2, "male"),
        _TemplatePerson("p10", 3, "male"),
        _TemplatePerson("p11", 3, "female"),
        _TemplatePerson("p12", 3, "male"),
    )
    families = (
        PedigreeFamily("f0", ("p0", "p1"), ("p2", "p4", "p5")),
        PedigreeFamily("f1", ("p2", "p3"), ("p6", "p8", "p9")),
        PedigreeFamily("f2", ("p6", "p7"), ("p10", "p11", "p12")),
    )
    return _Template("four_generation", people, families)


def _template_compound_relatedness() -> _Template:
    people = (
        _TemplatePerson("p0", 0, "male"),
        _TemplatePerson("p1", 0, "female"),
        _TemplatePerson("p2", 1, "female"),
        _TemplatePerson("p3", 1, "female"),
        _TemplatePerson("p4", 1, "male"),
        _TemplatePerson("p5", 2, "female"),
        _TemplatePerson("p6", 2, "male"),
        _TemplatePerson("p7", 2, "female"),
        _TemplatePerson("p8", 2, "male"),
    )
    families = (
        PedigreeFamily("f0", ("p0", "p1"), ("p2", "p3")),
        PedigreeFamily("f1", ("p4", "p2"), ("p5", "p7")),
        PedigreeFamily("f2", ("p4", "p3"), ("p6", "p8")),
    )
    return _Template("compound_relatedness", people, families)


def _templates() -> Tuple[_Template, ...]:
    return (
        _template_compact_three(),
        _template_wide_three(),
        _template_four_generation(),
        _template_compound_relatedness(),
    )


def _generation_persons(template: _Template, generation_index: int) -> Tuple[_TemplatePerson, ...]:
    return tuple(person for person in template.people if int(person.generation_index) == int(generation_index))


def _assign_labels(template: _Template, affected_ids: Iterable[str]) -> Tuple[PedigreePerson, ...]:
    affected_set = {str(person_id) for person_id in affected_ids}
    counts_by_generation: Dict[int, int] = {}
    result: List[PedigreePerson] = []
    for person in template.people:
        generation_index = int(person.generation_index)
        counts_by_generation[generation_index] = int(counts_by_generation.get(generation_index, 0)) + 1
        label = f"{GENERATION_LABELS[generation_index]}-{counts_by_generation[generation_index]}"
        result.append(
            PedigreePerson(
                person_id=str(person.person_id),
                generation_index=int(generation_index),
                sex=str(person.sex),
                affected=str(person.person_id) in affected_set,
                label=str(label),
            )
        )
    return tuple(result)


def _person_map(sample: PedigreeSample) -> Dict[str, PedigreePerson]:
    return {str(person.person_id): person for person in sample.people}


def _template_by_name(name: str) -> _Template:
    for template in _templates():
        if str(template.name) == str(name):
            return template
    raise ValueError(f"unknown pedigree template: {name}")


def _label_for_id(sample: PedigreeSample, person_id: str) -> str:
    return _person_map(sample)[str(person_id)].label


def _parents_by_child(sample: PedigreeSample) -> Dict[str, Tuple[str, str]]:
    result: Dict[str, Tuple[str, str]] = {}
    for family in sample.families:
        for child_id in family.child_ids:
            result[str(child_id)] = tuple(str(parent_id) for parent_id in family.parent_ids)  # type: ignore[assignment]
    return result


def _children_by_parent(sample: PedigreeSample) -> Dict[str, Tuple[str, ...]]:
    result: Dict[str, List[str]] = {str(person.person_id): [] for person in sample.people}
    for family in sample.families:
        for parent_id in family.parent_ids:
            result.setdefault(str(parent_id), []).extend(str(child_id) for child_id in family.child_ids)
    return {str(parent_id): tuple(child_ids) for parent_id, child_ids in result.items()}


def _families_by_partner_pair(sample: PedigreeSample) -> Dict[Tuple[str, str], PedigreeFamily]:
    result: Dict[Tuple[str, str], PedigreeFamily] = {}
    for family in sample.families:
        key = tuple(sorted(str(parent_id) for parent_id in family.parent_ids))
        result[key] = family
    return result


def _relationship_candidates(sample: PedigreeSample, relation: str) -> Tuple[Tuple[str, str, Tuple[Tuple[str, str], ...]], ...]:
    """Return `(person_a, person_b, extra_roles)` candidates for one relation."""

    parents_by_child = _parents_by_child(sample)
    children_by_parent = _children_by_parent(sample)
    candidates: List[Tuple[str, str, Tuple[Tuple[str, str], ...]]] = []
    if str(relation) == "partner":
        for family in sample.families:
            left, right = tuple(str(parent_id) for parent_id in family.parent_ids)
            candidates.append((left, right, ()))
            candidates.append((right, left, ()))
    elif str(relation) == "parent":
        for child_id, parent_ids in parents_by_child.items():
            for parent_id in parent_ids:
                candidates.append((str(parent_id), str(child_id), ()))
    elif str(relation) == "child":
        for child_id, parent_ids in parents_by_child.items():
            for parent_id in parent_ids:
                candidates.append((str(child_id), str(parent_id), ()))
    elif str(relation) == "sibling":
        for family in sample.families:
            children = tuple(str(child_id) for child_id in family.child_ids)
            for index, child_a in enumerate(children):
                for child_b in children[index + 1 :]:
                    bridge = (("shared_parent_1", str(family.parent_ids[0])), ("shared_parent_2", str(family.parent_ids[1])))
                    candidates.append((str(child_a), str(child_b), bridge))
                    candidates.append((str(child_b), str(child_a), bridge))
    elif str(relation) in {"grandparent", "grandchild"}:
        for middle_id, grandparent_ids in parents_by_child.items():
            for grandchild_id in children_by_parent.get(str(middle_id), ()):
                for grandparent_id in grandparent_ids:
                    bridge = (("middle_parent", str(middle_id)),)
                    if str(relation) == "grandparent":
                        candidates.append((str(grandparent_id), str(grandchild_id), bridge))
                    else:
                        candidates.append((str(grandchild_id), str(grandparent_id), bridge))
    else:
        raise ValueError(f"unsupported pedigree relationship: {relation}")
    return tuple(candidates)


def sample_pedigree_relationship(
    instance_seed: int,
    *,
    target_relationship: str,
    max_attempts: int = 80,
) -> PedigreeRelationshipQuerySample:
    """Sample one relationship query with a unique relationship answer."""

    if str(target_relationship) not in set(PEDIGREE_RELATIONSHIP_LABELS):
        raise ValueError(f"unsupported relationship label: {target_relationship}")
    templates = _templates()
    for attempt in range(max(1, int(max_attempts))):
        rng = spawn_rng(int(instance_seed), "pedigree_chart.relationship", int(attempt))
        template = templates[int(rng.randrange(len(templates)))]
        sample = PedigreeSample(
            people=_assign_labels(template, ()),
            families=tuple(template.families),
            query_id="relationship_label_between_two_people",
            target_count=0,
            target_generation_index=None,
            target_sex=None,
            counted_person_ids=(),
            template_name=str(template.name),
        )
        candidates = _relationship_candidates(sample, str(target_relationship))
        if not candidates:
            continue
        person_a_id, person_b_id, extra_roles = rng.choice(list(candidates))
        roles = (("person_a", str(person_a_id)), ("person_b", str(person_b_id)), *tuple(extra_roles))
        return PedigreeRelationshipQuerySample(
            sample=sample,
            query_id="relationship_label_between_two_people",
            answer=str(target_relationship),
            person_a_id=str(person_a_id),
            person_b_id=str(person_b_id),
            annotation_roles=tuple(roles),
        )
    raise ValueError("unable to sample pedigree relationship query")


def _ancestor_paths_by_person(sample: PedigreeSample, person_id: str) -> Dict[str, Tuple[Tuple[str, ...], ...]]:
    """Return all upward paths from one person to each ancestor, including self."""

    parents_by_child = _parents_by_child(sample)
    paths: Dict[str, List[Tuple[str, ...]]] = {}

    def visit(current_id: str, path: Tuple[str, ...]) -> None:
        paths.setdefault(str(current_id), []).append(tuple(path))
        for parent_id in parents_by_child.get(str(current_id), ()):
            if str(parent_id) in set(path):
                continue
            visit(str(parent_id), (*tuple(path), str(parent_id)))

    visit(str(person_id), (str(person_id),))
    return {str(key): tuple(value) for key, value in paths.items()}


def _format_relatedness_fraction(value: Fraction) -> str:
    normalized = Fraction(value)
    if int(normalized.denominator) == 1:
        return str(int(normalized.numerator))
    return f"{int(normalized.numerator)}/{int(normalized.denominator)}"


def _relatedness_fraction_and_paths(
    sample: PedigreeSample,
    person_a_id: str,
    person_b_id: str,
) -> Tuple[Fraction, Tuple[Dict[str, Any], ...]]:
    paths_a = _ancestor_paths_by_person(sample, str(person_a_id))
    paths_b = _ancestor_paths_by_person(sample, str(person_b_id))
    total = Fraction(0, 1)
    contributing: List[Dict[str, Any]] = []
    for ancestor_id in sorted(set(paths_a).intersection(paths_b)):
        for path_a in paths_a[str(ancestor_id)]:
            for path_b in paths_b[str(ancestor_id)]:
                if not set(path_a[:-1]).isdisjoint(set(path_b[:-1])):
                    continue
                edges = int(len(path_a) + len(path_b) - 2)
                contribution = Fraction(1, int(2**edges))
                total += contribution
                contributing.append(
                    {
                        "ancestor_id": str(ancestor_id),
                        "path_a": list(path_a),
                        "path_b": list(path_b),
                        "edge_count": int(edges),
                        "contribution": _format_relatedness_fraction(contribution),
                    }
                )
    return Fraction(total), tuple(contributing)


def _relatedness_annotation_roles(
    *,
    person_a_id: str,
    person_b_id: str,
    contributing_paths: Sequence[Mapping[str, Any]],
) -> Tuple[Tuple[str, str], ...]:
    roles: List[Tuple[str, str]] = [("person_a", str(person_a_id)), ("person_b", str(person_b_id))]
    seen_roles = {"person_a", "person_b"}
    for path_index, path_info in enumerate(contributing_paths, start=1):
        ancestor_id = str(path_info["ancestor_id"])
        role = f"shared_ancestor_{path_index}"
        if role not in seen_roles:
            roles.append((role, ancestor_id))
            seen_roles.add(role)
        for side_key, role_side in (("path_a", "a"), ("path_b", "b")):
            path = [str(item) for item in path_info.get(side_key, [])]
            middle_ids = tuple(person_id for person_id in path[1:-1] if person_id not in {str(person_a_id), str(person_b_id)})
            for middle_index, middle_id in enumerate(middle_ids, start=1):
                middle_role = f"path_{path_index}_{role_side}_{middle_index}"
                if middle_role in seen_roles:
                    continue
                roles.append((middle_role, str(middle_id)))
                seen_roles.add(middle_role)
    return tuple(roles)


def _relatedness_candidates(
    sample: PedigreeSample,
    target_relatedness: str,
) -> Tuple[PedigreeRelatednessQuerySample, ...]:
    candidates: List[PedigreeRelatednessQuerySample] = []
    people = tuple(sample.people)
    for index_a, person_a in enumerate(people):
        for person_b in people[index_a + 1 :]:
            fraction, contributing_paths = _relatedness_fraction_and_paths(
                sample,
                str(person_a.person_id),
                str(person_b.person_id),
            )
            answer = _format_relatedness_fraction(fraction)
            if str(answer) != str(target_relatedness):
                continue
            roles = _relatedness_annotation_roles(
                person_a_id=str(person_a.person_id),
                person_b_id=str(person_b.person_id),
                contributing_paths=contributing_paths,
            )
            candidates.append(
                PedigreeRelatednessQuerySample(
                    sample=sample,
                    query_id="relatedness_coefficient_between_two_people",
                    answer=str(answer),
                    person_a_id=str(person_a.person_id),
                    person_b_id=str(person_b.person_id),
                    annotation_roles=tuple(roles),
                    contributing_paths=tuple(contributing_paths),
                )
            )
    return tuple(candidates)


def sample_pedigree_relatedness(
    instance_seed: int,
    *,
    target_relatedness: str,
    max_attempts: int = 100,
) -> PedigreeRelatednessQuerySample:
    """Sample one pedigree relatedness-coefficient query."""

    if str(target_relatedness) not in set(PEDIGREE_RELATEDNESS_LABELS):
        raise ValueError(f"unsupported relatedness label: {target_relatedness}")
    templates = _templates()
    for attempt in range(max(1, int(max_attempts))):
        rng = spawn_rng(int(instance_seed), "pedigree_chart.relatedness", int(attempt))
        template = templates[int(rng.randrange(len(templates)))]
        sample = PedigreeSample(
            people=_assign_labels(template, ()),
            families=tuple(template.families),
            query_id="relatedness_coefficient_between_two_people",
            target_count=0,
            target_generation_index=None,
            target_sex=None,
            counted_person_ids=(),
            template_name=str(template.name),
        )
        candidates = _relatedness_candidates(sample, str(target_relatedness))
        if not candidates:
            continue
        return rng.choice(list(candidates))
    raise ValueError("unable to sample pedigree relatedness query")


def _text_bbox(draw: ImageDraw.ImageDraw, xy: Point, text: str, font) -> BBox:
    bbox = draw.textbbox((int(xy[0]), int(xy[1])), str(text), font=font)
    return tuple(int(value) for value in bbox)  # type: ignore[return-value]


def _center_text(draw: ImageDraw.ImageDraw, center_xy: Point, text: str, font, fill: Tuple[int, int, int]) -> BBox:
    text_bbox = draw.textbbox((0, 0), str(text), font=font)
    width = int(text_bbox[2] - text_bbox[0])
    height = int(text_bbox[3] - text_bbox[1])
    xy = (int(center_xy[0] - (width / 2)), int(center_xy[1] - (height / 2)))
    draw_text_traced(
        draw,
        xy,
        str(text),
        fill=tuple(int(value) for value in fill),
        font=font,
        role="graph_pedigree_label_text",
        required=False,
    )
    return _text_bbox(draw, xy, str(text), font)


def _resolve_centers(
    sample: PedigreeSample,
    *,
    render_params: GraphRenderParams,
    bottom_reserved_px: int = 0,
) -> Tuple[Dict[str, Point], Dict[int, int], Dict[int, Tuple[int, int]]]:
    generations = sorted({int(person.generation_index) for person in sample.people})
    panel_left = int(render_params.outer_margin_px)
    panel_top = int(render_params.outer_margin_px)
    panel_right = int(render_params.canvas_width - render_params.outer_margin_px)
    panel_bottom = int(render_params.canvas_height - render_params.outer_margin_px)
    content_left = int(panel_left + render_params.panel_padding_px + 76)
    content_right = int(panel_right - render_params.panel_padding_px - 22)
    content_top = int(panel_top + render_params.panel_padding_px + 78)
    content_bottom = int(panel_bottom - render_params.panel_padding_px - 42 - max(0, int(bottom_reserved_px)))
    row_count = max(1, len(generations))
    if row_count == 1:
        row_y = {generations[0]: int((content_top + content_bottom) / 2)}
    else:
        row_y = {
            int(generation): int(round(content_top + ((content_bottom - content_top) * index / (row_count - 1))))
            for index, generation in enumerate(generations)
        }
    centers: Dict[str, Point] = {}
    row_extents: Dict[int, Tuple[int, int]] = {}
    for generation in generations:
        people = [person for person in sample.people if int(person.generation_index) == int(generation)]
        count = len(people)
        if count == 1:
            xs = [int((content_left + content_right) / 2)]
        else:
            available_width = int(content_right - content_left)
            spacing = min(112.0, float(available_width) / float(max(1, count - 1)))
            row_width = spacing * float(count - 1)
            start_x = (float(content_left + content_right) / 2.0) - (row_width / 2.0)
            xs = [int(round(start_x + (spacing * index))) for index in range(count)]
        for person, x in zip(people, xs):
            centers[str(person.person_id)] = (int(x), int(row_y[int(generation)]))
        row_extents[int(generation)] = (int(content_left), int(content_right))
    return centers, row_y, row_extents


def _draw_person_symbol(
    draw: ImageDraw.ImageDraw,
    *,
    center_xy: Point,
    sex: str,
    affected: bool,
    render_params: GraphRenderParams,
) -> BBox:
    radius = int(render_params.node_radius_px)
    x, y = int(center_xy[0]), int(center_xy[1])
    bbox = (int(x - radius), int(y - radius), int(x + radius), int(y + radius))
    fill_rgb = tuple(int(value) for value in (render_params.node_fill_rgb if bool(affected) else render_params.panel_fill_rgb))
    outline_rgb = tuple(int(value) for value in render_params.node_border_rgb)
    if str(sex) == "female":
        draw.ellipse(
            bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=int(render_params.node_border_width_px),
        )
    else:
        draw.rectangle(
            bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=int(render_params.node_border_width_px),
        )
    return tuple(int(value) for value in bbox)  # type: ignore[return-value]


def render_pedigree_chart_scene(
    *,
    sample: PedigreeSample,
    render_params: GraphRenderParams,
    scene_variant: str,
    scene_title: str,
    base_image: Image.Image,
    highlighted_person_ids: Sequence[str] = (),
    bottom_reserved_px: int = 0,
) -> RenderedPedigreeScene:
    """Render one pedigree chart and trace all symbol projections."""

    variant = str(scene_variant)
    if variant not in set(SUPPORTED_PEDIGREE_SCENE_VARIANTS):
        variant = "classic_pedigree"
    image = base_image
    draw = ImageDraw.Draw(image)
    panel_left = int(render_params.outer_margin_px)
    panel_top = int(render_params.outer_margin_px)
    panel_right = int(render_params.canvas_width - render_params.outer_margin_px)
    panel_bottom = int(render_params.canvas_height - render_params.outer_margin_px)
    panel_bbox = (panel_left, panel_top, panel_right, panel_bottom)
    draw.rounded_rectangle(
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(int(value) for value in render_params.panel_fill_rgb),
        outline=tuple(int(value) for value in render_params.panel_border_rgb),
        width=2,
    )

    title_font = load_font(
        int(render_params.panel_title_font_size_px),
        bold=True,
        font_family=str(render_params.font_family),
    )
    label_font = load_font(
        int(render_params.label_font_size_px),
        bold=True,
        font_family=str(render_params.font_family),
    )
    small_font = load_font(
        max(12, int(round(render_params.label_font_size_px * 0.78))),
        bold=True,
        font_family=str(render_params.font_family),
    )
    draw_text_traced(
        draw,
        (int(panel_left + render_params.panel_padding_px), int(panel_top + render_params.panel_padding_px)),
        str(scene_title),
        fill=tuple(int(value) for value in render_params.title_color_rgb),
        font=title_font,
        role="graph_pedigree_title_text",
        required=False,
    )
    subtitle = "Squares are male; circles are female"
    draw_text_traced(
        draw,
        (
            int(panel_left + render_params.panel_padding_px),
            int(panel_top + render_params.panel_padding_px + render_params.panel_title_font_size_px + 8),
        ),
        subtitle,
        fill=tuple(int(value) for value in render_params.edge_color_rgb),
        font=small_font,
        role="graph_pedigree_context_text",
        required=False,
    )

    centers, row_y, row_extents = _resolve_centers(
        sample,
        render_params=render_params,
        bottom_reserved_px=int(bottom_reserved_px),
    )
    if variant == "row_guided_pedigree":
        for generation, y in sorted(row_y.items()):
            left, right = row_extents[int(generation)]
            band_height = int(max(42, render_params.node_radius_px * 2 + 22))
            draw.rounded_rectangle(
                (int(left - 46), int(y - band_height / 2), int(right + 8), int(y + band_height / 2)),
                radius=12,
                fill=tuple(max(0, min(255, int(value))) for value in (246, 248, 252)),
                outline=None,
            )
    elif variant == "paper_pedigree":
        for generation, y in sorted(row_y.items()):
            left, right = row_extents[int(generation)]
            draw.line(
                (int(left - 44), int(y), int(right + 8), int(y)),
                fill=tuple(int(value) for value in render_params.panel_border_rgb),
                width=1,
            )

    people_by_id = _person_map(sample)
    connector_color = tuple(int(value) for value in render_params.edge_color_rgb)
    connector_width = max(2, int(render_params.edge_width_px))
    rendered_families: List[RenderedPedigreeFamily] = []
    for family in sample.families:
        parent_a, parent_b = str(family.parent_ids[0]), str(family.parent_ids[1])
        if parent_a not in centers or parent_b not in centers:
            continue
        pa = centers[parent_a]
        pb = centers[parent_b]
        radius = int(render_params.node_radius_px)
        spouse_start = (int(pa[0] + radius), int(pa[1]))
        spouse_end = (int(pb[0] - radius), int(pb[1]))
        if pa[0] > pb[0]:
            spouse_start = (int(pa[0] - radius), int(pa[1]))
            spouse_end = (int(pb[0] + radius), int(pb[1]))
        draw.line((spouse_start[0], spouse_start[1], spouse_end[0], spouse_end[1]), fill=connector_color, width=connector_width)
        descent_segments: List[Tuple[Point, Point]] = []
        child_centers = [centers[str(child_id)] for child_id in family.child_ids if str(child_id) in centers]
        if child_centers:
            parent_mid = (int(round((pa[0] + pb[0]) / 2)), int(pa[1]))
            child_y = int(child_centers[0][1])
            mid_y = int(round((parent_mid[1] + child_y) / 2))
            vertical_parent = ((int(parent_mid[0]), int(parent_mid[1])), (int(parent_mid[0]), int(mid_y)))
            draw.line((vertical_parent[0][0], vertical_parent[0][1], vertical_parent[1][0], vertical_parent[1][1]), fill=connector_color, width=connector_width)
            descent_segments.append(vertical_parent)
            child_xs = [int(point[0]) for point in child_centers]
            left_x = int(min(child_xs))
            right_x = int(max(child_xs))
            if left_x != right_x:
                sibship = ((left_x, mid_y), (right_x, mid_y))
                draw.line((left_x, mid_y, right_x, mid_y), fill=connector_color, width=connector_width)
                descent_segments.append(sibship)
            for child_center in child_centers:
                child_segment = ((int(child_center[0]), int(mid_y)), (int(child_center[0]), int(child_center[1] - radius)))
                draw.line(
                    (child_segment[0][0], child_segment[0][1], child_segment[1][0], child_segment[1][1]),
                    fill=connector_color,
                    width=connector_width,
                )
                descent_segments.append(child_segment)
        rendered_families.append(
            RenderedPedigreeFamily(
                family_id=str(family.family_id),
                parent_ids=tuple(str(parent_id) for parent_id in family.parent_ids),
                child_ids=tuple(str(child_id) for child_id in family.child_ids),
                spouse_segment_px=(spouse_start, spouse_end),
                descent_segments_px=tuple(descent_segments),
            )
        )

    generation_label_bboxes: Dict[str, BBox] = {}
    for generation, y in sorted(row_y.items()):
        generation_label = str(GENERATION_LABELS[int(generation)])
        generation_label_bboxes[generation_label] = _center_text(
            draw,
            (int(panel_left + render_params.panel_padding_px + 30), int(y)),
            generation_label,
            small_font,
            tuple(int(value) for value in render_params.title_color_rgb),
        )

    rendered_people: List[RenderedPedigreePerson] = []
    highlighted_set = {str(person_id) for person_id in highlighted_person_ids}
    for person in sample.people:
        center = centers[str(person.person_id)]
        symbol_bbox = _draw_person_symbol(
            draw,
            center_xy=center,
            sex=str(person.sex),
            affected=bool(person.affected),
            render_params=render_params,
        )
        label_y = int(center[1] + render_params.node_radius_px + 13)
        label_bbox = _center_text(
            draw,
            (int(center[0]), int(label_y)),
            str(person.label),
            label_font,
            tuple(int(value) for value in render_params.title_color_rgb),
        )
        rendered_people.append(
            RenderedPedigreePerson(
                person_id=str(person.person_id),
                label=str(person.label),
                generation_index=int(person.generation_index),
                generation_label=str(person.generation_label),
                sex=str(person.sex),
                affected=bool(person.affected),
                center_xy=(int(center[0]), int(center[1])),
                symbol_bbox_xyxy=tuple(int(value) for value in symbol_bbox),
                label_bbox_xyxy=tuple(int(value) for value in label_bbox),
            )
        )

    if highlighted_set:
        highlight_rgb = (211, 118, 36)
        for rendered_person in rendered_people:
            if str(rendered_person.person_id) not in highlighted_set:
                continue
            x0, y0, x1, y1 = rendered_person.symbol_bbox_xyxy
            pad = max(5, int(round(render_params.node_radius_px * 0.28)))
            highlight_bbox = (int(x0 - pad), int(y0 - pad), int(x1 + pad), int(y1 + pad))
            if str(rendered_person.sex) == "female":
                draw.ellipse(highlight_bbox, outline=highlight_rgb, width=3)
            else:
                draw.rounded_rectangle(highlight_bbox, radius=6, outline=highlight_rgb, width=3)

    panel_geometry = {
        "canvas_size": [int(render_params.canvas_width), int(render_params.canvas_height)],
        "panel_bbox_xyxy": [int(value) for value in panel_bbox],
        "generation_row_y": {str(GENERATION_LABELS[int(key)]): int(value) for key, value in sorted(row_y.items())},
        "highlighted_person_ids": sorted(highlighted_set),
        "bottom_reserved_px": int(max(0, int(bottom_reserved_px))),
    }
    return RenderedPedigreeScene(
        image=image,
        panel_geometry=dict(panel_geometry),
        people=tuple(rendered_people),
        families=tuple(rendered_families),
        scene_variant=str(variant),
        resolved_label_font_size_px=int(render_params.label_font_size_px),
        resolved_label_stroke_width_px=0,
        generation_label_bboxes={
            str(key): tuple(int(value) for value in bbox)
            for key, bbox in generation_label_bboxes.items()
        },
    )


def pedigree_scene_entities(sample: PedigreeSample, rendered_scene: RenderedPedigreeScene) -> Tuple[Dict[str, Any], ...]:
    """Return trace entity records for rendered pedigree people."""

    rendered_by_id = {str(person.person_id): person for person in rendered_scene.people}
    entities: List[Dict[str, Any]] = []
    for person in sample.people:
        rendered = rendered_by_id[str(person.person_id)]
        entities.append(
            {
                "entity_id": str(person.person_id),
                "entity_kind": "pedigree_person",
                "label": str(person.label),
                "generation_index": int(person.generation_index),
                "generation_label": str(person.generation_label),
                "sex": str(person.sex),
                "affected": bool(person.affected),
                "is_counted": str(person.person_id) in set(sample.counted_person_ids),
                "center_xy": [int(rendered.center_xy[0]), int(rendered.center_xy[1])],
                "symbol_bbox_xyxy": [int(value) for value in rendered.symbol_bbox_xyxy],
                "label_bbox_xyxy": [int(value) for value in rendered.label_bbox_xyxy],
            }
        )
    return tuple(entities)


def pedigree_family_relations(sample: PedigreeSample, rendered_scene: RenderedPedigreeScene) -> Tuple[Dict[str, Any], ...]:
    """Return trace relation records for pedigree family connectors."""

    rendered_by_id = {str(family.family_id): family for family in rendered_scene.families}
    relations: List[Dict[str, Any]] = []
    for family in sample.families:
        rendered = rendered_by_id.get(str(family.family_id))
        relations.append(
            {
                "family_id": str(family.family_id),
                "parent_ids": list(family.parent_ids),
                "child_ids": list(family.child_ids),
                "spouse_segment_px": [list(point) for point in rendered.spouse_segment_px] if rendered is not None else [],
                "descent_segments_px": [
                    [list(point) for point in segment]
                    for segment in (rendered.descent_segments_px if rendered is not None else ())
                ],
            }
        )
    return tuple(relations)


def projected_pedigree_person_point_annotation(
    rendered_scene: RenderedPedigreeScene,
    person_ids: Sequence[str],
) -> Dict[str, Any]:
    """Project selected person ids to point-set annotation."""

    rendered_by_id = {str(person.person_id): person for person in rendered_scene.people}
    points: List[List[int]] = []
    bbox_map: Dict[str, List[int]] = {}
    for person_id in [str(item) for item in person_ids]:
        person = rendered_by_id[str(person_id)]
        point = [int(person.center_xy[0]), int(person.center_xy[1])]
        points.append(point)
        bbox_map[str(person_id)] = [int(value) for value in round_bbox(person.symbol_bbox_xyxy)]
    return {
        "point_set": [list(point) for point in points],
        "pixel_point_set": [list(point) for point in points],
        "person_symbol_bbox_map": dict(bbox_map),
    }


def projected_keyed_pedigree_person_annotation(
    rendered_scene: RenderedPedigreeScene,
    role_person_ids: Sequence[Tuple[str, str]],
) -> Dict[str, Any]:
    """Project role-bound person ids to keyed bbox annotation."""

    rendered_by_id = {str(person.person_id): person for person in rendered_scene.people}
    keyed_bbox_map: Dict[str, List[int]] = {}
    keyed_point_map: Dict[str, List[int]] = {}
    role_person_map: Dict[str, str] = {}
    for role, person_id in role_person_ids:
        rendered = rendered_by_id[str(person_id)]
        role_key = str(role)
        keyed_bbox_map[role_key] = [int(value) for value in round_bbox(rendered.symbol_bbox_xyxy)]
        keyed_point_map[role_key] = [int(rendered.center_xy[0]), int(rendered.center_xy[1])]
        role_person_map[role_key] = str(person_id)
    return {
        "keyed_bbox_map": dict(keyed_bbox_map),
        "pixel_keyed_bbox_map": dict(keyed_bbox_map),
        "keyed_point_map": dict(keyed_point_map),
        "pixel_keyed_point_map": dict(keyed_point_map),
        "role_person_id_map": dict(role_person_map),
    }


def projected_pedigree_generation_annotation(
    rendered_scene: RenderedPedigreeScene,
    *,
    generation_label: str,
    person_ids: Sequence[str],
) -> Dict[str, Any]:
    """Project an answer generation row and its affected witnesses to bbox annotation."""

    rendered_by_id = {str(person.person_id): person for person in rendered_scene.people}
    bbox_set: List[List[int]] = []
    label_bbox = rendered_scene.generation_label_bboxes.get(str(generation_label))
    generation_label_bbox = [int(value) for value in round_bbox(label_bbox)] if label_bbox is not None else []
    if generation_label_bbox:
        bbox_set.append(list(generation_label_bbox))
    person_symbol_bbox_map: Dict[str, List[int]] = {}
    for person_id in [str(item) for item in person_ids]:
        rendered = rendered_by_id[str(person_id)]
        bbox = [int(value) for value in round_bbox(rendered.symbol_bbox_xyxy)]
        bbox_set.append(list(bbox))
        person_symbol_bbox_map[str(person_id)] = list(bbox)
    return {
        "bbox_set": [list(bbox) for bbox in bbox_set],
        "pixel_bbox_set": [list(bbox) for bbox in bbox_set],
        "generation_label_bbox": list(generation_label_bbox),
        "person_symbol_bbox_map": dict(person_symbol_bbox_map),
    }


__all__ = [
    "GENERATION_LABELS",
    "PEDIGREE_RELATEDNESS_LABELS",
    "PEDIGREE_RELATEDNESS_OPTION_LABELS",
    "PEDIGREE_RELATIONSHIP_LABELS",
    "PEDIGREE_SEX_LABELS",
    "SUPPORTED_PEDIGREE_RELATEDNESS_QUERY_IDS",
    "SUPPORTED_PEDIGREE_RELATIONSHIP_QUERY_IDS",
    "SUPPORTED_PEDIGREE_SCENE_VARIANTS",
    "PedigreeFamily",
    "PedigreePerson",
    "PedigreeRelatednessQuerySample",
    "PedigreeRelationshipQuerySample",
    "PedigreeSample",
    "RenderedPedigreePerson",
    "RenderedPedigreeScene",
    "pedigree_family_relations",
    "pedigree_scene_entities",
    "projected_keyed_pedigree_person_annotation",
    "render_pedigree_chart_scene",
    "sample_pedigree_relatedness",
    "sample_pedigree_relationship",
]
