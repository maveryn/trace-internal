"""Domain-specific file policies for scene-package migration gates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenePackageFilePolicy:
    """Allowed source layout for one domain's scene-package review candidates."""

    domain: str
    role_shared_files: frozenset[str]
    allowed_private_scene_files: frozenset[str] = frozenset()
    allow_shared_subdirectories: bool = False

    @property
    def allowed_shared_files(self) -> frozenset[str]:
        """Return every allowed direct filename in a scene ``shared/`` package."""

        return frozenset({"__init__.py"}) | self.role_shared_files


CHARTS_SCENE_PACKAGE_FILE_POLICY = ScenePackageFilePolicy(
    domain="charts",
    allowed_private_scene_files=frozenset(
        {
            "_lifecycle.py",
        }
    ),
    role_shared_files=frozenset(
        {
            "state.py",
            "data.py",
            "sampling.py",
            "rendering.py",
            "annotations.py",
            "prompts.py",
            "output.py",
            "defaults.py",
            "styles.py",
            "layout.py",
            "scales.py",
            "metrics.py",
            "spatial_primitives.py",
            "projection.py",
            "assets.py",
            "option_rendering.py",
        }
    ),
)


GAMES_SCENE_PACKAGE_FILE_POLICY = ScenePackageFilePolicy(
    domain="games",
    allowed_private_scene_files=frozenset(
        {
            "_lifecycle.py",
        }
    ),
    role_shared_files=frozenset(
        {
            "state.py",
            "sampling.py",
            "rendering.py",
            "prompts.py",
            "output.py",
            "defaults.py",
            "styles.py",
            "layout.py",
            "rules.py",
            "annotations.py",
            "option_rendering.py",
            "components.py",
            "labels.py",
        }
    ),
)


GEOMETRY_SCENE_PACKAGE_FILE_POLICY = ScenePackageFilePolicy(
    domain="geometry",
    allowed_private_scene_files=frozenset(
        {
            "_lifecycle.py",
        }
    ),
    role_shared_files=frozenset(
        {
            "state.py",
            "construction.py",
            "relations.py",
            "rendering.py",
            "annotations.py",
            "prompts.py",
            "output.py",
            "defaults.py",
            "sampling.py",
            "layout.py",
            "styles.py",
            "spatial_primitives.py",
            "algebra.py",
            "measurements.py",
            "projection.py",
            "option_rendering.py",
        }
    ),
)


GRAPH_SCENE_PACKAGE_FILE_POLICY = ScenePackageFilePolicy(
    domain="graph",
    allowed_private_scene_files=frozenset(
        {
            "_lifecycle.py",
        }
    ),
    role_shared_files=frozenset(
        {
            "state.py",
            "sampling.py",
            "algorithms.py",
            "rendering.py",
            "annotations.py",
            "prompts.py",
            "output.py",
            "defaults.py",
            "layout.py",
            "styles.py",
            "labels.py",
            "metrics.py",
            "topology.py",
            "projection.py",
            "option_rendering.py",
        }
    ),
)


SYMBOLIC_SCENE_PACKAGE_FILE_POLICY = ScenePackageFilePolicy(
    domain="symbolic",
    allowed_private_scene_files=frozenset(
        {
            "_lifecycle.py",
        }
    ),
    role_shared_files=frozenset(
        {
            "state.py",
            "sampling.py",
            "rules.py",
            "layout.py",
            "rendering.py",
            "annotations.py",
            "prompts.py",
            "output.py",
            "defaults.py",
            "styles.py",
            "assets.py",
            "components.py",
            "relations.py",
            "metrics.py",
            "transforms.py",
            "spatial_primitives.py",
            "option_rendering.py",
        }
    ),
)


SCENE_PACKAGE_FILE_POLICIES: dict[str, ScenePackageFilePolicy] = {
    CHARTS_SCENE_PACKAGE_FILE_POLICY.domain: CHARTS_SCENE_PACKAGE_FILE_POLICY,
    GAMES_SCENE_PACKAGE_FILE_POLICY.domain: GAMES_SCENE_PACKAGE_FILE_POLICY,
    GEOMETRY_SCENE_PACKAGE_FILE_POLICY.domain: GEOMETRY_SCENE_PACKAGE_FILE_POLICY,
    GRAPH_SCENE_PACKAGE_FILE_POLICY.domain: GRAPH_SCENE_PACKAGE_FILE_POLICY,
    SYMBOLIC_SCENE_PACKAGE_FILE_POLICY.domain: SYMBOLIC_SCENE_PACKAGE_FILE_POLICY,
}


def scene_package_file_policy(domain: str) -> ScenePackageFilePolicy | None:
    """Return the migration file policy for ``domain`` when one is defined."""

    return SCENE_PACKAGE_FILE_POLICIES.get(str(domain))


__all__ = [
    "CHARTS_SCENE_PACKAGE_FILE_POLICY",
    "GEOMETRY_SCENE_PACKAGE_FILE_POLICY",
    "GAMES_SCENE_PACKAGE_FILE_POLICY",
    "GRAPH_SCENE_PACKAGE_FILE_POLICY",
    "SCENE_PACKAGE_FILE_POLICIES",
    "ScenePackageFilePolicy",
    "SYMBOLIC_SCENE_PACKAGE_FILE_POLICY",
    "scene_package_file_policy",
]
