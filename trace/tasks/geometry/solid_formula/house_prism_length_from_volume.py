"""Compute length from a house-prism volume."""

from trace.tasks.registry import register_task

from ._lifecycle import build_solid_formula_plan, run_solid_formula_public_entry
from .shared.measurements import answer_support_probability_map, decimal_support, round1
from .shared.rendering import render_house_prism
from .shared.sampling import select_case_option, select_support_value
from .shared.state import SolidFormulaProblem

TASK_ID = "task_geometry__solid_formula__house_prism_length_from_volume"
ANNOTATION_KEYS = (
    "target_length_label",
    "volume_label",
    "triangle_base_label",
    "wall_height_label",
    "roof_height_label",
)
ANSWER_SUPPORT = decimal_support(2, 61, step=1)
CONSTRUCTION_OPTIONS = (
    (6.0, 4.0, 3.0),
    (8.0, 5.0, 4.0),
    (10.0, 4.0, 6.0),
    (12.0, 6.0, 3.0),
    (14.0, 5.0, 5.0),
    (16.0, 4.0, 6.0),
)


def _prepare_house_length_objective(
    *,
    instance_seed,
    params,
    selected_query,
    branch_probabilities,
):
    # This task binds prism length as the answer before rendering.
    prism_length = select_support_value(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.answer",
        support=ANSWER_SUPPORT,
    )
    (triangle_base, wall_height, roof_height), construction_count = select_case_option(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.construction",
        options=CONSTRUCTION_OPTIONS,
    )
    cross_section_area = (triangle_base * wall_height) + (0.5 * triangle_base * roof_height)
    volume = cross_section_area * prism_length
    support_probabilities = answer_support_probability_map(ANSWER_SUPPORT, prism_length)
    problem = SolidFormulaProblem(
        solid_kind="house_prism",
        answer=round1(prism_length),
        unknown_dimension="length",
        formula_family="house_prism_length_from_volume",
        formula="V = (bh + (1/2)bt)L, solve length L from rectangular wall and triangular roof cross-section",
        triangle_base=round1(triangle_base),
        prism_length=round1(prism_length),
        wall_height=round1(wall_height),
        roof_height=round1(roof_height),
        volume=round1(volume),
        answer_support_probabilities=support_probabilities,
        construction_case_count_for_answer=construction_count,
    )
    return build_solid_formula_plan(
        prompt_key="single",
        problem=problem,
        render_scene=render_house_prism,
        annotation_keys=ANNOTATION_KEYS,
        branch_probabilities=branch_probabilities,
        support_probabilities=support_probabilities,
    )


@register_task
class GeometrySolidFormulaHousePrismLengthFromVolumeTask:
    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = ("single",)
    default_query_id = "single"
    prepare_objective = staticmethod(_prepare_house_length_objective)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_solid_formula_public_entry(
            self,
            instance_seed,
            params=params,
            max_attempts=max_attempts,
        )
