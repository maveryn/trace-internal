"""Count named-color cells inside a row, column, or edge scope."""

from __future__ import annotations

from dataclasses import dataclass

from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
    resolve_required_int_bounds,
)
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import CellBoardObjectivePlan, run_cell_board_lifecycle
from .shared.sampling import (
    all_coords,
    sample_dimensions,
    sample_palette,
    sample_palette_size,
)
from .shared.state import CellBoardCase, SCENE_ID
from .shared.topology import sort_coords

TASK_ID = "task_puzzles__cell_board__scoped_attribute_count"
ROW_QUERY = "row_color_cell_count"
COLUMN_QUERY = "column_color_cell_count"
EDGE_QUERY = "edge_color_cell_count"
SUPPORTED_QUERY_IDS = (ROW_QUERY, COLUMN_QUERY, EDGE_QUERY)

_GEN_DEFAULTS, _RENDER_DEFAULTS, _ = load_scene_generation_rendering_prompt_defaults(
    "puzzles", SCENE_ID, task_id=TASK_ID
)


@dataclass(frozen=True)
class _ScopeSpec:
    """Task-local semantic branch for the scoped count objective."""

    query_id: str
    scope_kind: str


_BRANCHES = {
    ROW_QUERY: _ScopeSpec(query_id=ROW_QUERY, scope_kind="row"),
    COLUMN_QUERY: _ScopeSpec(query_id=COLUMN_QUERY, scope_kind="column"),
    EDGE_QUERY: _ScopeSpec(query_id=EDGE_QUERY, scope_kind="edge"),
}


def _scope_coords(*, rows: int, cols: int, scope_kind: str, rng) -> tuple[list, dict]:
    if scope_kind == "row":
        row = int(rng.randrange(int(rows)))
        return [(row, col) for col in range(int(cols))], {"query_row": row + 1}
    if scope_kind == "column":
        col = int(rng.randrange(int(cols)))
        return [(row, col) for row in range(int(rows))], {"query_col": col + 1}
    coords = [
        (row, col)
        for row in range(int(rows))
        for col in range(int(cols))
        if row in {0, int(rows) - 1} or col in {0, int(cols) - 1}
    ]
    return coords, {}


def _sample_scoped_answer(*, rng, params, scope_size: int) -> tuple[int, list[int]]:
    lo, hi = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=0,
        fallback_max=10,
        context="scoped cell-board count answer",
    )
    hi = min(int(hi), int(scope_size))
    if int(lo) > int(hi):
        raise ValueError("scoped answer support exceeds scope")
    support = list(range(int(lo), int(hi) + 1))
    return int(rng.choice(support)), [int(value) for value in support]


def _build_scoped_case(
    *,
    instance_seed: int,
    params,
    branch: _ScopeSpec,
) -> CellBoardCase:
    """Construct a board with exact matching-color cells in one visible scope."""

    rows, cols = sample_dimensions(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="puzzles.cell_board.scoped_attribute.dimensions",
    )
    rng = spawn_rng(int(instance_seed), "puzzles.cell_board.scoped_attribute.case")
    scope, scope_slots = _scope_coords(
        rows=int(rows),
        cols=int(cols),
        scope_kind=str(branch.scope_kind),
        rng=rng,
    )
    answer, support = _sample_scoped_answer(
        rng=rng,
        params=params,
        scope_size=len(scope),
    )
    palette_size = sample_palette_size(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="puzzles.cell_board.scoped_attribute.palette",
    )
    palette = sample_palette(rng=rng, palette_size=int(palette_size))
    target_color = palette[0]
    filler_colors = palette[1:]
    scope_set = set(scope)
    scope_list = list(scope)
    rng.shuffle(scope_list)
    counted = set(scope_list[: int(answer)])
    outside = [coord for coord in all_coords(rows=rows, cols=cols) if coord not in scope_set]
    rng.shuffle(outside)
    distractor_count = min(len(outside), int(rng.randint(0, 3)))
    distractors = set(outside[:distractor_count])
    board = {}
    for index, coord in enumerate(all_coords(rows=rows, cols=cols)):
        board[coord] = (
            target_color
            if coord in counted or coord in distractors
            else filler_colors[index % len(filler_colors)]
        )
    slots = {"query_color": str(target_color[0]), **scope_slots}
    return CellBoardCase(
        rows=int(rows),
        cols=int(cols),
        board_colors=board,
        answer_value=int(answer),
        annotation_kind="bbox_set",
        annotation_coords=tuple(sort_coords(counted)),
        coordinate_labels=str(branch.scope_kind) in {"row", "column"},
        prompt_task_key="cell_board_count_query",
        prompt_query_key=str(branch.query_id),
        prompt_slots=slots,
        execution_trace={
            "scope_kind": str(branch.scope_kind),
            "scope_coords": [[int(r), int(c)] for r, c in sort_coords(scope)],
            "query_color": str(target_color[0]),
            "outside_distractor_count": int(distractor_count),
            "answer_support": [int(value) for value in support],
        },
    )


@register_task
class PuzzlesCellBoardScopedAttributeCountTask:
    """Count named-color cells inside the task-selected board scope."""

    task_id = TASK_ID
    domain = "puzzles"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        selected_query, branch_probs, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=ROW_QUERY,
            task_id=TASK_ID,
            namespace="puzzles.cell_board.scoped_attribute.query",
        )
        branch = _BRANCHES[str(selected_query)]
        return run_cell_board_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            selected_query_id=str(selected_query),
            query_probabilities=branch_probs,
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            objective=CellBoardObjectivePlan(
                prompt_query_key=str(branch.query_id),
                construct_case=lambda seed: _build_scoped_case(
                    instance_seed=int(seed),
                    params=task_params,
                    branch=branch,
                ),
                query_params={"scope_kind": str(branch.scope_kind)},
            ),
        )


__all__ = ["PuzzlesCellBoardScopedAttributeCountTask"]
