"""Compute prism height from a prism-plus-pyramid volume."""

from trace.tasks.registry import register_task

from ._lifecycle import build_solid_formula_plan, run_solid_formula_public_entry
from .shared.measurements import answer_support_probability_map, decimal_support, round1
from .shared.rendering import render_prism_pyramid
from .shared.sampling import select_case_option, select_support_value
from .shared.state import SolidFormulaProblem

TASK_ID = "task_geometry__solid_formula__prism_pyramid_height_from_volume"
ANNOTATION_KEYS = (
    "target_prism_height_label",
    "volume_label",
    "known_length_label",
    "known_width_label",
    "pyramid_height_label",
)
ANSWER_SUPPORT = decimal_support(2, 61, step=1)
CONSTRUCTION_OPTIONS = (
    (5.0, 4.0, 3.0),
    (6.0, 5.0, 6.0),
    (7.0, 4.0, 9.0),
    (8.0, 6.0, 3.0),
    (9.0, 5.0, 6.0),
    (10.0, 7.0, 9.0),
)


def _prepare_prism_height_objective(
    *,
    instance_seed,
    params,
    selected_query,
    branch_probabilities,
):
    # This task binds prism height as the answer before rendering.
    prism_height = select_support_value(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.answer",
        support=ANSWER_SUPPORT,
    )
    (side_a, side_b, pyramid_height), construction_count = select_case_option(
        instance_seed=instance_seed,
        params=params,
        namespace=f"{TASK_ID}.{selected_query}.construction",
        options=CONSTRUCTION_OPTIONS,
    )
    base_area = side_a * side_b
    volume = base_area * (prism_height + (pyramid_height / 3.0))
    support_probabilities = answer_support_probability_map(ANSWER_SUPPORT, prism_height)
    problem = SolidFormulaProblem(
        solid_kind="prism_pyramid",
        answer=round1(prism_height),
        unknown_dimension="prism_height",
        formula_family="prism_pyramid_height_from_volume",
        formula="V = lwx + (1/3)lwp, solve prism height x from V, l, w, and pyramid height p",
        side_a=round1(side_a),
        side_b=round1(side_b),
        prism_height=round1(prism_height),
        pyramid_height=round1(pyramid_height),
        volume=round1(volume),
        answer_support_probabilities=support_probabilities,
        construction_case_count_for_answer=construction_count,
    )
    return build_solid_formula_plan(
        prompt_key="single",
        problem=problem,
        render_scene=render_prism_pyramid,
        annotation_keys=ANNOTATION_KEYS,
        branch_probabilities=branch_probabilities,
        support_probabilities=support_probabilities,
    )


@register_task
class GeometrySolidFormulaPrismPyramidHeightFromVolumeTask:
    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = ("single",)
    default_query_id = "single"
    prepare_objective = staticmethod(_prepare_prism_height_objective)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_solid_formula_public_entry(
            self,
            instance_seed,
            params=params,
            max_attempts=max_attempts,
        )
