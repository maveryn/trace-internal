"""Compute cylinder height from compound cylinder-cone volume data."""

from trace.tasks.registry import register_task

from ._lifecycle import build_solid_formula_plan, run_solid_formula_public_entry
from .shared.defaults import SCENE_ID
from .shared.measurements import answer_support_probability_map, decimal_support, round1
from .shared.rendering import render_cylinder_cone_height
from .shared.sampling import select_case_option, select_support_value
from .shared.state import SolidFormulaProblem

TASK_ID = "task_geometry__solid_formula__cylinder_cone_height_from_volume_radius"
ANNOTATION_KEYS = (
    "target_cylinder_height_label",
    "volume_label",
    "radius_label",
    "cone_height_label",
)
ANSWER_SUPPORT = decimal_support(2, 61, step=1)
CONSTRUCTION_OPTIONS = (
    (3.0, 3.0),
    (4.0, 6.0),
    (5.0, 9.0),
    (6.0, 12.0),
    (7.0, 6.0),
    (8.0, 9.0),
)


def _prepare_height_objective(
    *,
    instance_seed,
    params,
    selected_query,
    branch_probabilities,
):
    # This task binds cylinder height as the answer before rendering.
    cylinder_height = select_support_value(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.answer",
        support=ANSWER_SUPPORT,
    )
    (radius, cone_height), construction_count = select_case_option(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.construction",
        options=CONSTRUCTION_OPTIONS,
    )
    volume_pi_multiple = radius**2 * (cylinder_height + (cone_height / 3.0))
    support_probabilities = answer_support_probability_map(ANSWER_SUPPORT, cylinder_height)
    problem = SolidFormulaProblem(
        solid_kind="cylinder_cone",
        answer=round1(cylinder_height),
        unknown_dimension="cylinder_height",
        formula_family="cylinder_cone_height_from_volume_radius",
        formula="V = pi r^2x + (1/3)pi r^2c, solve cylinder height x from V, r, and cone height c",
        radius=round1(radius),
        cylinder_height=round1(cylinder_height),
        cone_height=round1(cone_height),
        volume_pi_multiple=round1(volume_pi_multiple),
        answer_support_probabilities=support_probabilities,
        construction_case_count_for_answer=construction_count,
    )
    return build_solid_formula_plan(
        prompt_key="single",
        problem=problem,
        render_scene=render_cylinder_cone_height,
        annotation_keys=ANNOTATION_KEYS,
        branch_probabilities=branch_probabilities,
        support_probabilities=support_probabilities,
    )


@register_task
class GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask:
    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = ("single",)
    default_query_id = "single"
    prepare_objective = staticmethod(_prepare_height_objective)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_solid_formula_public_entry(
            self,
            instance_seed,
            params=params,
            max_attempts=max_attempts,
        )
