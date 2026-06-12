"""Dataset and query construction for mixed-dashboard chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.sampling import normalize_positive_weights, weighted_choice
from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default, resolve_required_int_bounds
from ....shared.deterministic_sampling import resolve_selection_index
from ...shared.label_assets import (
    resolve_chart_category_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from ...shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
from .cross_panel_common import (
    SCENE_NAMESPACE,
    _GEN_DEFAULTS,
    _OPTION_LETTERS,
    _PANEL_KIND_NAMES,
    _SUPPORTED_CONDITION_COMPARISONS,
    _SUPPORTED_PANEL_KINDS,
    _SUPPORTED_RANK_DIRECTIONS,
    _SUPPORTED_REQUESTED_TRUTHS,
    _Category,
    _Dataset,
    _Panel,
    _Query,
    _RenderParams,
    _balanced_support_choice,
    _category_by_id,
    _condition_count_support,
    _condition_phrase,
    _join_labels,
    _option_count_support,
    _panel_by_id,
    _panel_condition_count_support,
    _rank_phrase,
    _rank_positions_by_category_id,
    _rank_support,
    _ranked_category_id,
    _resolve_render_params,
    _top_k_overlap_count_support,
    _top_k_support,
    _weighted_choice_from_defaults,
)


def _statement_candidate(
    *,
    panel_a: _Panel,
    category_a: _Category,
    panel_b: _Panel,
    category_b: _Category,
    comparison: str,
    statement_kind: str,
) -> Dict[str, Any]:
    value_a = int(panel_a.values_by_category_id[str(category_a.category_id)])
    value_b = int(panel_b.values_by_category_id[str(category_b.category_id)])
    if str(comparison) == "greater_than":
        truth = bool(value_a > value_b)
        relation = "greater than"
    elif str(comparison) == "less_than":
        truth = bool(value_a < value_b)
        relation = "less than"
    else:
        raise ValueError(f"unsupported statement comparison: {comparison}")
    if str(statement_kind) == "same_category_cross_panel":
        text = f'"{category_a.label}" in "{panel_a.name}" is {relation} in "{panel_b.name}".'
    elif str(statement_kind) == "two_categories_one_panel":
        text = f'In "{panel_a.name}", "{category_a.label}" is {relation} "{category_b.label}".'
    else:
        raise ValueError(f"unsupported statement kind: {statement_kind}")
    return {
        "text": str(text),
        "truth_value": bool(truth),
        "comparison": str(comparison),
        "statement_kind": str(statement_kind),
        "first_panel_id": str(panel_a.panel_id),
        "first_panel_name": str(panel_a.name),
        "first_category_id": str(category_a.category_id),
        "first_category_label": str(category_a.label),
        "first_value": int(value_a),
        "second_panel_id": str(panel_b.panel_id),
        "second_panel_name": str(panel_b.name),
        "second_category_id": str(category_b.category_id),
        "second_category_label": str(category_b.label),
        "second_value": int(value_b),
    }


def _statement_option_candidates(
    *,
    rng,
    categories: Sequence[_Category],
    panels: Sequence[_Panel],
) -> Tuple[Dict[str, Any], ...]:
    candidates: List[Dict[str, Any]] = []
    seen: set[str] = set()
    comparisons = ("greater_than", "less_than")
    panel_pairs = [(panel_a, panel_b) for panel_a in panels for panel_b in panels if str(panel_a.panel_id) != str(panel_b.panel_id)]
    category_pairs = [(category_a, category_b) for category_a in categories for category_b in categories if str(category_a.category_id) != str(category_b.category_id)]
    rng.shuffle(panel_pairs)
    rng.shuffle(category_pairs)

    for panel_a, panel_b in panel_pairs:
        shuffled_categories = list(categories)
        rng.shuffle(shuffled_categories)
        for category in shuffled_categories:
            for comparison in comparisons:
                candidate = _statement_candidate(
                    panel_a=panel_a,
                    category_a=category,
                    panel_b=panel_b,
                    category_b=category,
                    comparison=str(comparison),
                    statement_kind="same_category_cross_panel",
                )
                if str(candidate["text"]) not in seen:
                    seen.add(str(candidate["text"]))
                    candidates.append(candidate)

    shuffled_panels = list(panels)
    rng.shuffle(shuffled_panels)
    for panel in shuffled_panels:
        for category_a, category_b in category_pairs:
            for comparison in comparisons:
                candidate = _statement_candidate(
                    panel_a=panel,
                    category_a=category_a,
                    panel_b=panel,
                    category_b=category_b,
                    comparison=str(comparison),
                    statement_kind="two_categories_one_panel",
                )
                if str(candidate["text"]) not in seen:
                    seen.add(str(candidate["text"]))
                    candidates.append(candidate)
    rng.shuffle(candidates)
    return tuple(candidates)


def _top_k_category_ids(
    *,
    categories: Sequence[_Category],
    panel: _Panel,
    direction: str,
    top_k: int,
) -> Tuple[str, ...]:
    reverse = str(direction) == "largest"
    ordered = sorted(
        categories,
        key=lambda category: int(panel.values_by_category_id[str(category.category_id)]),
        reverse=bool(reverse),
    )
    if int(top_k) < 1 or int(top_k) > len(ordered):
        raise ValueError("top_k is outside category support")
    return tuple(str(category.category_id) for category in ordered[: int(top_k)])


def _compare_condition(value: int, comparison: str, threshold: int) -> bool:
    if str(comparison) == "greater_than":
        return int(value) > int(threshold)
    if str(comparison) == "less_than":
        return int(value) < int(threshold)
    raise ValueError(f"unsupported comparison: {comparison}")


def _choose_threshold_pair_for_count(
    *,
    rng,
    categories: Sequence[_Category],
    first_panel: _Panel,
    second_panel: _Panel,
    first_comparison: str,
    second_comparison: str,
    target_count: int,
    value_min: int,
    value_max: int,
) -> Tuple[int, int, Tuple[str, ...]]:
    candidates: List[Tuple[int, int, Tuple[str, ...]]] = []
    for first_threshold in range(int(value_min) + 2, int(value_max) - 1):
        for second_threshold in range(int(value_min) + 2, int(value_max) - 1):
            matches = tuple(
                str(category.category_id)
                for category in categories
                if _compare_condition(
                    int(first_panel.values_by_category_id[str(category.category_id)]),
                    str(first_comparison),
                    int(first_threshold),
                )
                and _compare_condition(
                    int(second_panel.values_by_category_id[str(category.category_id)]),
                    str(second_comparison),
                    int(second_threshold),
                )
            )
            if len(matches) == int(target_count):
                candidates.append((int(first_threshold), int(second_threshold), matches))
    if not candidates:
        raise ValueError("no threshold pair realizes the requested condition count")
    return candidates[int(rng.randrange(len(candidates)))]


def _sample_categories(params: Mapping[str, Any], *, instance_seed: int, render_params: _RenderParams) -> Tuple[_Category, ...]:
    category_min, category_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=5,
        fallback_max=10,
        context=SCENE_NAMESPACE,
    )
    if int(category_min) < 4:
        raise ValueError("category_count_min must be at least 4 for dashboard charts")
    category_max = min(int(category_max), len(render_params.category_palette_rgb))
    if int(category_min) > int(category_max):
        raise ValueError("category_count_min exceeds feasible palette/label support")
    explicit_category_count = params.get("category_count")
    if explicit_category_count is not None:
        category_count = int(explicit_category_count)
        if category_count < int(category_min) or category_count > int(category_max):
            raise ValueError("category_count must be within category_count_min..category_count_max")
    else:
        category_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.category_count",
            support=tuple(range(int(category_min), int(category_max) + 1)),
        )
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.categories")
    labels = list(
        resolve_chart_category_labels(
            rng,
            count=int(category_count),
            min_chars=2,
            max_chars=8,
            allow_spaces=False,
        ).labels
    )
    color_pool = list(render_params.category_palette_rgb)
    rng.shuffle(color_pool)
    return tuple(
        _Category(
            category_id=f"cat_{index}",
            label=str(labels[index]),
            color_rgb=tuple(color_pool[index]),
        )
        for index in range(int(category_count))
    )


def _sample_panel_title_labels(
    params: Mapping[str, Any],
    *,
    count: int,
    instance_seed: int,
    namespace: str,
    reserved_labels: Sequence[str] = (),
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    """Sample compact unique labels for dashboard panel titles."""

    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), str(namespace)),
        count=int(count),
        min_chars=2,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                _GEN_DEFAULTS,
                "panel_label_variant_weights",
                {
                    "named_compact": 1.0,
                    "report_topics": 1.0,
                    "technical_topics": 1.0,
                    "condition_labels": 0.75,
                    "temporal_sequence": 0.25,
                },
            ),
        ),
        reserved_labels=reserved_labels,
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"category_labels": tuple(str(label) for label in reserved_labels)},
        context="dashboard panel titles",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": {
            "label_variant": str(resolved.label_variant),
            "label_pool_kind": str(resolved.label_pool_kind),
            "label_source_kind": str(resolved.label_source_kind),
            "label_bucket": str(resolved.label_bucket),
            "label_manifest": str(resolved.label_manifest),
            "label_filter": dict(resolved.label_filter),
            "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
        },
        "panel_label_collision_check": dict(collision_check),
    }


def _sample_panels(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    categories: Sequence[_Category],
) -> Tuple[Tuple[_Panel, ...], Dict[str, Any]]:
    panel_count_min, panel_count_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=4,
        fallback_max=9,
        context=SCENE_NAMESPACE,
    )
    if int(panel_count_min) < 3:
        raise ValueError("panel_count_min must be at least 3 for dashboard cross-panel queries")
    explicit_panel_count = params.get("panel_count")
    if explicit_panel_count is not None:
        panel_count = int(explicit_panel_count)
        if panel_count < int(panel_count_min) or panel_count > int(panel_count_max):
            raise ValueError("panel_count must be within panel_count_min..panel_count_max")
    else:
        panel_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_count",
            support=tuple(range(int(panel_count_min), int(panel_count_max) + 1)),
        )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=12,
        fallback_max=92,
        context=SCENE_NAMESPACE,
    )
    if int(value_max) - int(value_min) + 1 < len(categories):
        raise ValueError("value range is too small to give each panel unique category values")
    explicit_kinds = params.get("panel_kinds")
    if explicit_kinds is not None:
        if not isinstance(explicit_kinds, Sequence) or isinstance(explicit_kinds, (str, bytes)):
            raise ValueError("panel_kinds must be a sequence when provided")
        selected_kinds = [str(kind) for kind in explicit_kinds]
        if explicit_panel_count is None:
            panel_count = len(selected_kinds)
            if panel_count < int(panel_count_min) or panel_count > int(panel_count_max):
                raise ValueError("panel_kinds length must be within panel_count_min..panel_count_max")
        if len(selected_kinds) != int(panel_count):
            raise ValueError("panel_kinds length must match sampled or configured panel_count")
        unsupported = sorted(set(selected_kinds) - set(_SUPPORTED_PANEL_KINDS))
        if unsupported:
            raise ValueError(f"unsupported panel kinds: {unsupported}")
    else:
        raw_weights = params.get(
            "panel_kind_weights",
            group_default(_GEN_DEFAULTS, "panel_kind_weights", {kind: 1.0 for kind in _SUPPORTED_PANEL_KINDS}),
        )
        if not isinstance(raw_weights, Mapping):
            raise ValueError("panel_kind_weights must be a mapping when provided")
        probabilities = normalize_positive_weights(
            {str(kind): float(weight) for kind, weight in raw_weights.items() if str(kind) in set(_SUPPORTED_PANEL_KINDS)},
            default_keys=list(_SUPPORTED_PANEL_KINDS),
        )
        kind_rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.panel_kinds")
        selected_kinds = [
            str(weighted_choice(kind_rng, probabilities, sort_keys=True))
            for _ in range(int(panel_count))
        ]
    panel_title_labels, panel_label_meta = _sample_panel_title_labels(
        params,
        count=int(panel_count),
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.panel_titles",
        reserved_labels=tuple(str(category.label) for category in categories),
    )
    panels: List[_Panel] = []
    for index, kind in enumerate(selected_kinds):
        panel_id = f"panel_{index}"
        name = f"{panel_title_labels[index]} {_PANEL_KIND_NAMES[str(kind)]}"
        rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.panel_values.{panel_id}")
        values = rng.sample(list(range(int(value_min), int(value_max) + 1)), len(categories))
        panels.append(
            _Panel(
                panel_id=str(panel_id),
                kind=str(kind),
                name=str(name),
                values_by_category_id={
                    str(category.category_id): int(value)
                    for category, value in zip(categories, values)
                },
            )
        )
    return tuple(panels), dict(panel_label_meta)


def _choose_rank_params(
    rng,
    *,
    params: Mapping[str, Any],
    category_count: int,
) -> Tuple[str, int]:
    direction = _weighted_choice_from_defaults(
        rng,
        params=params,
        key="rank_direction",
        supported=_SUPPORTED_RANK_DIRECTIONS,
        fallback_weights_key="rank_direction_weights",
    )
    support = tuple(value for value in _rank_support(params) if int(value) <= int(category_count))
    if not support:
        raise ValueError("rank support has no feasible values for category count")
    rank_n = int(support[int(rng.randrange(len(support)))])
    return str(direction), int(rank_n)


def _choose_distinct_rank_params(
    rng,
    *,
    params: Mapping[str, Any],
    category_count: int,
    avoid_phrase: str,
) -> Tuple[str, int]:
    """Choose rank parameters whose visible phrase differs from an existing rank phrase."""

    candidates: List[Tuple[str, int]] = []
    raw_weights = params.get(
        "rank_direction_weights",
        group_default(_GEN_DEFAULTS, "rank_direction_weights", {direction: 1.0 for direction in _SUPPORTED_RANK_DIRECTIONS}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("rank_direction_weights must be a mapping when provided")
    feasible_ranks = tuple(value for value in _rank_support(params) if int(value) <= int(category_count))
    for direction in _SUPPORTED_RANK_DIRECTIONS:
        if float(raw_weights.get(str(direction), 0.0)) <= 0.0:
            continue
        for rank_n in feasible_ranks:
            if _rank_phrase(str(direction), int(rank_n)) != str(avoid_phrase):
                candidates.append((str(direction), int(rank_n)))
    if not candidates:
        raise ValueError("no distinct rank phrase is feasible")
    return candidates[int(rng.randrange(len(candidates)))]


def _build_query(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    prompt_key: str,
    prompt_key_probabilities: Mapping[str, float],
    categories: Sequence[_Category],
    panels: Sequence[_Panel],
) -> _Query:
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.query.{prompt_key}")
    panel_ids = [str(panel.panel_id) for panel in panels]

    if str(prompt_key) == "source_rank_target_value":
        source_id, target_id = rng.sample(panel_ids, 2)
        source_panel = _panel_by_id(panels, source_id)
        target_panel = _panel_by_id(panels, target_id)
        direction, rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        category_id = _ranked_category_id(categories=categories, panel=source_panel, direction=direction, rank_n=rank_n)
        answer = int(target_panel.values_by_category_id[str(category_id)])
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "source_panel_id": str(source_id),
            "source_panel_name": str(source_panel.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "rank_direction": str(direction),
            "rank_n": int(rank_n),
            "rank_phrase": _rank_phrase(str(direction), int(rank_n)),
            "selected_category_id": str(category_id),
            "selected_category_label": str(_category_by_id(categories, category_id).label),
            "source_value": int(source_panel.values_by_category_id[str(category_id)]),
            "target_value": int(answer),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=int(answer),
            answer_type="integer",
            annotation_refs=((str(source_id), str(category_id)), (str(target_id), str(category_id))),
            params=query_params,
        )

    if str(prompt_key) == "source_rank_difference_value":
        source_id, target_id = rng.sample(panel_ids, 2)
        source_panel = _panel_by_id(panels, source_id)
        target_panel = _panel_by_id(panels, target_id)
        direction, rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        category_id = _ranked_category_id(categories=categories, panel=source_panel, direction=direction, rank_n=rank_n)
        source_value = int(source_panel.values_by_category_id[str(category_id)])
        target_value = int(target_panel.values_by_category_id[str(category_id)])
        answer = abs(int(source_value) - int(target_value))
        if int(answer) == 0:
            raise ValueError("source-rank difference must be non-zero")
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "source_panel_id": str(source_id),
            "source_panel_name": str(source_panel.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "rank_direction": str(direction),
            "rank_n": int(rank_n),
            "rank_phrase": _rank_phrase(str(direction), int(rank_n)),
            "selected_category_id": str(category_id),
            "selected_category_label": str(_category_by_id(categories, category_id).label),
            "source_value": int(source_value),
            "target_value": int(target_value),
            "absolute_difference": int(answer),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=int(answer),
            answer_type="integer",
            annotation_refs=((str(source_id), str(category_id)), (str(target_id), str(category_id))),
            params=query_params,
        )

    if str(prompt_key) == "dual_source_target_sum_value":
        first_source_id, second_source_id, target_id = rng.sample(panel_ids, 3)
        first_source = _panel_by_id(panels, first_source_id)
        second_source = _panel_by_id(panels, second_source_id)
        target_panel = _panel_by_id(panels, target_id)
        first_direction, first_rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        second_direction, second_rank_n = _choose_distinct_rank_params(
            rng,
            params=params,
            category_count=len(categories),
            avoid_phrase=_rank_phrase(str(first_direction), int(first_rank_n)),
        )
        first_category_id = _ranked_category_id(
            categories=categories,
            panel=first_source,
            direction=first_direction,
            rank_n=first_rank_n,
        )
        second_category_id = _ranked_category_id(
            categories=categories,
            panel=second_source,
            direction=second_direction,
            rank_n=second_rank_n,
        )
        if str(first_category_id) == str(second_category_id):
            raise ValueError("dual-source sum needs two distinct selected categories")
        first_target_value = int(target_panel.values_by_category_id[str(first_category_id)])
        second_target_value = int(target_panel.values_by_category_id[str(second_category_id)])
        answer = int(first_target_value) + int(second_target_value)
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "first_source_panel_id": str(first_source_id),
            "first_source_panel_name": str(first_source.name),
            "second_source_panel_id": str(second_source_id),
            "second_source_panel_name": str(second_source.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "first_rank_direction": str(first_direction),
            "first_rank_n": int(first_rank_n),
            "first_rank_phrase": _rank_phrase(str(first_direction), int(first_rank_n)),
            "second_rank_direction": str(second_direction),
            "second_rank_n": int(second_rank_n),
            "second_rank_phrase": _rank_phrase(str(second_direction), int(second_rank_n)),
            "first_category_id": str(first_category_id),
            "first_category_label": str(_category_by_id(categories, first_category_id).label),
            "second_category_id": str(second_category_id),
            "second_category_label": str(_category_by_id(categories, second_category_id).label),
            "first_target_value": int(first_target_value),
            "second_target_value": int(second_target_value),
            "sum_value": int(answer),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=int(answer),
            answer_type="integer",
            annotation_refs=(
                (str(first_source_id), str(first_category_id)),
                (str(second_source_id), str(second_category_id)),
                (str(target_id), str(first_category_id)),
                (str(target_id), str(second_category_id)),
            ),
            params=query_params,
        )

    if str(prompt_key) == "dual_condition_count":
        first_panel_id, second_panel_id = rng.sample(panel_ids, 2)
        first_panel = _panel_by_id(panels, first_panel_id)
        second_panel = _panel_by_id(panels, second_panel_id)
        first_comparison = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="first_condition_comparison",
            supported=_SUPPORTED_CONDITION_COMPARISONS,
            fallback_weights_key="condition_comparison_weights",
        )
        second_comparison = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="second_condition_comparison",
            supported=_SUPPORTED_CONDITION_COMPARISONS,
            fallback_weights_key="condition_comparison_weights",
        )
        support = _condition_count_support(params, len(categories))
        support_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.condition_count",
        )
        target_count = int(support[abs(int(support_index)) % len(support)])
        value_min = int(params.get("value_min", group_default(_GEN_DEFAULTS, "value_min", 12)))
        value_max = int(params.get("value_max", group_default(_GEN_DEFAULTS, "value_max", 92)))
        first_threshold, second_threshold, matches = _choose_threshold_pair_for_count(
            rng=rng,
            categories=categories,
            first_panel=first_panel,
            second_panel=second_panel,
            first_comparison=str(first_comparison),
            second_comparison=str(second_comparison),
            target_count=int(target_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        annotation_refs: List[Tuple[str, str]] = []
        category_order = {str(category.category_id): index for index, category in enumerate(categories)}
        for category_id in sorted(matches, key=lambda item: category_order[str(item)]):
            annotation_refs.append((str(first_panel_id), str(category_id)))
            annotation_refs.append((str(second_panel_id), str(category_id)))
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "first_condition_panel_id": str(first_panel_id),
            "first_condition_panel_name": str(first_panel.name),
            "second_condition_panel_id": str(second_panel_id),
            "second_condition_panel_name": str(second_panel.name),
            "first_condition_comparison": str(first_comparison),
            "second_condition_comparison": str(second_comparison),
            "first_threshold": int(first_threshold),
            "second_threshold": int(second_threshold),
            "first_condition_phrase": _condition_phrase(str(first_comparison), int(first_threshold)),
            "second_condition_phrase": _condition_phrase(str(second_comparison), int(second_threshold)),
            "matching_category_ids": list(matches),
            "matching_category_labels": [str(_category_by_id(categories, category_id).label) for category_id in matches],
            "target_count_support": list(support),
            "count_value": int(len(matches)),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=int(len(matches)),
            answer_type="integer",
            annotation_refs=tuple(annotation_refs),
            params=query_params,
        )

    if str(prompt_key) == "panel_gap_extremum_category_label":
        first_panel_id, second_panel_id = rng.sample(panel_ids, 2)
        first_panel = _panel_by_id(panels, first_panel_id)
        second_panel = _panel_by_id(panels, second_panel_id)
        direction = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="gap_extremum_direction",
            supported=_SUPPORTED_RANK_DIRECTIONS,
            fallback_weights_key="gap_extremum_weights",
        )
        if should_use_unanswerable_branch(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_gap_extremum_category_label",
            enabled=bool(params.get("_enable_unanswerable", False)),
        ):
            visible_panel_names = [str(panel.name) for panel in panels]
            missing_panel_base_labels, _missing_panel_label_meta = _sample_panel_title_labels(
                params,
                count=max(16, len(visible_panel_names) + 8),
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.missing_panel_candidates",
                reserved_labels=tuple(visible_panel_names),
            )
            missing_panel_candidates = tuple(
                f"{label} Panel"
                for label in missing_panel_base_labels
            )
            missing_panel_name = choose_missing_label(
                visible_labels=visible_panel_names,
                candidate_labels=missing_panel_candidates,
                fallback_prefix="Panel ",
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.missing_panel",
            )
            missing_first = bool(int(rng.randrange(2)) == 0)
            query_params = {
                "prompt_key": str(prompt_key),
                "scene_variant": "mixed_dashboard",
                "prompt_key_probabilities": dict(prompt_key_probabilities),
                "first_gap_panel_id": "" if missing_first else str(first_panel_id),
                "first_gap_panel_name": str(missing_panel_name if missing_first else first_panel.name),
                "second_gap_panel_id": "" if not missing_first else str(second_panel_id),
                "second_gap_panel_name": str(missing_panel_name if not missing_first else second_panel.name),
                "gap_extremum_direction": str(direction),
                "gap_extremum_phrase": "largest" if str(direction) == "largest" else "smallest",
                "answer_category_id": "",
                "answer_category_label": UNANSWERABLE_ANSWER,
                "answerability": "unanswerable",
                "absence_proof": absence_proof(
                    requested_item=f"panel {missing_panel_name}",
                    visible_candidates=visible_panel_names,
                    checked_scope="dashboard panel titles",
                    absence_reason="one named comparison panel is not shown in the dashboard",
                ),
            }
            return _Query(
                prompt_key=str(prompt_key),
                answer=UNANSWERABLE_ANSWER,
                answer_type="string",
                annotation_refs=(),
                params=query_params,
            )
        gaps_by_category = {
            str(category.category_id): abs(
                int(first_panel.values_by_category_id[str(category.category_id)])
                - int(second_panel.values_by_category_id[str(category.category_id)])
            )
            for category in categories
        }
        if len(set(int(value) for value in gaps_by_category.values())) != len(gaps_by_category):
            raise ValueError("panel gap extremum must be unique across categories")
        reverse = str(direction) == "largest"
        answer_category = sorted(
            categories,
            key=lambda category: int(gaps_by_category[str(category.category_id)]),
            reverse=bool(reverse),
        )[0]
        first_value = int(first_panel.values_by_category_id[str(answer_category.category_id)])
        second_value = int(second_panel.values_by_category_id[str(answer_category.category_id)])
        answer_gap = int(gaps_by_category[str(answer_category.category_id)])
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "first_gap_panel_id": str(first_panel_id),
            "first_gap_panel_name": str(first_panel.name),
            "second_gap_panel_id": str(second_panel_id),
            "second_gap_panel_name": str(second_panel.name),
            "gap_extremum_direction": str(direction),
            "gap_extremum_phrase": "largest" if str(direction) == "largest" else "smallest",
            "answer_category_id": str(answer_category.category_id),
            "answer_category_label": str(answer_category.label),
            "first_value": int(first_value),
            "second_value": int(second_value),
            "answer_gap": int(answer_gap),
            "gaps_by_category_id": dict(gaps_by_category),
            "answerability": "answerable",
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=str(answer_category.label),
            answer_type="string",
            annotation_refs=((str(first_panel_id), str(answer_category.category_id)), (str(second_panel_id), str(answer_category.category_id))),
            params=query_params,
        )

    if str(prompt_key) == "shared_label_rank_gap_extremum":
        first_panel_id, second_panel_id = rng.sample(panel_ids, 2)
        first_panel = _panel_by_id(panels, first_panel_id)
        second_panel = _panel_by_id(panels, second_panel_id)
        rank_direction = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="rank_direction",
            supported=_SUPPORTED_RANK_DIRECTIONS,
            fallback_weights_key="rank_direction_weights",
        )
        gap_direction = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="gap_extremum_direction",
            supported=_SUPPORTED_RANK_DIRECTIONS,
            fallback_weights_key="gap_extremum_weights",
        )
        first_ranks = _rank_positions_by_category_id(
            categories=categories,
            panel=first_panel,
            direction=str(rank_direction),
        )
        second_ranks = _rank_positions_by_category_id(
            categories=categories,
            panel=second_panel,
            direction=str(rank_direction),
        )
        gaps_by_category = {
            str(category.category_id): abs(
                int(first_ranks[str(category.category_id)])
                - int(second_ranks[str(category.category_id)])
            )
            for category in categories
        }
        target_gap = (
            max(int(value) for value in gaps_by_category.values())
            if str(gap_direction) == "largest"
            else min(int(value) for value in gaps_by_category.values())
        )
        answer_category_ids = [
            str(category_id)
            for category_id, gap in gaps_by_category.items()
            if int(gap) == int(target_gap)
        ]
        if len(answer_category_ids) != 1:
            raise ValueError("shared-label rank-gap extremum must have a unique answer")
        answer_category = _category_by_id(categories, str(answer_category_ids[0]))
        first_rank_position = int(first_ranks[str(answer_category.category_id)])
        second_rank_position = int(second_ranks[str(answer_category.category_id)])
        rank_direction_phrase = "highest-to-lowest" if str(rank_direction) == "largest" else "lowest-to-highest"
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "first_rank_gap_panel_id": str(first_panel_id),
            "first_rank_gap_panel_name": str(first_panel.name),
            "second_rank_gap_panel_id": str(second_panel_id),
            "second_rank_gap_panel_name": str(second_panel.name),
            "rank_direction": str(rank_direction),
            "rank_direction_phrase": str(rank_direction_phrase),
            "gap_extremum_direction": str(gap_direction),
            "gap_extremum_phrase": "largest" if str(gap_direction) == "largest" else "smallest",
            "answer_category_id": str(answer_category.category_id),
            "answer_category_label": str(answer_category.label),
            "first_rank_position": int(first_rank_position),
            "second_rank_position": int(second_rank_position),
            "answer_rank_gap": int(target_gap),
            "first_rank_positions_by_category_id": dict(first_ranks),
            "second_rank_positions_by_category_id": dict(second_ranks),
            "rank_gaps_by_category_id": dict(gaps_by_category),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=str(answer_category.label),
            answer_type="string",
            annotation_refs=((str(first_panel_id), str(answer_category.category_id)), (str(second_panel_id), str(answer_category.category_id))),
            params=query_params,
        )

    if str(prompt_key) == "statement_option_selection_label":
        option_counts = _option_count_support(params)
        explicit_answer_letter = params.get("answer_letter")
        if explicit_answer_letter is not None:
            answer_letter = str(explicit_answer_letter).upper()
            if answer_letter not in _OPTION_LETTERS:
                raise ValueError("answer_letter must be A..F")
        else:
            feasible_letters = _OPTION_LETTERS[: max(option_counts)]
            answer_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.statement_option.answer_letter",
            )
            answer_letter = str(feasible_letters[abs(int(answer_index)) % len(feasible_letters)])
        feasible_option_counts = tuple(
            int(count)
            for count in option_counts
            if _OPTION_LETTERS.index(str(answer_letter)) < int(count)
        )
        if not feasible_option_counts:
            raise ValueError("answer_letter is infeasible for configured option_count support")
        option_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.statement_option.option_count.{answer_letter}",
            support=feasible_option_counts,
        )
        requested_truth = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="requested_truth",
            supported=_SUPPORTED_REQUESTED_TRUTHS,
            fallback_weights_key="statement_requested_truth_weights",
        )
        target_truth = str(requested_truth) == "true"
        candidates = _statement_option_candidates(rng=rng, categories=categories, panels=panels)
        selected_pool = [candidate for candidate in candidates if bool(candidate["truth_value"]) is bool(target_truth)]
        distractor_pool = [candidate for candidate in candidates if bool(candidate["truth_value"]) is not bool(target_truth)]
        if not selected_pool or len(distractor_pool) < int(option_count) - 1:
            raise ValueError("not enough dashboard statement candidates for requested option set")
        selected = dict(selected_pool[int(rng.randrange(len(selected_pool)))])
        selected_text = str(selected["text"])
        distractors: List[Dict[str, Any]] = []
        used_texts = {selected_text}
        for candidate in distractor_pool:
            if str(candidate["text"]) in used_texts:
                continue
            distractors.append(dict(candidate))
            used_texts.add(str(candidate["text"]))
            if len(distractors) >= int(option_count) - 1:
                break
        if len(distractors) != int(option_count) - 1:
            raise ValueError("failed to construct unique statement distractors")
        option_letters = _OPTION_LETTERS[: int(option_count)]
        answer_index = option_letters.index(str(answer_letter))
        option_records: List[Dict[str, Any]] = []
        distractor_index = 0
        for index, option_label in enumerate(option_letters):
            record = dict(selected) if int(index) == int(answer_index) else dict(distractors[distractor_index])
            if int(index) != int(answer_index):
                distractor_index += 1
            record["option_label"] = str(option_label)
            record["option_id"] = f"option_{option_label}"
            option_records.append(record)
        selected_record = option_records[int(answer_index)]
        matching_labels = [
            str(option["option_label"])
            for option in option_records
            if bool(option["truth_value"]) is bool(target_truth)
        ]
        if matching_labels != [str(answer_letter)]:
            raise ValueError("statement option set does not have exactly one requested truth match")
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "requested_truth": str(requested_truth),
            "requested_truth_phrase": "true" if bool(target_truth) else "false",
            "option_count": int(option_count),
            "option_labels": list(option_letters),
            "answer_option_label": str(answer_letter),
            "statement_options": [dict(option) for option in option_records],
            "selected_statement": dict(selected_record),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=str(answer_letter),
            answer_type="option_letter",
            annotation_refs=(
                (str(selected_record["first_panel_id"]), str(selected_record["first_category_id"])),
                (str(selected_record["second_panel_id"]), str(selected_record["second_category_id"])),
            ),
            params=query_params,
        )

    if str(prompt_key) == "top_k_overlap_count":
        direction = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="top_k_rank_direction",
            supported=_SUPPORTED_RANK_DIRECTIONS,
            fallback_weights_key="rank_direction_weights",
        )
        top_k_values = _top_k_support(params, len(categories))
        raw_support = params.get("top_k_overlap_count_support", group_default(_GEN_DEFAULTS, "top_k_overlap_count_support", [1, 2, 3, 4, 5]))
        if not isinstance(raw_support, Sequence) or isinstance(raw_support, (str, bytes)):
            raise ValueError("top_k_overlap_count_support must be a sequence")
        feasible_targets = sorted(
            {
                int(target)
                for target in raw_support
                for candidate_top_k in top_k_values
                if max(0, int(candidate_top_k) * 2 - len(categories)) <= int(target) <= int(candidate_top_k)
            }
        )
        if not feasible_targets:
            raise ValueError("top_k_overlap_count_support has no feasible targets")
        target_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.top_k_overlap_count.answer",
            support=feasible_targets,
        )
        feasible_top_k_values = tuple(
            int(candidate_top_k)
            for candidate_top_k in top_k_values
            if max(0, int(candidate_top_k) * 2 - len(categories)) <= int(target_count) <= int(candidate_top_k)
        )
        top_k = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.top_k_overlap_count.top_k",
            support=feasible_top_k_values,
        )
        support = _top_k_overlap_count_support(params, category_count=len(categories), top_k=int(top_k))
        first_panel_id, second_panel_id = rng.sample(panel_ids, 2)
        first_panel = _panel_by_id(panels, first_panel_id)
        second_panel = _panel_by_id(panels, second_panel_id)
        first_top = _top_k_category_ids(
            categories=categories,
            panel=first_panel,
            direction=str(direction),
            top_k=int(top_k),
        )
        outside_first_top = [str(category.category_id) for category in categories if str(category.category_id) not in set(first_top)]
        if int(top_k) - int(target_count) > len(outside_first_top):
            raise ValueError("target overlap is infeasible for sampled category count/top_k")
        overlap = tuple(rng.sample(list(first_top), int(target_count))) if int(target_count) > 0 else ()
        extra = tuple(rng.sample(outside_first_top, int(top_k) - int(target_count))) if int(top_k) > int(target_count) else ()
        desired_second_top = tuple(overlap) + tuple(extra)
        available_values = sorted(int(value) for value in second_panel.values_by_category_id.values())
        if str(direction) == "largest":
            target_values = list(reversed(available_values[-int(top_k) :]))
            other_values = list(reversed(available_values[: len(available_values) - int(top_k)]))
        else:
            target_values = list(available_values[: int(top_k)])
            other_values = list(available_values[int(top_k) :])
        target_ids = list(desired_second_top)
        other_ids = [str(category.category_id) for category in categories if str(category.category_id) not in set(target_ids)]
        rng.shuffle(target_ids)
        rng.shuffle(other_ids)
        for category_id, value in zip(target_ids, target_values):
            second_panel.values_by_category_id[str(category_id)] = int(value)
        for category_id, value in zip(other_ids, other_values):
            second_panel.values_by_category_id[str(category_id)] = int(value)
        second_top = _top_k_category_ids(
            categories=categories,
            panel=second_panel,
            direction=str(direction),
            top_k=int(top_k),
        )
        realized_overlap = tuple(category_id for category_id in first_top if category_id in set(second_top))
        if len(realized_overlap) != int(target_count):
            raise ValueError("constructed top-k overlap did not realize requested count")
        category_order = {str(category.category_id): index for index, category in enumerate(categories)}
        overlap_sorted = tuple(sorted(realized_overlap, key=lambda category_id: category_order[str(category_id)]))
        annotation_refs = tuple(
            (panel_id, category_id)
            for category_id in overlap_sorted
            for panel_id in (str(first_panel_id), str(second_panel_id))
        )
        rank_word = "highest-valued" if str(direction) == "largest" else "lowest-valued"
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "first_topk_panel_id": str(first_panel_id),
            "first_topk_panel_name": str(first_panel.name),
            "second_topk_panel_id": str(second_panel_id),
            "second_topk_panel_name": str(second_panel.name),
            "top_k_rank_direction": str(direction),
            "top_k": int(top_k),
            "top_k_phrase": f"{int(top_k)} {rank_word}",
            "first_top_category_ids": list(first_top),
            "first_top_category_labels": [str(_category_by_id(categories, category_id).label) for category_id in first_top],
            "second_top_category_ids": list(second_top),
            "second_top_category_labels": [str(_category_by_id(categories, category_id).label) for category_id in second_top],
            "overlap_category_ids": list(overlap_sorted),
            "overlap_category_labels": [str(_category_by_id(categories, category_id).label) for category_id in overlap_sorted],
            "target_count_support": list(support),
            "count_value": int(len(overlap_sorted)),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=int(len(overlap_sorted)),
            answer_type="integer",
            annotation_refs=tuple(annotation_refs),
            params=query_params,
        )

    if str(prompt_key) == "category_panel_condition_count":
        comparison = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="panel_condition_comparison",
            supported=_SUPPORTED_CONDITION_COMPARISONS,
            fallback_weights_key="condition_comparison_weights",
        )
        support = _panel_condition_count_support(params, len(panels))
        target_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.category_panel_condition_count.answer",
            support=support,
        )
        value_min = int(params.get("value_min", group_default(_GEN_DEFAULTS, "value_min", 12)))
        value_max = int(params.get("value_max", group_default(_GEN_DEFAULTS, "value_max", 92)))
        candidates: List[Tuple[str, int, Tuple[str, ...]]] = []
        for category in categories:
            category_id = str(category.category_id)
            for threshold in range(int(value_min) + 2, int(value_max) - 1):
                matches = tuple(
                    str(panel.panel_id)
                    for panel in panels
                    if _compare_condition(
                        int(panel.values_by_category_id[str(category_id)]),
                        str(comparison),
                        int(threshold),
                    )
                )
                if len(matches) == int(target_count):
                    candidates.append((str(category_id), int(threshold), matches))
        if not candidates:
            raise ValueError("no dashboard category/threshold realizes requested panel-condition count")
        category_id, threshold, matches = candidates[int(rng.randrange(len(candidates)))]
        category = _category_by_id(categories, category_id)
        panel_order = {str(panel.panel_id): index for index, panel in enumerate(panels)}
        matching_panel_ids = tuple(sorted(matches, key=lambda panel_id: panel_order[str(panel_id)]))
        annotation_refs = tuple((str(panel_id), str(category_id)) for panel_id in matching_panel_ids)
        query_params = {
            "prompt_key": str(prompt_key),
            "scene_variant": "mixed_dashboard",
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            "condition_category_id": str(category_id),
            "condition_category_label": str(category.label),
            "panel_condition_comparison": str(comparison),
            "panel_threshold": int(threshold),
            "panel_condition_phrase": _condition_phrase(str(comparison), int(threshold)),
            "matching_panel_ids": list(matching_panel_ids),
            "matching_panel_names": [str(_panel_by_id(panels, panel_id).name) for panel_id in matching_panel_ids],
            "target_count_support": list(support),
            "count_value": int(len(matching_panel_ids)),
        }
        return _Query(
            prompt_key=str(prompt_key),
            answer=int(len(matching_panel_ids)),
            answer_type="integer",
            annotation_refs=tuple(annotation_refs),
            params=query_params,
        )

    raise ValueError(f"unsupported prompt_key: {prompt_key}")


def _build_dataset(params: Mapping[str, Any], *, instance_seed: int, prompt_key: str) -> _Dataset:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    categories = _sample_categories(params, instance_seed=int(instance_seed), render_params=render_params)
    panels, panel_label_meta = _sample_panels(params, instance_seed=int(instance_seed), categories=categories)
    query = _build_query(
        params,
        instance_seed=int(instance_seed),
        prompt_key=str(prompt_key),
        prompt_key_probabilities={},
        categories=categories,
        panels=panels,
    )
    common_query_params = {
        "panel_count": int(len(panels)),
        "category_count": int(len(categories)),
        "panel_name_list": _join_labels([str(panel.name) for panel in panels]),
        "panel_kind_list": _join_labels([str(panel.kind) for panel in panels]),
        **dict(panel_label_meta),
    }
    query = _Query(
        prompt_key=str(query.prompt_key),
        answer=query.answer,
        answer_type=str(query.answer_type),
        annotation_refs=tuple(query.annotation_refs),
        params={**common_query_params, **dict(query.params)},
    )
    return _Dataset(
        scene_variant="mixed_dashboard",
        categories=tuple(categories),
        panels=tuple(panels),
        query=query,
    )

def build_source_rank_target_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="source_rank_target_value")


def build_source_rank_difference_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="source_rank_difference_value")


def build_dual_source_target_sum_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="dual_source_target_sum_value")


def build_dual_condition_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="dual_condition_count")


def build_panel_gap_extremum_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="panel_gap_extremum_category_label")


def build_shared_label_rank_gap_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="shared_label_rank_gap_extremum")


def build_statement_option_selection_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="statement_option_selection_label")


def build_top_k_overlap_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="top_k_overlap_count")


def build_category_panel_condition_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    return _build_dataset(params, instance_seed=int(instance_seed), prompt_key="category_panel_condition_count")


__all__ = [
    "build_category_panel_condition_dataset",
    "build_dual_condition_count_dataset",
    "build_dual_source_target_sum_dataset",
    "build_panel_gap_extremum_dataset",
    "build_shared_label_rank_gap_dataset",
    "build_source_rank_difference_dataset",
    "build_source_rank_target_dataset",
    "build_statement_option_selection_dataset",
    "build_top_k_overlap_dataset",
]
