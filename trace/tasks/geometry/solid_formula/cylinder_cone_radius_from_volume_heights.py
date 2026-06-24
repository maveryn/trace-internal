"""Compute a shared radius from compound cylinder-cone volume data."""

from trace.tasks.registry import register_task

from ._lifecycle import build_solid_formula_plan, run_solid_formula_public_entry
from .shared.measurements import answer_support_probability_map, decimal_support, round1
from .shared.rendering import render_cylinder_cone_radius
from .shared.sampling import select_case_option, select_support_value
from .shared.state import SolidFormulaProblem

TASK_ID = "task_geometry__solid_formula__cylinder_cone_radius_from_volume_heights"
ANNOTATION_KEYS = (
    "target_radius_label",
    "volume_label",
    "total_height_label",
    "cone_height_label",
)
ANSWER_SUPPORT = decimal_support(2, 61, step=1)
CONSTRUCTION_OPTIONS = (
    (6.0, 3.0),
    (8.0, 6.0),
    (10.0, 9.0),
    (12.0, 6.0),
    (14.0, 12.0),
    (16.0, 9.0),
)


def _prepare_radius_objective(
    *,
    instance_seed,
    params,
    selected_query,
    branch_probabilities,
):
    # This task binds radius as the answer before shared rendering.
    radius = select_support_value(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.answer",
        support=ANSWER_SUPPORT,
    )
    (cylinder_height, cone_height), construction_count = select_case_option(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.construction",
        options=CONSTRUCTION_OPTIONS,
    )
    total_height = cylinder_height + cone_height
    volume_pi_multiple = radius**2 * (cylinder_height + (cone_height / 3.0))
    support_probabilities = answer_support_probability_map(ANSWER_SUPPORT, radius)
    problem = SolidFormulaProblem(
        solid_kind="cylinder_cone",
        answer=round1(radius),
        unknown_dimension="radius",
        formula_family="cylinder_cone_radius_from_volume_heights",
        formula="V = pi r^2(H-c) + (1/3)pi r^2c, solve r from V, total height H, and cone height c",
        radius=round1(radius),
        total_height=round1(total_height),
        cylinder_height=round1(cylinder_height),
        cone_height=round1(cone_height),
        volume_pi_multiple=round1(volume_pi_multiple),
        answer_support_probabilities=support_probabilities,
        construction_case_count_for_answer=construction_count,
    )
    return build_solid_formula_plan(
        prompt_key="single",
        problem=problem,
        render_scene=render_cylinder_cone_radius,
        annotation_keys=ANNOTATION_KEYS,
        branch_probabilities=branch_probabilities,
        support_probabilities=support_probabilities,
    )


@register_task
class GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask:
    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = ("single",)
    default_query_id = "single"
    prepare_objective = staticmethod(_prepare_radius_objective)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_solid_formula_public_entry(
            self,
            instance_seed,
            params=params,
            max_attempts=max_attempts,
        )
