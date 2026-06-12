"""Identity-free semantic sampling primitives for dominoes scene tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.games.shared.layout import resolve_games_layout_jitter
from trace.tasks.games.shared.style import SUPPORTED_DOMINO_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import sample_font_family
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .rendering import DominoRenderParams, DominoTileInstance
from .state import (
    CANONICAL_DOMINOES,
    DEFAULTS,
    DOMINOES_NAMESPACE,
    OPTION_LABELS,
    PIP_VALUES,
    SUPPORTED_DOMINO_SCENE_VARIANTS,
    DominoIntegerAxis,
    DominoSceneAxes,
    SampledDominoScene,
)


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one named axis without task identity."""

    rng = spawn_rng(int(instance_seed), f"{DOMINOES_NAMESPACE}.{str(namespace)}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{DOMINOES_NAMESPACE}.{str(namespace)}",
    )
    return str(selected), dict(probabilities)


def resolve_domino_scene_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> DominoSceneAxes:
    """Resolve scene and style axes common to dominoes tasks."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_DOMINO_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_DOMINO_STYLE_VARIANTS,
    )
    return DominoSceneAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
    )


def resolve_domino_integer_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> DominoIntegerAxis:
    """Resolve one task-owned integer axis."""

    support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=support,
        namespace=f"{DOMINOES_NAMESPACE}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return DominoIntegerAxis(value=int(value), support=tuple(int(v) for v in support), probabilities=dict(probabilities))


def resolve_domino_target_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    fallback_support: Sequence[int],
    namespace: str,
) -> DominoIntegerAxis:
    """Resolve a task-owned target answer axis."""

    return resolve_domino_integer_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=fallback_support,
        namespace=str(namespace),
        balanced_flag_key="balanced_target_answer_sampling",
    )


def resolve_domino_candidate_count_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    scene_variant: str,
    objective_key: str,
    target_answer: int,
) -> DominoIntegerAxis:
    """Resolve a feasible visible candidate count for a dominoes task."""

    support_key = _candidate_count_support_key(str(scene_variant))
    raw_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=support_key,
        fallback=getattr(DEFAULTS, support_key),
    )
    feasible = _feasible_candidate_count_support(
        query_id=str(objective_key),
        target_answer=int(target_answer),
        raw_support=raw_support,
    )
    if not feasible:
        raise ValueError(f"no feasible candidate_count values remain for {objective_key}/{scene_variant}")
    candidate_params = dict(params)
    candidate_params[support_key] = [int(value) for value in feasible]
    return resolve_domino_integer_axis(
        instance_seed=int(instance_seed),
        params=candidate_params,
        gen_defaults=gen_defaults,
        support_key=support_key,
        explicit_key="candidate_count",
        fallback_support=feasible,
        namespace=f"candidate_count.{str(scene_variant)}.{str(objective_key)}",
        balanced_flag_key="balanced_candidate_count_sampling",
    )


def _canonical_tile(left_value: int, right_value: int) -> Tuple[int, int]:
    """Return the canonical unordered representation for one domino tile."""

    lower = min(int(left_value), int(right_value))
    upper = max(int(left_value), int(right_value))
    return (int(lower), int(upper))


def _tile_sum(tile: Tuple[int, int]) -> int:
    """Return the pip sum for one canonical domino tile."""

    return int(tile[0] + tile[1])


def _build_tile_instance(
    *,
    tile_id: str,
    oriented_tile: Tuple[int, int],
    role: str,
    is_reference: bool = False,
    highlight_right_half: bool = False,
    option_label: str | None = None,
) -> DominoTileInstance:
    """Build one rendered domino tile payload from oriented half values."""

    return DominoTileInstance(
        tile_id=str(tile_id),
        left_value=int(oriented_tile[0]),
        right_value=int(oriented_tile[1]),
        role=str(role),
        is_reference=bool(is_reference),
        highlight_right_half=bool(highlight_right_half),
        option_label=None if option_label is None else str(option_label),
    )


def _candidate_count_support_key(scene_variant: str) -> str:
    """Return the configured visible candidate-count support key for one layout family."""

    return {
        "single_row": "single_row_candidate_count_support",
        "two_row": "two_row_candidate_count_support",
    }[str(scene_variant)]


def _feasible_candidate_count_support(
    *,
    query_id: str,
    target_answer: int,
    raw_support: Sequence[int],
) -> Tuple[int, ...]:
    """Return the subset of candidate-count support that can realize the active query."""

    feasible: List[int] = []
    for raw_value in raw_support:
        candidate_count = int(raw_value)
        if str(query_id) == "second_play_candidate_count":
            minimum = max(7, int(target_answer) + 1)
        elif str(query_id) == "extendable_first_play_count":
            minimum = max(7, int(target_answer) * 2)
        else:
            minimum = max(7, int(target_answer))
        if str(query_id) == "sum_to_target_count" and int(target_answer) == 0:
            minimum = 7
        if int(candidate_count) < int(minimum):
            continue
        feasible.append(int(candidate_count))
    return tuple(int(value) for value in feasible)


def _sample_chain_with_end(
    rng,
    *,
    end_tile: Tuple[int, int],
    avoid_prefix_values: Sequence[int] = (),
    avoid_prefix_doubles: bool = False,
) -> Tuple[Tuple[int, int], ...]:
    """Sample one valid oriented 3-tile chain whose rightmost tile is `end_tile`.

    `avoid_prefix_values` keeps the first two tiles from consuming certain values so
    query-specific answer pools remain stable (for example the open-end value for
    `matching_end_count` or all doubles for `double_count`).
    """

    end_left = int(end_tile[0])
    end_right = int(end_tile[1])
    blocked_values = {int(value) for value in avoid_prefix_values}
    disallowed = {_canonical_tile(int(end_left), int(end_right))}
    middle_options: List[Tuple[int, int]] = []
    for middle_left in PIP_VALUES:
        middle_canonical = _canonical_tile(int(middle_left), int(end_left))
        if middle_canonical in disallowed:
            continue
        if int(middle_left) in blocked_values or int(end_left) in blocked_values:
            continue
        if bool(avoid_prefix_doubles) and int(middle_left) == int(end_left):
            continue
        middle_options.append((int(middle_left), int(end_left)))
    if not middle_options:
        raise ValueError("unable to sample middle domino for chain")
    middle_tile = middle_options[int(rng.randrange(len(middle_options)))]
    disallowed.add(_canonical_tile(int(middle_tile[0]), int(middle_tile[1])))

    first_options: List[Tuple[int, int]] = []
    for first_left in PIP_VALUES:
        first_canonical = _canonical_tile(int(first_left), int(middle_tile[0]))
        if first_canonical in disallowed:
            continue
        if int(first_left) in blocked_values or int(middle_tile[0]) in blocked_values:
            continue
        if bool(avoid_prefix_doubles) and int(first_left) == int(middle_tile[0]):
            continue
        first_options.append((int(first_left), int(middle_tile[0])))
    if not first_options:
        raise ValueError("unable to sample first domino for chain")
    first_tile = first_options[int(rng.randrange(len(first_options)))]
    return (
        (int(first_tile[0]), int(first_tile[1])),
        (int(middle_tile[0]), int(middle_tile[1])),
        (int(end_left), int(end_right)),
    )


def _sample_generic_chain(
    rng,
    *,
    avoid_doubles: bool,
) -> Tuple[Tuple[int, int], ...]:
    """Sample one generic valid 3-tile chain."""

    for _ in range(96):
        end_left = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        end_right = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        if bool(avoid_doubles) and int(end_left) == int(end_right):
            continue
        try:
            chain = _sample_chain_with_end(
                rng,
                end_tile=(int(end_left), int(end_right)),
                avoid_prefix_doubles=bool(avoid_doubles),
            )
        except ValueError:
            continue
        if bool(avoid_doubles) and any(int(left_value) == int(right_value) for left_value, right_value in chain):
            continue
        return chain
    raise ValueError("unable to sample generic domino chain")


def _candidate_pool_for_chain(oriented_chain: Sequence[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
    """Return the canonical domino pool not already consumed by the visible chain."""

    chain_tiles = {_canonical_tile(int(left_value), int(right_value)) for left_value, right_value in oriented_chain}
    return tuple(tile for tile in CANONICAL_DOMINOES if tile not in chain_tiles)


def _random_orientation(rng, *, tile: Tuple[int, int]) -> Tuple[int, int]:
    """Return one random visible orientation for a canonical domino tile."""

    left_value, right_value = int(tile[0]), int(tile[1])
    if int(left_value) == int(right_value):
        return (int(left_value), int(right_value))
    if bool(rng.randrange(2)):
        return (int(left_value), int(right_value))
    return (int(right_value), int(left_value))


def _can_connect(tile: Tuple[int, int], open_end: int) -> bool:
    """Return whether one canonical tile can connect to the given open end."""

    return int(open_end) in {int(tile[0]), int(tile[1])}


def _new_open_end(tile: Tuple[int, int], open_end: int) -> int:
    """Return the new open-end value after playing `tile` on `open_end`."""

    if not _can_connect(tile, int(open_end)):
        raise ValueError("tile does not connect to open end")
    if int(tile[0]) == int(tile[1]):
        return int(open_end)
    return int(tile[1]) if int(tile[0]) == int(open_end) else int(tile[0])


def _tile_id_for_canonical(
    candidate_instances: Sequence[DominoTileInstance],
    canonical_tile: Tuple[int, int],
) -> str | None:
    """Return the rendered candidate id for one canonical domino tile."""

    target = _canonical_tile(int(canonical_tile[0]), int(canonical_tile[1]))
    for tile in candidate_instances:
        if _canonical_tile(int(tile.left_value), int(tile.right_value)) == target:
            return str(tile.tile_id)
    return None


def _build_scene_instances(
    *,
    rng,
    oriented_chain: Sequence[Tuple[int, int]],
    candidate_tiles: Sequence[Tuple[int, int]],
    annotation_tiles: Sequence[Tuple[int, int]],
    reference_role: str | None,
    highlight_open_end: bool,
    shuffle_candidates: bool = True,
    label_candidates: bool = False,
) -> Tuple[Tuple[DominoTileInstance, ...], Tuple[DominoTileInstance, ...], Tuple[str, ...], str | None]:
    """Build rendered chain/candidate instances and witness ids from canonical tiles."""

    annotation_canonicals = {_canonical_tile(int(tile[0]), int(tile[1])) for tile in annotation_tiles}
    chain_instances: List[DominoTileInstance] = []
    candidate_instances: List[DominoTileInstance] = []
    annotation_tile_ids: List[str] = []
    reference_tile_id: str | None = None

    for index, oriented_tile in enumerate(oriented_chain, start=1):
        tile_id = f"chain_{index:02d}"
        is_reference = bool(index == len(oriented_chain) and reference_role is not None)
        chain_instances.append(
            _build_tile_instance(
                tile_id=str(tile_id),
                oriented_tile=(int(oriented_tile[0]), int(oriented_tile[1])),
                role=str(reference_role) if bool(is_reference) else "chain",
                is_reference=bool(is_reference),
                highlight_right_half=bool(is_reference and highlight_open_end),
            )
        )
        if bool(is_reference):
            reference_tile_id = str(tile_id)

    ordered_candidates = list(candidate_tiles)
    if bool(shuffle_candidates):
        rng.shuffle(ordered_candidates)
    for index, canonical_tile in enumerate(ordered_candidates, start=1):
        tile_id = f"candidate_{index:02d}"
        candidate_instances.append(
            _build_tile_instance(
                tile_id=str(tile_id),
                oriented_tile=_random_orientation(rng, tile=canonical_tile),
                role="candidate",
                option_label=OPTION_LABELS[index - 1] if bool(label_candidates) else None,
            )
        )
        if _canonical_tile(int(canonical_tile[0]), int(canonical_tile[1])) in annotation_canonicals:
            annotation_tile_ids.append(str(tile_id))

    return (
        tuple(chain_instances),
        tuple(candidate_instances),
        tuple(annotation_tile_ids),
        None if reference_tile_id is None else str(reference_tile_id),
    )


def sample_matching_end_scene(rng, *, candidate_count: int, target_answer: int) -> SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose dominoes matching the open end."""

    for _ in range(256):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        connector_value_options = [value for value in PIP_VALUES if int(value) != int(open_end_value)]
        connector_value = int(connector_value_options[int(rng.randrange(len(connector_value_options)))])
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value),),
            )
        except ValueError:
            continue
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        matching_pool = [tile for tile in candidate_pool if int(open_end_value) in {int(tile[0]), int(tile[1])}]
        nonmatching_pool = [tile for tile in candidate_pool if int(open_end_value) not in {int(tile[0]), int(tile[1])}]
        if int(len(matching_pool)) < int(target_answer):
            continue
        if int(len(nonmatching_pool)) < int(candidate_count - target_answer):
            continue
        annotation_tiles = list(rng.sample(matching_pool, int(target_answer)))
        filler_tiles = list(rng.sample(nonmatching_pool, int(candidate_count - target_answer)))
        selected_candidates = annotation_tiles + filler_tiles
        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role="reference_end",
            highlight_open_end=True,
        )
        return SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample matching-end domino scene")


def sample_higher_sum_scene(rng, *, candidate_count: int, target_answer: int) -> SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose dominoes above the reference sum."""

    feasible_end_tiles = [tile for tile in CANONICAL_DOMINOES if 6 <= _tile_sum(tile) <= 8]
    for _ in range(320):
        end_tile = feasible_end_tiles[int(rng.randrange(len(feasible_end_tiles)))]
        oriented_end = _random_orientation(rng, tile=end_tile)
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(oriented_end[0]), int(oriented_end[1])),
            )
        except ValueError:
            continue
        reference_sum = int(oriented_chain[-1][0] + oriented_chain[-1][1])
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        higher_pool = [tile for tile in candidate_pool if _tile_sum(tile) > int(reference_sum)]
        not_higher_pool = [tile for tile in candidate_pool if _tile_sum(tile) <= int(reference_sum)]
        if int(len(higher_pool)) < int(target_answer):
            continue
        if int(len(not_higher_pool)) < int(candidate_count - target_answer):
            continue
        annotation_tiles = list(rng.sample(higher_pool, int(target_answer)))
        filler_tiles = list(rng.sample(not_higher_pool, int(candidate_count - target_answer)))
        selected_candidates = annotation_tiles + filler_tiles
        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role="reference_sum",
            highlight_open_end=False,
        )
        return SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=int(reference_sum),
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample higher-sum domino scene")


def sample_sum_to_target_scene(
    rng,
    *,
    candidate_count: int,
    target_answer: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose dominoes matching a target sum."""

    explicit_target_total = params.get("target_total")
    raw_target_total_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="sum_target_total_support",
        fallback=DEFAULTS.sum_target_total_support,
    )
    for _ in range(320):
        try:
            oriented_chain = _sample_generic_chain(rng, avoid_doubles=False)
        except ValueError:
            continue
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        feasible_totals: List[int] = []
        for total in raw_target_total_support:
            exact_pool = [tile for tile in candidate_pool if _tile_sum(tile) == int(total)]
            non_target_pool = [tile for tile in candidate_pool if _tile_sum(tile) != int(total)]
            if int(target_answer) == 0:
                if int(len(non_target_pool)) >= int(candidate_count):
                    feasible_totals.append(int(total))
            elif int(len(exact_pool)) >= int(target_answer) and int(len(non_target_pool)) >= int(candidate_count - target_answer):
                feasible_totals.append(int(total))
        if explicit_target_total is not None:
            target_total = int(explicit_target_total)
            if int(target_total) not in set(feasible_totals):
                raise ValueError(f"unsupported target_total for sum_to_target_count: {target_total}")
        else:
            if not feasible_totals:
                continue
            target_total = int(feasible_totals[int(rng.randrange(len(feasible_totals)))])

        exact_pool = [tile for tile in candidate_pool if _tile_sum(tile) == int(target_total)]
        non_target_pool = [tile for tile in candidate_pool if _tile_sum(tile) != int(target_total)]
        annotation_tiles = (
            []
            if int(target_answer) == 0
            else list(rng.sample(exact_pool, int(target_answer)))
        )
        filler_tiles = list(rng.sample(non_target_pool, int(candidate_count - target_answer)))
        selected_candidates = list(annotation_tiles) + filler_tiles
        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role=None,
            highlight_open_end=False,
        )
        return SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=None,
            target_total=int(target_total),
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample sum-to-target domino scene")


def sample_double_scene(rng, *, candidate_count: int, target_answer: int) -> SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose doubles."""

    for _ in range(256):
        try:
            oriented_chain = _sample_generic_chain(rng, avoid_doubles=True)
        except ValueError:
            continue
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        double_pool = [tile for tile in candidate_pool if int(tile[0]) == int(tile[1])]
        non_double_pool = [tile for tile in candidate_pool if int(tile[0]) != int(tile[1])]
        if int(len(double_pool)) < int(target_answer):
            continue
        if int(len(non_double_pool)) < int(candidate_count - target_answer):
            continue
        annotation_tiles = list(rng.sample(double_pool, int(target_answer)))
        filler_tiles = list(rng.sample(non_double_pool, int(candidate_count - target_answer)))
        selected_candidates = annotation_tiles + filler_tiles
        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role=None,
            highlight_open_end=False,
        )
        return SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=None,
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample double-count domino scene")


def sample_second_play_candidate_scene(rng, *, candidate_count: int, target_answer: int) -> SampledDominoScene:
    """Sample a scene with one first play and exactly `target_answer` possible second plays."""

    for _ in range(360):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        bridge_options = [value for value in PIP_VALUES if int(value) != int(open_end_value)]
        bridge_value = int(bridge_options[int(rng.randrange(len(bridge_options)))])
        connector_options = [
            value for value in PIP_VALUES
            if int(value) not in {int(open_end_value), int(bridge_value)}
        ]
        if not connector_options:
            continue
        connector_value = int(connector_options[int(rng.randrange(len(connector_options)))])
        first_tile = _canonical_tile(int(open_end_value), int(bridge_value))
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value), int(bridge_value)),
            )
        except ValueError:
            continue
        candidate_pool = set(_candidate_pool_for_chain(oriented_chain))
        if first_tile not in candidate_pool:
            continue
        second_pool = [
            tile for tile in candidate_pool
            if tile != first_tile
            and int(bridge_value) in {int(tile[0]), int(tile[1])}
            and int(open_end_value) not in {int(tile[0]), int(tile[1])}
        ]
        filler_pool = [
            tile for tile in candidate_pool
            if tile != first_tile
            and int(bridge_value) not in {int(tile[0]), int(tile[1])}
            and int(open_end_value) not in {int(tile[0]), int(tile[1])}
        ]
        if int(len(second_pool)) < int(target_answer):
            continue
        if int(len(filler_pool)) < int(candidate_count - target_answer - 1):
            continue
        annotation_tiles = list(rng.sample(second_pool, int(target_answer)))
        filler_tiles = list(rng.sample(filler_pool, int(candidate_count - target_answer - 1)))
        selected_candidates = [first_tile] + annotation_tiles + filler_tiles
        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role="reference_end",
            highlight_open_end=True,
            shuffle_candidates=True,
            label_candidates=False,
        )
        first_step_tile_id = _tile_id_for_canonical(candidate_instances, first_tile)
        return SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            target_total=None,
            first_step_tile_id=first_step_tile_id,
            second_step_tile_id=None,
            bridge_value=int(bridge_value),
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                    "is_unique_first_play": bool(str(tile.tile_id) == str(first_step_tile_id)),
                    "is_second_play_candidate": bool(str(tile.tile_id) in set(annotation_tile_ids)),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample second-play candidate domino scene")


def sample_extendable_first_play_scene(rng, *, candidate_count: int, target_answer: int) -> SampledDominoScene:
    """Sample a scene with exactly `target_answer` first plays that allow a next play."""

    target_count = int(target_answer)
    for _ in range(420):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        bridge_values = [int(value) for value in PIP_VALUES if int(value) != int(open_end_value)]
        if int(target_count) > int(len(bridge_values)):
            continue
        target_bridges = list(rng.sample(bridge_values, int(target_count)))
        remaining_bridges = [value for value in bridge_values if int(value) not in set(target_bridges)]
        max_dead_count = max(0, min(len(remaining_bridges) - 1, int(candidate_count) - (2 * int(target_count))))
        dead_count = 0 if max_dead_count <= 0 else int(rng.randrange(max_dead_count + 1))
        dead_bridges = list(rng.sample(remaining_bridges, int(dead_count))) if int(dead_count) > 0 else []
        connector_options = [
            value for value in PIP_VALUES
            if int(value) not in {int(open_end_value), *[int(v) for v in target_bridges], *[int(v) for v in dead_bridges]}
        ]
        if not connector_options:
            continue
        connector_value = int(connector_options[int(rng.randrange(len(connector_options)))])
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value), *target_bridges, *dead_bridges),
            )
        except ValueError:
            continue
        candidate_pool = set(_candidate_pool_for_chain(oriented_chain))
        annotation_tiles = [_canonical_tile(int(open_end_value), int(bridge)) for bridge in target_bridges]
        support_tiles = [_canonical_tile(int(bridge), int(bridge)) for bridge in target_bridges]
        dead_first_tiles = [_canonical_tile(int(open_end_value), int(bridge)) for bridge in dead_bridges]
        required_tiles = list(annotation_tiles) + list(support_tiles) + list(dead_first_tiles)
        if any(tile not in candidate_pool for tile in required_tiles):
            continue
        required_set = set(required_tiles)
        dead_value_set = {int(value) for value in dead_bridges}
        filler_pool = [
            tile for tile in candidate_pool
            if tile not in required_set
            and int(open_end_value) not in {int(tile[0]), int(tile[1])}
            and not ({int(tile[0]), int(tile[1])} & dead_value_set)
        ]
        filler_count = int(candidate_count) - int(len(required_tiles))
        if int(filler_count) < 0 or int(len(filler_pool)) < int(filler_count):
            continue
        filler_tiles = list(rng.sample(filler_pool, int(filler_count)))
        selected_candidates = required_tiles + filler_tiles

        exact_extendable: List[Tuple[int, int]] = []
        selected_set = [_canonical_tile(int(tile[0]), int(tile[1])) for tile in selected_candidates]
        for tile in selected_set:
            if not _can_connect(tile, int(open_end_value)):
                continue
            next_open = _new_open_end(tile, int(open_end_value))
            has_followup = any(
                other != tile and _can_connect(other, int(next_open))
                for other in selected_set
            )
            if bool(has_followup):
                exact_extendable.append(tile)
        if {_canonical_tile(*tile) for tile in exact_extendable} != {_canonical_tile(*tile) for tile in annotation_tiles}:
            continue

        chain_instances, candidate_instances, annotation_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            annotation_tiles=annotation_tiles,
            reference_role="reference_end",
            highlight_open_end=True,
            shuffle_candidates=True,
            label_candidates=False,
        )
        return SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            annotation_tile_ids=annotation_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                    "is_extendable_first_play": bool(str(tile.tile_id) in set(annotation_tile_ids)),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample extendable first-play domino scene")


def resolve_domino_render_params(params: Mapping[str, Any], *, render_defaults: Mapping[str, Any], instance_seed: int) -> DominoRenderParams:
    """Resolve domino-scene rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.dominoes.font_family",
        params=params,
    )
    return DominoRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(render_defaults, "panel_margin_px", DEFAULTS.panel_margin_px))),
        chain_top_px=int(params.get("chain_top_px", group_default(render_defaults, "chain_top_px", DEFAULTS.chain_top_px))),
        tile_width_px=int(params.get("tile_width_px", group_default(render_defaults, "tile_width_px", DEFAULTS.tile_width_px))),
        tile_height_px=int(params.get("tile_height_px", group_default(render_defaults, "tile_height_px", DEFAULTS.tile_height_px))),
        chain_gap_px=int(params.get("chain_gap_px", group_default(render_defaults, "chain_gap_px", DEFAULTS.chain_gap_px))),
        candidate_gap_px=int(
            params.get("candidate_gap_px", group_default(render_defaults, "candidate_gap_px", DEFAULTS.candidate_gap_px))
        ),
        row_gap_px=int(params.get("row_gap_px", group_default(render_defaults, "row_gap_px", DEFAULTS.row_gap_px))),
        tile_corner_radius_px=int(
            params.get(
                "tile_corner_radius_px",
                group_default(render_defaults, "tile_corner_radius_px", DEFAULTS.tile_corner_radius_px),
            )
        ),
        pip_radius_px=int(params.get("pip_radius_px", group_default(render_defaults, "pip_radius_px", DEFAULTS.pip_radius_px))),
        divider_width_px=int(
            params.get("divider_width_px", group_default(render_defaults, "divider_width_px", DEFAULTS.divider_width_px))
        ),
        reference_tag_font_size_px=int(
            params.get(
                "reference_tag_font_size_px",
                group_default(render_defaults, "reference_tag_font_size_px", DEFAULTS.reference_tag_font_size_px),
            )
        ),
        reference_tag_gap_px=int(
            params.get(
                "reference_tag_gap_px",
                group_default(render_defaults, "reference_tag_gap_px", DEFAULTS.reference_tag_gap_px),
            )
        ),
        section_label_font_size_px=int(
            params.get(
                "section_label_font_size_px",
                group_default(render_defaults, "section_label_font_size_px", DEFAULTS.section_label_font_size_px),
            )
        ),
        section_separator_width_px=int(
            params.get(
                "section_separator_width_px",
                group_default(render_defaults, "section_separator_width_px", DEFAULTS.section_separator_width_px),
            )
        ),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            render_defaults,
            instance_seed=int(instance_seed),
            namespace="games.dominoes.layout",
        ),
    )




__all__ = [
    "resolve_domino_candidate_count_axis",
    "resolve_domino_integer_axis",
    "resolve_domino_render_params",
    "resolve_domino_scene_axes",
    "resolve_domino_target_axis",
    "sample_double_scene",
    "sample_extendable_first_play_scene",
    "sample_higher_sum_scene",
    "sample_matching_end_scene",
    "sample_second_play_candidate_scene",
    "sample_sum_to_target_scene",
]
