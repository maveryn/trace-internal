"""Source-image helpers for RPG dungeon reconstruction tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import hash64
from trace.tasks.illustrations.shared.rpg_tile_profiles import resolve_rpg_tile_profile
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map

from .rendering import (
    DEFAULT_TILE_PX,
    MAX_MONSTER_CHAMBER_COUNT,
    MAX_TOTAL_CHEST_COUNT,
    MIN_TOTAL_CHEST_COUNT,
    RENDERER_ID,
    SCENE_ID,
    render_rpg_dungeon_profile_scene,
)
from .state import RpgDungeonScene


@dataclass(frozen=True)
class RpgDungeonSourceSceneSpec:
    """Dense RPG dungeon source scene shared by visual reconstruction tasks."""

    source_chest_count: int
    source_reachable_chest_count: int
    source_monster_count: int
    source_size: Tuple[int, int]
    source_profile_trace: Dict[str, Any]
    source_chest_count_probabilities: Dict[str, float]
    source_reachable_chest_count_probabilities: Dict[str, float]
    source_monster_count_probabilities: Dict[str, float]


def sample_support_index(
    *,
    seed_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support: Sequence[int],
    explicit_key: str,
) -> Tuple[int, Dict[str, float]]:
    """Select one integer value from finite support."""

    values = tuple(int(value) for value in support)
    if not values:
        raise ValueError(f"{explicit_key} has empty support")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if value not in set(values):
            raise ValueError(f"{explicit_key} must be one of {values}")
        return int(value), {str(value): 1.0}
    if params.get("_sample_cursor") is not None:
        value = values[abs(int(params["_sample_cursor"])) % len(values)]
    else:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(seed_namespace),
        )
        value = values[int(index) % len(values)]
    return int(value), dict(uniform_probability_map(values))


def _range_support(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    support_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, ...]:
    raw_support = params.get(str(support_key), group_default(defaults, str(support_key), None))
    if raw_support is not None:
        if isinstance(raw_support, int):
            values = (int(raw_support),)
        else:
            values = tuple(int(value) for value in raw_support)
        support = tuple(dict.fromkeys(value for value in values if int(fallback_min) <= int(value) <= int(fallback_max)))
        if not support:
            raise ValueError(f"{support_key} must include at least one value in [{fallback_min}, {fallback_max}]")
        return support
    low = int(params.get(str(min_key), group_default(defaults, str(min_key), int(fallback_min))))
    high = int(params.get(str(max_key), group_default(defaults, str(max_key), int(fallback_max))))
    low = max(int(fallback_min), low)
    high = min(int(fallback_max), high)
    if low > high:
        raise ValueError(f"{min_key}/{max_key} leaves no feasible source chest count")
    return tuple(range(int(low), int(high) + 1))


def _bounded_count_support(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback: Sequence[int],
    max_value: int,
) -> Tuple[int, ...]:
    raw_support = params.get(str(support_key), group_default(defaults, str(support_key), tuple(fallback)))
    if isinstance(raw_support, int):
        values = (int(raw_support),)
    else:
        values = tuple(int(value) for value in raw_support)
    support = tuple(dict.fromkeys(value for value in values if 0 <= int(value) <= int(max_value)))
    explicit = params.get(str(explicit_key))
    if explicit is not None and int(explicit) not in set(support):
        raise ValueError(f"{explicit_key} must be one of {support}")
    if not support:
        raise ValueError(f"{support_key} must include at least one feasible value")
    return support


def sample_rpg_dungeon_source_scene_spec(
    *,
    seed_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    source_chest_count_min: int,
    source_chest_count_max: int,
    grid_rows: int | None = None,
    grid_cols: int | None = None,
) -> RpgDungeonSourceSceneSpec:
    """Resolve source render dimensions and scene counts for reconstruction tasks."""

    chest_support = _range_support(
        params=params,
        defaults=generation_defaults,
        min_key="source_chest_count_min",
        max_key="source_chest_count_max",
        support_key="source_chest_count_support",
        fallback_min=int(source_chest_count_min),
        fallback_max=int(source_chest_count_max),
    )
    source_chest_count, chest_probabilities = sample_support_index(
        seed_namespace=f"{seed_namespace}:source_chest_count",
        instance_seed=int(instance_seed),
        params=params,
        support=chest_support,
        explicit_key="source_chest_count",
    )
    reachable_support = _bounded_count_support(
        params=params,
        defaults=generation_defaults,
        support_key="source_reachable_chest_count_support",
        explicit_key="source_reachable_chest_count",
        fallback=tuple(range(1, int(source_chest_count))),
        max_value=int(source_chest_count) - 1,
    )
    reachable_count, reachable_probabilities = sample_support_index(
        seed_namespace=f"{seed_namespace}:source_reachable_chest_count",
        instance_seed=hash64(int(instance_seed), int(source_chest_count)),
        params=params,
        support=reachable_support,
        explicit_key="source_reachable_chest_count",
    )
    monster_support = _bounded_count_support(
        params=params,
        defaults=generation_defaults,
        support_key="source_monster_count_support",
        explicit_key="source_monster_count",
        fallback=tuple(range(1, min(MAX_MONSTER_CHAMBER_COUNT, int(source_chest_count)) + 1)),
        max_value=min(MAX_MONSTER_CHAMBER_COUNT, int(source_chest_count)),
    )
    monster_count, monster_probabilities = sample_support_index(
        seed_namespace=f"{seed_namespace}:source_monster_count",
        instance_seed=hash64(int(instance_seed), int(source_chest_count), int(reachable_count)),
        params=params,
        support=monster_support,
        explicit_key="source_monster_count",
    )
    profile = resolve_rpg_tile_profile(
        params=params,
        defaults=generation_defaults,
        tile_px_key="rpg_dungeon_tile_px",
        fallback_tile_px=DEFAULT_TILE_PX,
        instance_seed=int(instance_seed),
        namespace=f"{seed_namespace}:source_profile",
        width_key="source_width",
        height_key="source_height",
    )
    width = int(profile.width)
    height = int(profile.height)
    trace = dict(profile.trace())
    if grid_rows is not None and grid_cols is not None:
        if width % int(grid_cols) != 0 or height % int(grid_rows) != 0:
            raise ValueError("RPG dungeon source profile must align with the requested reconstruction grid")
        trace["grid_alignment"] = {"rows": int(grid_rows), "cols": int(grid_cols)}
    return RpgDungeonSourceSceneSpec(
        source_chest_count=int(source_chest_count),
        source_reachable_chest_count=int(reachable_count),
        source_monster_count=int(monster_count),
        source_size=(int(width), int(height)),
        source_profile_trace=trace,
        source_chest_count_probabilities=dict(chest_probabilities),
        source_reachable_chest_count_probabilities=dict(reachable_probabilities),
        source_monster_count_probabilities=dict(monster_probabilities),
    )


def render_rpg_dungeon_source_scene(
    *,
    seed_namespace: str,
    instance_seed: int,
    attempt_index: int,
    source: RpgDungeonSourceSceneSpec,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> RpgDungeonScene:
    """Render one dense source RPG dungeon panel."""

    tile_px = int(
        params.get(
            "source_tile_px",
            params.get("tile_px", group_default(render_defaults, "rpg_dungeon_tile_px", DEFAULT_TILE_PX)),
        )
    )
    render_params = {
        "canvas_width": int(source.source_size[0]),
        "canvas_height": int(source.source_size[1]),
        "tile_px": int(tile_px),
        "grid_cols": int(source.source_profile_trace.get("rpg_tile_profile", {}).get("grid_cols", 0)),
        "grid_rows": int(source.source_profile_trace.get("rpg_tile_profile", {}).get("grid_rows", 0)),
        **dict(source.source_profile_trace),
    }
    return render_rpg_dungeon_profile_scene(
        hash64(int(instance_seed), f"{seed_namespace}:source_scene", int(attempt_index)),
        render_params=render_params,
        tile_px=tile_px,
        reachable_chest_count=int(source.source_reachable_chest_count),
        total_chest_count=int(source.source_chest_count),
        monster_chamber_count=int(source.source_monster_count),
    )


def rpg_dungeon_source_style_trace(scene: RpgDungeonScene) -> Dict[str, Any]:
    """Return render style metadata for a source dungeon scene."""

    return {
        "renderer_id": str(scene.trace.get("renderer_id", RENDERER_ID)),
        "scene_id": SCENE_ID,
        "theme_id": str(scene.trace.get("theme_id", "")),
        "tile_px": int(scene.trace.get("tile_px", 0)),
        "grid_cols": int(scene.trace.get("grid_cols", 0)),
        "grid_rows": int(scene.trace.get("grid_rows", 0)),
        "layout_orientation": str(scene.trace.get("layout_orientation", "")),
        "total_chest_count": int(scene.trace.get("total_chest_count", 0)),
        "source_reachable_chests": len(scene.reachable_chest_ids),
        "monster_count": int(scene.trace.get("monster_count", 0)),
    }


__all__ = [
    "RpgDungeonSourceSceneSpec",
    "render_rpg_dungeon_source_scene",
    "rpg_dungeon_source_style_trace",
    "sample_rpg_dungeon_source_scene_spec",
    "sample_support_index",
]
