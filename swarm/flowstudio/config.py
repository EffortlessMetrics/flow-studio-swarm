"""
Flow Studio configuration module.

Provides FlowStudioConfig dataclass for managing Flow Studio paths.
This creates a seam for future extraction into a standalone package
while keeping the current single-repo structure.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FlowStudioConfig:
    """
    Configuration for Flow Studio paths and settings.

    All paths are absolute Path objects. Use from_repo_root() to construct
    from a repository root path.

    Attributes:
        repo_root: Root of the repository
        flows_dir: Directory containing flow YAML configs
        agents_dir: Directory containing agent YAML configs
        tours_dir: Directory containing tour YAML configs
        runs_dir: Directory containing active runs (gitignored)
        examples_dir: Directory containing example runs (committed)
        artifact_catalog: Path to artifact catalog JSON
    """

    repo_root: Path
    flows_dir: Path
    agents_dir: Path
    tours_dir: Path
    runs_dir: Path
    examples_dir: Path
    artifact_catalog: Path

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "FlowStudioConfig":
        """
        Construct config from a repository root path.

        Args:
            repo_root: Path to the repository root

        Returns:
            FlowStudioConfig with all paths resolved
        """
        repo_root = repo_root.resolve()
        return cls(
            repo_root=repo_root,
            flows_dir=repo_root / "swarm" / "config" / "flows",
            agents_dir=repo_root / "swarm" / "config" / "agents",
            tours_dir=repo_root / "swarm" / "config" / "tours",
            runs_dir=repo_root / "swarm" / "runs",
            examples_dir=repo_root / "swarm" / "examples",
            artifact_catalog=repo_root / "swarm" / "meta" / "artifact_catalog.json",
        )

    @classmethod
    def from_file(cls, file_path: Path, levels_up: int = 2) -> "FlowStudioConfig":
        """
        Construct config from a file path by walking up directories.

        This is useful for constructing config from __file__ in scripts.

        Args:
            file_path: Path to a file (e.g., __file__)
            levels_up: Number of parent directories to walk up (default: 2)

        Returns:
            FlowStudioConfig with all paths resolved
        """
        repo_root = Path(file_path).resolve()
        for _ in range(levels_up):
            repo_root = repo_root.parent
        return cls.from_repo_root(repo_root)

    def validate(self) -> list[str]:
        """
        Validate that required directories exist.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.repo_root.exists():
            errors.append(f"repo_root does not exist: {self.repo_root}")
            return errors  # Can't check others if root missing

        if not self.flows_dir.exists():
            errors.append(f"flows_dir does not exist: {self.flows_dir}")

        if not self.agents_dir.exists():
            errors.append(f"agents_dir does not exist: {self.agents_dir}")

        # runs_dir and examples_dir may not exist yet (created on demand)
        # artifact_catalog may not exist yet (optional)
        # tours_dir may not exist (optional feature)

        return errors

    def ensure_runs_dir(self) -> None:
        """Create runs directory if it doesn't exist."""
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def get_run_path(self, run_id: str) -> Path:
        """Get path to a specific run."""
        return self.runs_dir / run_id

    def get_example_path(self, example_id: str) -> Path:
        """Get path to a specific example."""
        return self.examples_dir / example_id

    def list_flows(self) -> list[Path]:
        """List all flow YAML files."""
        if not self.flows_dir.exists():
            return []
        return sorted(self.flows_dir.glob("*.yaml"))

    def list_agents(self) -> list[Path]:
        """List all agent YAML files."""
        if not self.agents_dir.exists():
            return []
        return sorted(self.agents_dir.glob("*.yaml"))

    def list_runs(self) -> list[Path]:
        """List all active runs."""
        if not self.runs_dir.exists():
            return []
        import os

        runs = []
        with os.scandir(self.runs_dir) as it:
            for entry in it:
                if entry.is_dir() and not entry.name.startswith("."):
                    runs.append(Path(entry.path))
        return sorted(runs)

    def list_examples(self) -> list[Path]:
        """List all example runs."""
        if not self.examples_dir.exists():
            return []
        import os

        examples = []
        with os.scandir(self.examples_dir) as it:
            for entry in it:
                if entry.is_dir() and not entry.name.startswith("."):
                    examples.append(Path(entry.path))
        return sorted(examples)


# Default config instance (lazily constructed)
_DEFAULT_CONFIG: Optional[FlowStudioConfig] = None


def get_default_config() -> FlowStudioConfig:
    """
    Get the default FlowStudioConfig for this repository.

    Lazily constructs the config on first call.
    """
    global _DEFAULT_CONFIG
    if _DEFAULT_CONFIG is None:
        _DEFAULT_CONFIG = FlowStudioConfig.from_file(Path(__file__), levels_up=2)
    return _DEFAULT_CONFIG
