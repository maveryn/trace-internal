"""Public task for `task_charts__surface_3d__surface_extremum_label`."""

from __future__ import annotations

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.charts.surface_3d._lifecycle import Surface3DTaskPlan, run_surface_3d_lifecycle
from trace.tasks.charts.surface_3d.shared.annotations import bbox_for_single_witness
from trace.tasks.charts.surface_3d.shared.defaults import DOMAIN, SURFACE_VARIANT
from trace.tasks.charts.surface_3d.shared.sampling import (
    balanced_choice,
    balanced_int,
    configured_count,
    sample_entity_labels,
)
from trace.tasks.charts.surface_3d.shared.state import Surface3DDataset, SurfaceCell
from trace.tasks.registry import register_task


TASK_ID = "task_charts__surface_3d__surface_extremum_label"
OBJECTIVE_CONTRACT = "surface_extremum_label"
HIGHEST_QUERY_ID = "highest"
LOWEST_QUERY_ID = "lowest"
SUPPORTED_QUERY_IDS = (HIGHEST_QUERY_ID, LOWEST_QUERY_ID)
DEFAULT_QUERY_ID = HIGHEST_QUERY_ID
PROMPT_QUERY_KEY_BY_BRANCH = {
    HIGHEST_QUERY_ID: "surface_highest_value",
    LOWEST_QUERY_ID: "surface_lowest_value",
}


def _row_answer_value(row_values_by_x, selected_branch):
    if str(selected_branch) == HIGHEST_QUERY_ID:
        target_value = max(row_values_by_x.values())
    elif str(selected_branch) == LOWEST_QUERY_ID:
        target_value = min(row_values_by_x.values())
    else:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    winners = [str(label) for label, value in row_values_by_x.items() if int(value) == int(target_value)]
    if len(winners) != 1:
        raise ValueError("surface extremum answer is not unique")
    return str(winners[0]), int(target_value)


def _build_surface_dataset(params, instance_seed, selected_branch):
    """Sample one categorical surface row with a unique highest/lowest x-label answer."""

    x_count = balanced_int(
        low=configured_count(params, "surface_x_count_min", 5),
        high=configured_count(params, "surface_x_count_max", 7),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.x_count",
    )
    y_count = balanced_int(
        low=configured_count(params, "surface_y_count_min", 4),
        high=configured_count(params, "surface_y_count_max", 6),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.y_count",
    )
    x_labels = sample_entity_labels(int(x_count), instance_seed=int(instance_seed), namespace="surface_x")
    y_labels = sample_entity_labels(int(y_count), instance_seed=int(instance_seed), namespace="surface_y")
    target_y = str(
        balanced_choice(
            y_labels,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_y",
        )
    )
    answer_x = str(
        balanced_choice(
            x_labels,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.answer_x.{selected_branch}",
        )
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values")
    cells: list[SurfaceCell] = []
    for y_index, y_label in enumerate(y_labels):
        row_values = [int(rng.randint(25, 74)) for _ in range(int(x_count))]
        if str(y_label) == target_y:
            answer_index = list(x_labels).index(answer_x)
            if str(selected_branch) == HIGHEST_QUERY_ID:
                row_values = [int(min(value, 70)) for value in row_values]
                row_values[answer_index] = int(rng.randint(86, 96))
            else:
                row_values = [int(max(value, 30)) for value in row_values]
                row_values[answer_index] = int(rng.randint(7, 16))
        for x_index, x_label in enumerate(x_labels):
            cells.append(
                SurfaceCell(
                    cell_id=f"cell_{x_label}_{y_label}",
                    x_label=str(x_label),
                    y_label=str(y_label),
                    x_index=int(x_index),
                    y_index=int(y_index),
                    value=int(row_values[x_index]),
                )
            )
    row_values_by_x = {str(cell.x_label): int(cell.value) for cell in cells if str(cell.y_label) == target_y}
    answer_label, answer_value = _row_answer_value(row_values_by_x, str(selected_branch))
    if str(answer_label) != str(answer_x):
        raise ValueError("constructed surface answer does not match selected cell")
    dataset = Surface3DDataset(
        scene_variant=SURFACE_VARIANT,
        points=(),
        surface_cells=tuple(cells),
        panels=(),
        x_axis_label="Platform",
        y_axis_label="Group",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(x_count) - 1))),
        y_range=(0.0, float(max(1, int(y_count) - 1))),
        z_range=(0.0, 100.0),
        x_labels=tuple(x_labels),
        y_labels=tuple(y_labels),
        title="3D Surface Chart",
    )
    return dataset, target_y, answer_label, answer_value, row_values_by_x


def _build_plan(params, instance_seed, selected_branch, query_probabilities):
    """Bind row-extremum semantics for one categorical 3D surface."""

    if str(selected_branch) not in SUPPORTED_QUERY_IDS:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    dataset, target_y, answer_label, answer_value, row_values_by_x = _build_surface_dataset(
        params,
        int(instance_seed),
        str(selected_branch),
    )
    answer_cell_id = f"cell_{answer_label}_{target_y}"

    def _bind_annotation(rendered):
        return bbox_for_single_witness(rendered.surface_cell_bboxes_px[str(answer_cell_id)])

    return Surface3DTaskPlan(
        dataset=dataset,
        answer_gt=TypedValue(type="string", value=str(answer_label)),
        annotation_builder=_bind_annotation,
        prompt_query_key=str(PROMPT_QUERY_KEY_BY_BRANCH[str(selected_branch)]),
        dynamic_slots={"target_y_category": str(target_y)},
        branch_params={
            "target_y_category": str(target_y),
            "answer_cell_id": str(answer_cell_id),
            "answer_value": int(answer_value),
            "row_values_by_x": dict(row_values_by_x),
            "x_count": len(dataset.x_labels),
            "y_count": len(dataset.y_labels),
        },
        relations={
            "target_y_category": str(target_y),
            "answer_cell_id": str(answer_cell_id),
            "answer_label": str(answer_label),
            "query_id_probabilities": dict(query_probabilities),
        },
        witness_symbolic={
            "type": "surface_3d_surface_extremum_witness",
            "cell_id": str(answer_cell_id),
            "answer": str(answer_label),
        },
        question_format="surface_3d_surface_extremum_label",
    )


class ChartsThreeDSurfaceExtremumLabelTask:
    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = OBJECTIVE_CONTRACT
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True
    default_query_id = DEFAULT_QUERY_ID
    build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_surface_3d_lifecycle(
            task=self,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            default_query_id=DEFAULT_QUERY_ID,
            build_plan=_build_plan,
        )


register_task(ChartsThreeDSurfaceExtremumLabelTask)


__all__ = ["ChartsThreeDSurfaceExtremumLabelTask"]
