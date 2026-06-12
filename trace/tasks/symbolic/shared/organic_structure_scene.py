"""Reusable constrained organic-structure notation scene helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ...shared.bbox_projection import round_bbox


BOND_ORDER_VALUES: Mapping[str, int] = {"single": 1, "double": 2, "triple": 3}
SUPPORTED_BOND_ORDERS: Tuple[str, ...] = ("single", "double", "triple")
SUPPORTED_ORGANIC_RING_SIZES: Tuple[int, ...] = (5, 6)
ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT = 4
ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT = 4
ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT = 4


@dataclass(frozen=True)
class OrganicAtom:
    item_id: str
    x: float
    y: float
    element: str = "C"
    implicit: bool = True


@dataclass(frozen=True)
class OrganicBond:
    item_id: str
    atom_a: int
    atom_b: int
    order: str
    role: str = "backbone"
    ring_index: int | None = None


@dataclass(frozen=True)
class OrganicStructureSpec:
    atoms: Tuple[OrganicAtom, ...]
    bonds: Tuple[OrganicBond, ...]
    ring_atom_sets: Tuple[Tuple[int, ...], ...]
    scaffold_id: str
    scaffold_family: str
    target_bond_order: str
    target_answer_value: int
    constraint_policy: str


@dataclass(frozen=True)
class OrganicConstraintReport:
    valence_by_atom_id: Dict[str, int]
    max_valence: int
    branch_point_atom_ids: Tuple[str, ...]
    min_branch_angle_degrees: float | None
    triple_linear_atom_ids: Tuple[str, ...]
    ring_sizes: Tuple[int, ...]
    crossing_count: int

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "valence_by_atom_id": dict(self.valence_by_atom_id),
            "max_valence": int(self.max_valence),
            "branch_point_atom_ids": list(self.branch_point_atom_ids),
            "min_branch_angle_degrees": None
            if self.min_branch_angle_degrees is None
            else round(float(self.min_branch_angle_degrees), 3),
            "triple_linear_atom_ids": list(self.triple_linear_atom_ids),
            "ring_sizes": [int(value) for value in self.ring_sizes],
            "crossing_count": int(self.crossing_count),
        }


@dataclass(frozen=True)
class OrganicProjection:
    atom_points_px: Tuple[Tuple[float, float], ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class OrganicRenderedStructure:
    entities: Tuple[Dict[str, Any], ...]
    item_bboxes: Dict[str, Tuple[float, float, float, float]]
    item_point_pairs: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]
    item_points: Dict[str, Tuple[float, float]]
    metadata: Dict[str, Any]


def _regular_ring_vertices(cx: float, cy: float, radius: float, sides: int, phase: float) -> Tuple[Tuple[float, float], ...]:
    return tuple(
        (
            float(cx) + float(radius) * math.cos(float(phase) + 2.0 * math.pi * idx / int(sides)),
            float(cy) + float(radius) * math.sin(float(phase) + 2.0 * math.pi * idx / int(sides)),
        )
        for idx in range(int(sides))
    )


def _new_atom(atoms: list[OrganicAtom], x: float, y: float) -> int:
    atom_index = len(atoms)
    atoms.append(OrganicAtom(item_id=f"atom_{atom_index:02d}", x=float(x), y=float(y)))
    return atom_index


def _new_bond(
    bonds: list[OrganicBond],
    atom_a: int,
    atom_b: int,
    order: str,
    *,
    role: str = "backbone",
    ring_index: int | None = None,
) -> str:
    bond_id = f"bond_{len(bonds) + 1:02d}"
    bonds.append(
        OrganicBond(
            item_id=bond_id,
            atom_a=int(atom_a),
            atom_b=int(atom_b),
            order=str(order),
            role=str(role),
            ring_index=ring_index,
        )
    )
    return bond_id


def _target_bond_ids(spec: OrganicStructureSpec, target_bond_order: str) -> Tuple[str, ...]:
    return tuple(str(bond.item_id) for bond in spec.bonds if str(bond.order) == str(target_bond_order))


def _atom_degrees(spec: OrganicStructureSpec) -> Tuple[int, ...]:
    degrees = [0 for _ in spec.atoms]
    for bond in spec.bonds:
        degrees[int(bond.atom_a)] += 1
        degrees[int(bond.atom_b)] += 1
    return tuple(int(value) for value in degrees)


def organic_branch_point_atom_indices(spec: OrganicStructureSpec) -> Tuple[int, ...]:
    """Return skeletal vertices where three or more drawn bonds meet."""

    return tuple(idx for idx, degree in enumerate(_atom_degrees(spec)) if int(degree) >= 3)


def _target_branch_atom_ids(spec: OrganicStructureSpec) -> Tuple[str, ...]:
    return tuple(str(spec.atoms[idx].item_id) for idx in organic_branch_point_atom_indices(spec))


def organic_ring_item_ids(spec: OrganicStructureSpec, target_ring_size: int) -> Tuple[str, ...]:
    """Return ring item ids whose rendered polygon has the requested vertex count."""

    return tuple(
        f"ring_{ring_index + 1:02d}"
        for ring_index, ring_atoms in enumerate(spec.ring_atom_sets)
        if len(ring_atoms) == int(target_ring_size)
    )


def _make_polyene_scaffold(rng: Any, *, target_bond_order: str, answer_count: int) -> OrganicStructureSpec:
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    edge_count = int(answer_count) * 2 + rng.choice((1, 2))
    atom_count = edge_count + 1
    for idx in range(atom_count):
        _new_atom(atoms, float(idx) * 0.92, 0.42 if idx % 2 else -0.42)

    target_edge_indices = set(range(0, int(answer_count) * 2, 2))
    for edge_index in range(edge_count):
        order = "double" if edge_index in target_edge_indices else "single"
        _new_bond(bonds, edge_index, edge_index + 1, order, role="polyene_backbone")

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=tuple(),
        scaffold_id=f"polyene_chain_{answer_count}",
        scaffold_family="polyene_chain",
        target_bond_order=str(target_bond_order),
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_cycloalkene_scaffold(_rng: Any, *, target_bond_order: str, answer_count: int) -> OrganicStructureSpec:
    if int(answer_count) > 3:
        raise ValueError("cycloalkene scaffold supports at most three target double bonds")
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    for x, y in _regular_ring_vertices(0.0, 0.0, 1.08, 6, math.pi / 6):
        _new_atom(atoms, x, y)

    double_edges_by_count = {
        1: (0,),
        2: (0, 3),
        3: (0, 2, 4),
    }
    target_edges = set(double_edges_by_count[int(answer_count)])
    for edge_index in range(6):
        order = "double" if edge_index in target_edges else "single"
        _new_bond(bonds, edge_index, (edge_index + 1) % 6, order, role="ring", ring_index=0)

    anchor = 5
    center_x = sum(atom.x for atom in atoms[:6]) / 6.0
    center_y = sum(atom.y for atom in atoms[:6]) / 6.0
    ax = atoms[anchor].x
    ay = atoms[anchor].y
    angle = math.atan2(ay - center_y, ax - center_x)
    tail = _new_atom(atoms, ax + 0.95 * math.cos(angle), ay + 0.95 * math.sin(angle))
    _new_bond(bonds, anchor, tail, "single", role="side_chain")

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=((0, 1, 2, 3, 4, 5),),
        scaffold_id=f"cycloalkene_ring_{answer_count}",
        scaffold_family="cycloalkene_ring",
        target_bond_order=str(target_bond_order),
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_polyyne_scaffold(_rng: Any, *, target_bond_order: str, answer_count: int) -> OrganicStructureSpec:
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    atom_count = int(answer_count) * 2 + 2
    for idx in range(atom_count):
        _new_atom(atoms, float(idx) * 0.78, 0.0)

    target_edges = set(range(1, int(answer_count) * 2, 2))
    for edge_index in range(atom_count - 1):
        order = "triple" if edge_index in target_edges else "single"
        _new_bond(bonds, edge_index, edge_index + 1, order, role="polyyne_backbone")

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=tuple(),
        scaffold_id=f"polyyne_chain_{answer_count}",
        scaffold_family="polyyne_chain",
        target_bond_order=str(target_bond_order),
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_alkynyl_ring_scaffold(_rng: Any, *, target_bond_order: str, answer_count: int) -> OrganicStructureSpec:
    if int(answer_count) > 3:
        raise ValueError("alkynyl ring scaffold supports at most three target triple bonds")
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    ring_points = _regular_ring_vertices(0.0, 0.0, 1.08, 6, math.pi / 6)
    for x, y in ring_points:
        _new_atom(atoms, x, y)

    for edge_index in range(6):
        order = "double" if edge_index in (0, 2, 4) else "single"
        _new_bond(bonds, edge_index, (edge_index + 1) % 6, order, role="aromatic_ring", ring_index=0)

    anchors_by_count = {
        1: (1,),
        2: (1, 4),
        3: (1, 3, 5),
    }
    center_x = sum(atom.x for atom in atoms[:6]) / 6.0
    center_y = sum(atom.y for atom in atoms[:6]) / 6.0
    for anchor in anchors_by_count[int(answer_count)]:
        ax = atoms[anchor].x
        ay = atoms[anchor].y
        angle = math.atan2(ay - center_y, ax - center_x)
        first = _new_atom(atoms, ax + 0.72 * math.cos(angle), ay + 0.72 * math.sin(angle))
        second = _new_atom(atoms, atoms[first].x + 0.94 * math.cos(angle), atoms[first].y + 0.94 * math.sin(angle))
        _new_bond(bonds, anchor, first, "single", role="alkynyl_substituent")
        _new_bond(bonds, first, second, "triple", role="alkynyl_substituent")

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=((0, 1, 2, 3, 4, 5),),
        scaffold_id=f"alkynyl_ring_{answer_count}",
        scaffold_family="alkynyl_ring",
        target_bond_order=str(target_bond_order),
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_unbranched_alkane_scaffold(_rng: Any, *, answer_count: int) -> OrganicStructureSpec:
    if int(answer_count) != 0:
        raise ValueError("unbranched alkane scaffold only supports zero branch points")
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    for idx in range(7):
        _new_atom(atoms, float(idx) * 0.94, 0.40 if idx % 2 else -0.40)
    for edge_index in range(6):
        _new_bond(bonds, edge_index, edge_index + 1, "single", role="unbranched_backbone")
    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=tuple(),
        scaffold_id="unbranched_alkane_0",
        scaffold_family="unbranched_alkane",
        target_bond_order="not_applicable",
        target_answer_value=0,
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_branched_alkane_scaffold(_rng: Any, *, answer_count: int) -> OrganicStructureSpec:
    if int(answer_count) < 1 or int(answer_count) > ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT:
        raise ValueError("branched alkane scaffold supports branch-point counts 1..4")
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    branch_count = int(answer_count)
    backbone_count = max(7, branch_count * 2 + 4)
    for idx in range(backbone_count):
        _new_atom(atoms, float(idx) * 0.92, 0.42 if idx % 2 else -0.42)
    for edge_index in range(backbone_count - 1):
        _new_bond(bonds, edge_index, edge_index + 1, "single", role="branched_backbone")

    for branch_index in range(branch_count):
        anchor = 2 + branch_index * 2
        atom = atoms[anchor]
        outward = 1.0 if atom.y > 0 else -1.0
        tail = _new_atom(atoms, atom.x, atom.y + outward * 1.02)
        _new_bond(bonds, anchor, tail, "single", role="branch_substituent")

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=tuple(),
        scaffold_id=f"branched_alkane_{branch_count}",
        scaffold_family="branched_alkane",
        target_bond_order="not_applicable",
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_substituted_cycloalkane_scaffold(_rng: Any, *, answer_count: int) -> OrganicStructureSpec:
    if int(answer_count) < 0 or int(answer_count) > 3:
        raise ValueError("substituted cycloalkane scaffold supports branch-point counts 0..3")
    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    for x, y in _regular_ring_vertices(0.0, 0.0, 1.08, 6, math.pi / 6):
        _new_atom(atoms, x, y)
    for edge_index in range(6):
        _new_bond(bonds, edge_index, (edge_index + 1) % 6, "single", role="ring", ring_index=0)

    anchors_by_count = {
        0: tuple(),
        1: (0,),
        2: (0, 3),
        3: (0, 2, 4),
    }
    center_x = sum(atom.x for atom in atoms[:6]) / 6.0
    center_y = sum(atom.y for atom in atoms[:6]) / 6.0
    for anchor in anchors_by_count[int(answer_count)]:
        ax = atoms[anchor].x
        ay = atoms[anchor].y
        angle = math.atan2(ay - center_y, ax - center_x)
        tail = _new_atom(atoms, ax + 0.96 * math.cos(angle), ay + 0.96 * math.sin(angle))
        _new_bond(bonds, anchor, tail, "single", role="ring_substituent", ring_index=None)

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=((0, 1, 2, 3, 4, 5),),
        scaffold_id=f"substituted_cycloalkane_{int(answer_count)}",
        scaffold_family="substituted_cycloalkane",
        target_bond_order="not_applicable",
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def _make_separated_ring_size_scaffold(rng: Any, *, target_ring_size: int, answer_count: int) -> OrganicStructureSpec:
    target_ring_size = int(target_ring_size)
    answer_count = int(answer_count)
    if target_ring_size not in SUPPORTED_ORGANIC_RING_SIZES:
        raise ValueError(f"unsupported target ring size: {target_ring_size}")
    if answer_count < 0 or answer_count > ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT:
        raise ValueError(f"ring-size scaffold supports counts 0..{ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT}")

    distractor_ring_size = 5 if target_ring_size == 6 else 6
    max_total_rings = ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT
    max_distractors = max(0, max_total_rings - answer_count)
    if answer_count == 0:
        distractor_count = int(rng.choice(tuple(range(1, max_total_rings + 1))))
    else:
        distractor_count = int(rng.choice(tuple(range(min(2, max_distractors) + 1))))

    ring_sizes = [int(target_ring_size) for _ in range(answer_count)] + [int(distractor_ring_size) for _ in range(distractor_count)]
    rng.shuffle(ring_sizes)

    atoms: list[OrganicAtom] = []
    bonds: list[OrganicBond] = []
    ring_atom_sets: list[Tuple[int, ...]] = []
    ring_centers: list[Tuple[float, float]] = []
    ring_spacing = 3.15
    for ring_index, ring_size in enumerate(ring_sizes):
        cx = (float(ring_index) - (len(ring_sizes) - 1) / 2.0) * ring_spacing
        cy = 0.18 if ring_index % 2 else -0.18
        radius = 1.02 if int(ring_size) == 6 else 0.98
        ring_indices: list[int] = []
        for x, y in _regular_ring_vertices(cx, cy, radius, int(ring_size), 0.0):
            ring_indices.append(_new_atom(atoms, x, y))
        current_ring_index = len(ring_atom_sets)
        for edge_index in range(int(ring_size)):
            _new_bond(
                bonds,
                ring_indices[edge_index],
                ring_indices[(edge_index + 1) % int(ring_size)],
                "single",
                role="ring",
                ring_index=current_ring_index,
            )
        ring_atom_sets.append(tuple(ring_indices))
        ring_centers.append((float(cx), float(cy)))

    for left_ring_index in range(max(0, len(ring_atom_sets) - 1)):
        right_ring_index = left_ring_index + 1
        left_center = ring_centers[left_ring_index]
        right_center = ring_centers[right_ring_index]
        left_atom = max(
            ring_atom_sets[left_ring_index],
            key=lambda atom_index: (
                atoms[int(atom_index)].x - left_center[0],
                -abs(atoms[int(atom_index)].y - left_center[1]),
            ),
        )
        right_atom = min(
            ring_atom_sets[right_ring_index],
            key=lambda atom_index: (
                atoms[int(atom_index)].x - right_center[0],
                abs(atoms[int(atom_index)].y - right_center[1]),
            ),
        )
        _new_bond(bonds, int(left_atom), int(right_atom), "single", role="ring_link")

    return OrganicStructureSpec(
        atoms=tuple(atoms),
        bonds=tuple(bonds),
        ring_atom_sets=tuple(ring_atom_sets),
        scaffold_id=f"separated_rings_{target_ring_size}_{answer_count}_{len(ring_sizes)}",
        scaffold_family="separated_ring_chain",
        target_bond_order="not_applicable",
        target_answer_value=int(answer_count),
        constraint_policy="basic_carbon_valence_and_line_angle_geometry_v1",
    )


def build_constrained_organic_structure(rng: Any, *, target_bond_order: str, answer_count: int) -> OrganicStructureSpec:
    """Build a notation-plausible skeletal structure with exact target count."""

    target_bond_order = str(target_bond_order)
    answer_count = int(answer_count)
    if target_bond_order not in ("double", "triple"):
        raise ValueError(f"unsupported target bond order: {target_bond_order!r}")
    if answer_count < 1 or answer_count > ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT:
        raise ValueError(
            f"organic structures support answer counts 1..{ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT}; got {answer_count}"
        )

    builders: list[Any]
    if target_bond_order == "double":
        builders = [_make_polyene_scaffold]
        if answer_count <= 3:
            builders.append(_make_cycloalkene_scaffold)
    else:
        builders = [_make_polyyne_scaffold]
        if answer_count <= 3:
            builders.append(_make_alkynyl_ring_scaffold)

    rng.shuffle(builders)
    errors: list[str] = []
    for builder in builders:
        try:
            spec = builder(rng, target_bond_order=target_bond_order, answer_count=answer_count)
            report = validate_organic_structure(spec)
            target_ids = _target_bond_ids(spec, target_bond_order)
            if len(target_ids) != answer_count:
                raise ValueError(f"target count mismatch for {spec.scaffold_id}: {len(target_ids)} != {answer_count}")
            if report.crossing_count:
                raise ValueError(f"crossed bonds in {spec.scaffold_id}")
            return spec
        except ValueError as exc:
            errors.append(str(exc))
    raise RuntimeError(f"no constrained organic scaffold fit the request: {'; '.join(errors)}")


def build_constrained_organic_branch_structure(rng: Any, *, answer_count: int) -> OrganicStructureSpec:
    """Build a notation-plausible skeletal structure with exact branch-point count."""

    answer_count = int(answer_count)
    if answer_count < 0 or answer_count > ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT:
        raise ValueError(
            f"organic branch structures support answer counts 0..{ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT}; got {answer_count}"
        )

    builders: list[Any] = []
    if answer_count == 0:
        builders.extend([_make_unbranched_alkane_scaffold, _make_substituted_cycloalkane_scaffold])
    else:
        builders.append(_make_branched_alkane_scaffold)
        if answer_count <= 3:
            builders.append(_make_substituted_cycloalkane_scaffold)

    rng.shuffle(builders)
    errors: list[str] = []
    for builder in builders:
        try:
            spec = builder(rng, answer_count=answer_count)
            report = validate_organic_structure(spec)
            branch_ids = _target_branch_atom_ids(spec)
            if len(branch_ids) != answer_count:
                raise ValueError(f"branch-point count mismatch for {spec.scaffold_id}: {len(branch_ids)} != {answer_count}")
            if report.crossing_count:
                raise ValueError(f"crossed bonds in {spec.scaffold_id}")
            return spec
        except ValueError as exc:
            errors.append(str(exc))
    raise RuntimeError(f"no constrained organic branch scaffold fit the request: {'; '.join(errors)}")


def build_constrained_organic_ring_size_structure(rng: Any, *, target_ring_size: int, answer_count: int) -> OrganicStructureSpec:
    """Build a notation-plausible separated-ring structure with exact target ring count."""

    target_ring_size = int(target_ring_size)
    answer_count = int(answer_count)
    if target_ring_size not in SUPPORTED_ORGANIC_RING_SIZES:
        raise ValueError(f"unsupported target ring size: {target_ring_size}")
    if answer_count < 0 or answer_count > ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT:
        raise ValueError(
            f"organic ring-size structures support answer counts 0..{ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT}; got {answer_count}"
        )

    errors: list[str] = []
    for _attempt in range(8):
        try:
            spec = _make_separated_ring_size_scaffold(rng, target_ring_size=target_ring_size, answer_count=answer_count)
            report = validate_organic_structure(spec)
            matching_ids = organic_ring_item_ids(spec, target_ring_size)
            if len(matching_ids) != answer_count:
                raise ValueError(f"ring-size count mismatch for {spec.scaffold_id}: {len(matching_ids)} != {answer_count}")
            if report.crossing_count:
                raise ValueError(f"crossed bonds in {spec.scaffold_id}")
            return spec
        except ValueError as exc:
            errors.append(str(exc))
    raise RuntimeError(f"no constrained organic ring-size scaffold fit the request: {'; '.join(errors)}")


def validate_organic_structure(spec: OrganicStructureSpec) -> OrganicConstraintReport:
    atom_count = len(spec.atoms)
    valences = [0 for _ in range(atom_count)]
    neighbors: list[list[Tuple[int, OrganicBond]]] = [[] for _ in range(atom_count)]
    for bond in spec.bonds:
        if bond.order not in BOND_ORDER_VALUES:
            raise ValueError(f"unsupported bond order {bond.order!r}")
        if bond.atom_a == bond.atom_b:
            raise ValueError("self-bonds are not allowed")
        if bond.atom_a < 0 or bond.atom_a >= atom_count or bond.atom_b < 0 or bond.atom_b >= atom_count:
            raise ValueError("bond endpoint is out of range")
        order_value = int(BOND_ORDER_VALUES[str(bond.order)])
        valences[bond.atom_a] += order_value
        valences[bond.atom_b] += order_value
        neighbors[bond.atom_a].append((bond.atom_b, bond))
        neighbors[bond.atom_b].append((bond.atom_a, bond))

    over_valent = [spec.atoms[idx].item_id for idx, value in enumerate(valences) if value > 4]
    if over_valent:
        raise ValueError(f"carbon valence exceeded for {over_valent}")

    multiple_counts = [0 for _ in range(atom_count)]
    for bond in spec.bonds:
        if bond.order in ("double", "triple"):
            multiple_counts[bond.atom_a] += 1
            multiple_counts[bond.atom_b] += 1
    crowded_multiple = [spec.atoms[idx].item_id for idx, value in enumerate(multiple_counts) if value > 1]
    if crowded_multiple:
        raise ValueError(f"adjacent cumulated multiple bonds are not supported: {crowded_multiple}")

    triple_linear_atom_ids: list[str] = []
    for bond in spec.bonds:
        if bond.order != "triple":
            continue
        for atom_index, partner_index in ((bond.atom_a, bond.atom_b), (bond.atom_b, bond.atom_a)):
            if len(neighbors[atom_index]) > 2:
                raise ValueError(f"triple-bond atom {spec.atoms[atom_index].item_id} is branched")
            if len(neighbors[atom_index]) == 2:
                other_index = next(idx for idx, _bond in neighbors[atom_index] if idx != partner_index)
                dot = _normalized_dot(spec.atoms[atom_index], spec.atoms[partner_index], spec.atoms[other_index])
                if dot > -0.94:
                    raise ValueError(f"triple-bond atom {spec.atoms[atom_index].item_id} is not linear")
                triple_linear_atom_ids.append(spec.atoms[atom_index].item_id)

    for ring in spec.ring_atom_sets:
        if len(ring) not in (5, 6):
            raise ValueError("v1 organic rings must be pentagons or hexagons")

    branch_indices = organic_branch_point_atom_indices(spec)
    branch_angles: list[float] = []
    for atom_index in branch_indices:
        branch_angles.append(_minimum_incident_angle_degrees(spec, int(atom_index), neighbors[int(atom_index)]))
    min_branch_angle = min(branch_angles) if branch_angles else None
    if min_branch_angle is not None and float(min_branch_angle) < 40.0:
        raise ValueError(f"branch angle is too cramped: {min_branch_angle:.2f} degrees")

    crossing_count = _count_crossings(spec)
    if crossing_count:
        raise ValueError(f"structure has {crossing_count} crossed bond(s)")

    return OrganicConstraintReport(
        valence_by_atom_id={spec.atoms[idx].item_id: int(value) for idx, value in enumerate(valences)},
        max_valence=max(valences) if valences else 0,
        branch_point_atom_ids=tuple(spec.atoms[idx].item_id for idx in branch_indices),
        min_branch_angle_degrees=None if min_branch_angle is None else float(min_branch_angle),
        triple_linear_atom_ids=tuple(triple_linear_atom_ids),
        ring_sizes=tuple(len(ring) for ring in spec.ring_atom_sets),
        crossing_count=int(crossing_count),
    )


def _minimum_incident_angle_degrees(
    spec: OrganicStructureSpec,
    atom_index: int,
    neighbors: Sequence[Tuple[int, OrganicBond]],
) -> float:
    origin = spec.atoms[int(atom_index)]
    angles: list[float] = []
    for left_index, (left_neighbor, _left_bond) in enumerate(neighbors):
        for right_neighbor, _right_bond in neighbors[left_index + 1 :]:
            dot = max(
                -1.0,
                min(
                    1.0,
                    _normalized_dot(origin, spec.atoms[int(left_neighbor)], spec.atoms[int(right_neighbor)]),
                ),
            )
            angles.append(math.degrees(math.acos(dot)))
    return min(angles) if angles else 180.0


def _normalized_dot(origin: OrganicAtom, a: OrganicAtom, b: OrganicAtom) -> float:
    ax = float(a.x) - float(origin.x)
    ay = float(a.y) - float(origin.y)
    bx = float(b.x) - float(origin.x)
    by = float(b.y) - float(origin.y)
    alen = math.hypot(ax, ay) or 1.0
    blen = math.hypot(bx, by) or 1.0
    return (ax * bx + ay * by) / (alen * blen)


def _count_crossings(spec: OrganicStructureSpec) -> int:
    crossings = 0
    for left_index, left in enumerate(spec.bonds):
        left_atoms = {left.atom_a, left.atom_b}
        a = spec.atoms[left.atom_a]
        b = spec.atoms[left.atom_b]
        for right in spec.bonds[left_index + 1 :]:
            if left_atoms.intersection({right.atom_a, right.atom_b}):
                continue
            c = spec.atoms[right.atom_a]
            d = spec.atoms[right.atom_b]
            if _segments_intersect((a.x, a.y), (b.x, b.y), (c.x, c.y), (d.x, d.y)):
                crossings += 1
    return crossings


def _segments_intersect(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
) -> bool:
    def orient(p: Tuple[float, float], q: Tuple[float, float], r: Tuple[float, float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    return (o1 * o2 < -1e-9) and (o3 * o4 < -1e-9)


def project_organic_structure(
    *,
    spec: OrganicStructureSpec,
    panel_bbox: Tuple[int, int, int, int],
    structure_width_px: int,
    structure_height_px: int,
    instance_seed: int,
    namespace: str,
) -> OrganicProjection:
    rng = spawn_rng(int(instance_seed), f"{namespace}.layout_projection")
    min_x = min(atom.x for atom in spec.atoms)
    max_x = max(atom.x for atom in spec.atoms)
    min_y = min(atom.y for atom in spec.atoms)
    max_y = max(atom.y for atom in spec.atoms)
    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)
    available_w = min(int(structure_width_px), int(panel_bbox[2] - panel_bbox[0]) - 110)
    available_h = min(int(structure_height_px), int(panel_bbox[3] - panel_bbox[1]) - 120)
    scale = min(float(available_w) / width, float(available_h) / height)
    scale *= rng.choice((0.82, 0.88, 0.94))
    cx = (panel_bbox[0] + panel_bbox[2]) / 2.0 + rng.uniform(-26.0, 26.0)
    cy = (panel_bbox[1] + panel_bbox[3]) / 2.0 + rng.uniform(-18.0, 18.0)
    source_cx = (min_x + max_x) / 2.0
    source_cy = (min_y + max_y) / 2.0
    points = tuple((cx + (atom.x - source_cx) * scale, cy + (atom.y - source_cy) * scale) for atom in spec.atoms)
    return OrganicProjection(
        atom_points_px=points,
        metadata={
            "projected_atoms_px": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
            "atom_count": int(len(points)),
            "bond_count": int(len(spec.bonds)),
            "projection_scale": round(float(scale), 6),
            "scaffold_id": str(spec.scaffold_id),
            "scaffold_family": str(spec.scaffold_family),
        },
    )


def _bond_bbox(p0: Tuple[float, float], p1: Tuple[float, float], pad: float) -> Tuple[float, float, float, float]:
    return round_bbox((min(p0[0], p1[0]) - pad, min(p0[1], p1[1]) - pad, max(p0[0], p1[0]) + pad, max(p0[1], p1[1]) + pad))


def _shortened_points(p0: Tuple[float, float], p1: Tuple[float, float], shorten_px: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    dx = float(p1[0]) - float(p0[0])
    dy = float(p1[1]) - float(p0[1])
    length = math.hypot(dx, dy) or 1.0
    amount = min(float(shorten_px), length * 0.18)
    ux = dx / length
    uy = dy / length
    return (p0[0] + ux * amount, p0[1] + uy * amount), (p1[0] - ux * amount, p1[1] - uy * amount)


def _draw_offset_line(
    draw: ImageDraw.ImageDraw,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    *,
    offset: float,
    fill: Tuple[int, int, int],
    width: int,
) -> None:
    dx = float(p1[0]) - float(p0[0])
    dy = float(p1[1]) - float(p0[1])
    length = math.hypot(dx, dy) or 1.0
    nx = -dy / length
    ny = dx / length
    draw.line(
        (p0[0] + nx * offset, p0[1] + ny * offset, p1[0] + nx * offset, p1[1] + ny * offset),
        fill=fill,
        width=int(width),
        joint="curve",
    )


def _ring_centers(spec: OrganicStructureSpec, points: Sequence[Tuple[float, float]]) -> Dict[int, Tuple[float, float]]:
    centers: Dict[int, Tuple[float, float]] = {}
    for ring_index, ring_atoms in enumerate(spec.ring_atom_sets):
        xs = [float(points[int(idx)][0]) for idx in ring_atoms]
        ys = [float(points[int(idx)][1]) for idx in ring_atoms]
        centers[int(ring_index)] = (sum(xs) / len(xs), sum(ys) / len(ys))
    return centers


def _draw_bond(
    draw: ImageDraw.ImageDraw,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    *,
    order: str,
    ring_center: Tuple[float, float] | None,
    bond_rgb: Tuple[int, int, int],
    bond_width_px: int,
    bond_gap_px: int,
) -> None:
    if str(order) == "double" and ring_center is not None:
        inner0, inner1 = _shortened_points(p0, p1, max(8.0, float(bond_gap_px)))
        draw.line((p0[0], p0[1], p1[0], p1[1]), fill=bond_rgb, width=int(bond_width_px), joint="curve")
        dx = float(p1[0]) - float(p0[0])
        dy = float(p1[1]) - float(p0[1])
        length = math.hypot(dx, dy) or 1.0
        nx = -dy / length
        ny = dx / length
        mx = (p0[0] + p1[0]) / 2.0
        my = (p0[1] + p1[1]) / 2.0
        if ((ring_center[0] - mx) * nx + (ring_center[1] - my) * ny) < 0:
            nx *= -1.0
            ny *= -1.0
        offset = float(bond_gap_px)
        draw.line(
            (inner0[0] + nx * offset, inner0[1] + ny * offset, inner1[0] + nx * offset, inner1[1] + ny * offset),
            fill=bond_rgb,
            width=int(bond_width_px),
            joint="curve",
        )
        return
    if str(order) == "double":
        line0, line1 = _shortened_points(p0, p1, max(5.0, float(bond_gap_px) * 0.75))
        gap = float(bond_gap_px) / 2.0
        _draw_offset_line(draw, line0, line1, offset=-gap, fill=bond_rgb, width=int(bond_width_px))
        _draw_offset_line(draw, line0, line1, offset=gap, fill=bond_rgb, width=int(bond_width_px))
        return
    if str(order) == "triple":
        line0, line1 = _shortened_points(p0, p1, max(7.0, float(bond_gap_px)))
        gap = float(bond_gap_px)
        _draw_offset_line(draw, line0, line1, offset=-gap, fill=bond_rgb, width=int(bond_width_px))
        _draw_offset_line(draw, line0, line1, offset=0.0, fill=bond_rgb, width=int(bond_width_px))
        _draw_offset_line(draw, line0, line1, offset=gap, fill=bond_rgb, width=int(bond_width_px))
        return
    draw.line((p0[0], p0[1], p1[0], p1[1]), fill=bond_rgb, width=int(bond_width_px), joint="curve")


def draw_organic_structure(
    draw: ImageDraw.ImageDraw,
    *,
    spec: OrganicStructureSpec,
    projection: OrganicProjection,
    bond_rgb: Tuple[int, int, int],
    bond_width_px: int,
    bond_gap_px: int,
) -> OrganicRenderedStructure:
    points = projection.atom_points_px
    ring_centers = _ring_centers(spec, points)
    item_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    item_point_pairs: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {}
    item_points: Dict[str, Tuple[float, float]] = {}
    entities: list[Dict[str, Any]] = []

    for bond in spec.bonds:
        p0 = points[int(bond.atom_a)]
        p1 = points[int(bond.atom_b)]
        _draw_bond(
            draw,
            p0,
            p1,
            order=str(bond.order),
            ring_center=ring_centers.get(int(bond.ring_index)) if bond.ring_index is not None else None,
            bond_rgb=bond_rgb,
            bond_width_px=int(bond_width_px),
            bond_gap_px=int(bond_gap_px),
        )
        bbox = _bond_bbox(p0, p1, pad=max(10.0, float(bond_gap_px + bond_width_px + 4)))
        point_pair = (
            (round(float(p0[0]), 3), round(float(p0[1]), 3)),
            (round(float(p1[0]), 3), round(float(p1[1]), 3)),
        )
        item_bboxes[str(bond.item_id)] = bbox
        item_point_pairs[str(bond.item_id)] = point_pair
        entities.append(
            {
                "entity_id": str(bond.item_id),
                "entity_type": "organic_bond",
                "bbox_px": list(bbox),
                "point_pair_px": [list(point) for point in point_pair],
                "from_atom": int(bond.atom_a),
                "to_atom": int(bond.atom_b),
                "bond_order": str(bond.order),
                "bond_role": str(bond.role),
                "ring_index": None if bond.ring_index is None else int(bond.ring_index),
            }
        )

    for atom_index, point in enumerate(points):
        atom = spec.atoms[int(atom_index)]
        point_value = (round(float(point[0]), 3), round(float(point[1]), 3))
        item_points[str(atom.item_id)] = point_value
        entities.append(
            {
                "entity_id": str(atom.item_id),
                "entity_type": "organic_line_angle_vertex",
                "center_px": [float(point_value[0]), float(point_value[1])],
                "element": str(atom.element),
                "implicit": bool(atom.implicit),
            }
        )

    for ring_index, ring_atoms in enumerate(spec.ring_atom_sets, start=1):
        xs = [points[int(idx)][0] for idx in ring_atoms]
        ys = [points[int(idx)][1] for idx in ring_atoms]
        bbox = round_bbox((min(xs), min(ys), max(xs), max(ys)))
        ring_id = f"ring_{ring_index:02d}"
        item_bboxes[ring_id] = bbox
        entities.append(
            {
                "entity_id": ring_id,
                "entity_type": "organic_ring",
                "bbox_px": list(bbox),
                "atom_indices": [int(idx) for idx in ring_atoms],
                "ring_size": int(len(ring_atoms)),
            }
        )

    return OrganicRenderedStructure(
        entities=tuple(entities),
        item_bboxes=item_bboxes,
        item_point_pairs=item_point_pairs,
        item_points=item_points,
        metadata={
            "bond_render_style": "line_angle_shortened_multiple_bonds_v1",
            "bond_bbox_policy": "bond_segment_bbox_with_multiple_bond_padding_for_debug_only",
            "bond_annotation_policy": "semantic_bond_endpoint_point_pair",
            "vertex_annotation_policy": "semantic_line_angle_vertex_center_point",
        },
    )


__all__ = [
    "BOND_ORDER_VALUES",
    "ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT",
    "ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT",
    "ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT",
    "OrganicAtom",
    "OrganicBond",
    "OrganicConstraintReport",
    "OrganicProjection",
    "OrganicRenderedStructure",
    "OrganicStructureSpec",
    "SUPPORTED_BOND_ORDERS",
    "SUPPORTED_ORGANIC_RING_SIZES",
    "build_constrained_organic_branch_structure",
    "build_constrained_organic_ring_size_structure",
    "build_constrained_organic_structure",
    "draw_organic_structure",
    "organic_branch_point_atom_indices",
    "organic_ring_item_ids",
    "project_organic_structure",
    "validate_organic_structure",
]
