"""
Core SpecManager implementation.

The SpecManager is the ONLY component authorized to write spec files.
It provides:
- Schema validation via jsonschema
- Atomic writes with backup
- ETag-based concurrency control (using spec_hash from canonical module)
- Git integration (optional commit on save)
- Compile-to-prompt-plan convenience methods
- Shred/merge overlay behavior (flow.json + flow.ui.json)

This module follows ADR-001 (spec-first architecture) and provides the
central authority for all spec file operations.

The spec store lives at swarm/specs/ (JSON-only runtime truth).
Legacy swarm/spec/ (YAML) is supported for migration but deprecated.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .compile import compile_to_prompt_plan as _compile_to_prompt_plan
from .etag import canonical_json, compute_etag_bytes, compute_file_etag
from .errors import ConcurrencyError, SpecNotFoundError, SpecValidationError
from .git import git_commit
from .io import atomic_write
from .models import FlowGraph, StepTemplate, ValidationError, ValidationResult
from .paths import (
    DEFAULT_SPEC_DIR,
    DEFAULT_SPECS_DIR,
    flow_graph_path,
    flow_path,
    flow_ui_path,
    flows_dir,
    resolve_repo_root,
    schema_path,
    schemas_dir,
    station_path,
    stations_dir,
    template_path,
    templates_dir,
)
from .schemas import load_schema
from .validate import check_jsonschema, validate_spec


logger = logging.getLogger(__name__)

# =============================================================================
# SpecManager
# =============================================================================


class SpecManager:
    """Central manager for spec file operations.

    The SpecManager is the ONLY authorized writer of spec files.
    All spec modifications should go through this class to ensure:
    - Schema validation
    - Atomic writes with backup
    - ETag-based concurrency control
    - Optional git integration
    - Shred/merge overlay behavior (flow.json + flow.ui.json)

    The spec store lives at swarm/specs/ (JSON-only runtime truth).

    Usage:
        manager = SpecManager(repo_root=Path("/path/to/repo"))

        # Read specs (with overlay merge)
        flow = manager.get_flow_with_ui("3-build")  # Merges flow.json + flow.ui.json

        # Read specs
        graph = manager.get_flow_graph("build-flow")
        template = manager.get_step_template("code-critic-template")

        # Validate
        errors = manager.validate_spec("flow_graph", graph_data)

        # Write with concurrency control
        new_etag = manager.save_flow_graph("build-flow", graph_data, etag=old_etag)

        # Write with shred (splits into flow.json + flow.ui.json)
        manager.save_flow_with_ui("3-build", data, ui_data=ui_overlay)

        # Compile to prompt plan
        plan = manager.compile_to_prompt_plan("3-build")
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        spec_dir: Optional[Path] = None,
        specs_dir: Optional[Path] = None,
        enable_git: bool = False,
        backup_on_write: bool = True,
    ):
        """Initialize the SpecManager.

        Args:
            repo_root: Repository root path. If None, attempts to auto-detect.
            spec_dir: Override for legacy spec directory (YAML). If None, uses repo_root/swarm/spec.
            specs_dir: Override for new specs directory (JSON). If None, uses repo_root/swarm/specs.
            enable_git: If True, commit changes after saving specs.
            backup_on_write: If True, create .bak files before overwriting.
        """
        self._repo_root = self._resolve_repo_root(repo_root)
        self._spec_dir = spec_dir or (self._repo_root / DEFAULT_SPEC_DIR)  # Legacy
        self._specs_dir = specs_dir or (self._repo_root / DEFAULT_SPECS_DIR)  # New JSON store
        self._enable_git = enable_git
        self._backup_on_write = backup_on_write

        # Schema cache
        self._schemas: Dict[str, Dict[str, Any]] = {}

        # Validation availability
        self._jsonschema_available = self._check_jsonschema()

        logger.debug(
            "SpecManager initialized: repo_root=%s, specs_dir=%s, git=%s",
            self._repo_root,
            self._specs_dir,
            self._enable_git,
        )

    def _resolve_repo_root(self, repo_root: Optional[Path]) -> Path:
        """Resolve repository root path."""
        return resolve_repo_root(repo_root)

    def _check_jsonschema(self) -> bool:
        """Check if jsonschema is available."""
        return check_jsonschema(logger)

    # =========================================================================
    # Path Resolution
    # =========================================================================

    @property
    def repo_root(self) -> Path:
        """Get repository root path."""
        return self._repo_root

    @property
    def spec_dir(self) -> Path:
        """Get legacy spec directory path (YAML)."""
        return self._spec_dir

    @property
    def specs_dir(self) -> Path:
        """Get new specs directory path (JSON - runtime truth)."""
        return self._specs_dir

    def _flows_dir(self) -> Path:
        """Get flows directory (new JSON store)."""
        return flows_dir(self._specs_dir)

    def _stations_dir(self) -> Path:
        """Get stations directory (new JSON store)."""
        return stations_dir(self._specs_dir)

    def _templates_dir(self) -> Path:
        """Get templates directory (new JSON store)."""
        return templates_dir(self._specs_dir)

    def _schemas_dir(self) -> Path:
        """Get schemas directory (new JSON store, fallback to legacy)."""
        return schemas_dir(self._specs_dir, self._spec_dir)

    def _flow_path(self, flow_id: str) -> Path:
        """Get path to flow JSON file."""
        return flow_path(self._specs_dir, flow_id)

    def _flow_ui_path(self, flow_id: str) -> Path:
        """Get path to flow UI overlay file."""
        return flow_ui_path(self._specs_dir, flow_id)

    def _flow_graph_path(self, flow_id: str) -> Path:
        """Get path to flow graph file (legacy path structure)."""
        return flow_graph_path(self._specs_dir, self._spec_dir, flow_id)

    def _station_path(self, station_id: str) -> Path:
        """Get path to station JSON file."""
        return station_path(self._specs_dir, station_id)

    def _template_path(self, template_id: str) -> Path:
        """Get path to template file."""
        return template_path(self._specs_dir, template_id)

    def _schema_path(self, schema_name: str) -> Path:
        """Get path to schema file."""
        return schema_path(self._schemas_dir(), schema_name)

    # =========================================================================
    # Schema Loading
    # =========================================================================

    def _load_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Load a JSON schema by name.

        Args:
            schema_name: Schema name (e.g., "flow_graph", "step_template").

        Returns:
            Parsed schema dict, or None if not found.
        """
        return load_schema(schema_name, self._schemas_dir(), self._schemas, logger)

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_spec(
        self, spec_type: str, data: Dict[str, Any]
    ) -> List[ValidationError]:
        """Validate spec data against its JSON schema.

        Args:
            spec_type: Type of spec ("flow_graph", "step_template", "run_state", etc.).
            data: The spec data to validate.

        Returns:
            List of validation errors. Empty list means valid.
        """
        return validate_spec(
            self._load_schema,
            spec_type,
            data,
            self._jsonschema_available,
            logger,
        )

    def validate_flow_graph(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate flow graph data."""
        errors = self.validate_spec("flow_graph", data)
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_step_template(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate step template data."""
        errors = self.validate_spec("step_template", data)
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_run_state(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate run state data."""
        errors = self.validate_spec("run_state", data)
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_prompt_plan(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate prompt plan data."""
        errors = self.validate_spec("prompt_plan", data)
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    # =========================================================================
    # Reading Specs
    # =========================================================================

    def get_flow_graph(self, flow_id: str) -> FlowGraph:
        """Load a flow graph by ID.

        Args:
            flow_id: The flow graph identifier (e.g., "build-flow").

        Returns:
            Parsed FlowGraph with computed ETag.

        Raises:
            SpecNotFoundError: If the flow graph doesn't exist.
            SpecValidationError: If the data fails schema validation.
        """
        path = self._flow_graph_path(flow_id)
        if not path.exists():
            raise SpecNotFoundError("flow_graph", flow_id, path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise SpecValidationError(
                "flow_graph",
                [ValidationError(path="", message=f"Invalid JSON: {e}")],
            )

        # Validate
        errors = self.validate_spec("flow_graph", data)
        if errors:
            raise SpecValidationError("flow_graph", errors)

        # Compute ETag
        etag = compute_file_etag(path)

        return FlowGraph.from_dict(data, etag=etag)

    def get_step_template(self, template_id: str) -> StepTemplate:
        """Load a step template by ID.

        Args:
            template_id: The template identifier (e.g., "code-critic-template").

        Returns:
            Parsed StepTemplate with computed ETag.

        Raises:
            SpecNotFoundError: If the template doesn't exist.
            SpecValidationError: If the data fails schema validation.
        """
        path = self._template_path(template_id)
        if not path.exists():
            raise SpecNotFoundError("step_template", template_id, path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise SpecValidationError(
                "step_template",
                [ValidationError(path="", message=f"Invalid JSON: {e}")],
            )

        # Validate
        errors = self.validate_spec("step_template", data)
        if errors:
            raise SpecValidationError("step_template", errors)

        # Compute ETag
        etag = compute_file_etag(path)

        return StepTemplate.from_dict(data, etag=etag)

    def get_all_templates(self) -> List[StepTemplate]:
        """Load all step templates.

        Returns:
            List of all valid StepTemplates.
            Invalid templates are logged and skipped.
        """
        templates: List[StepTemplate] = []
        templates_dir = self._templates_dir()

        if not templates_dir.exists():
            logger.debug("Templates directory not found: %s", templates_dir)
            return templates

        for json_file in templates_dir.glob("*.json"):
            template_id = json_file.stem
            try:
                template = self.get_step_template(template_id)
                templates.append(template)
            except (SpecNotFoundError, SpecValidationError) as e:
                logger.warning("Skipping invalid template %s: %s", template_id, e)

        return sorted(templates, key=lambda t: t.id)

    def list_flow_graphs(self) -> List[str]:
        """List all available flow graph IDs."""
        flows_dir = self._flows_dir()
        if not flows_dir.exists():
            return []

        flow_ids = []
        for item in flows_dir.iterdir():
            if item.is_dir() and (item / "graph.json").exists():
                flow_ids.append(item.name)

        return sorted(flow_ids)

    def list_templates(self) -> List[str]:
        """List all available template IDs."""
        templates_dir = self._templates_dir()
        if not templates_dir.exists():
            return []

        return sorted(
            p.stem
            for p in templates_dir.glob("*.json")
            if not p.name.startswith("_")
        )

    def get_template(self, template_id: str) -> Tuple[Dict[str, Any], str]:
        """Get a template as raw dict with ETag.

        This is a convenience method for the API layer that returns the
        template data as a dict (for JSON serialization) along with an ETag
        for HTTP caching.

        Args:
            template_id: The template identifier (e.g., "microloop-writer").

        Returns:
            Tuple of (template_data_dict, etag_string).

        Raises:
            FileNotFoundError: If template not found.
        """
        path = self._template_path(template_id)
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_id}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        etag = compute_file_etag(path)
        return data, etag

    # =========================================================================
    # Writing Specs
    # =========================================================================

    def _atomic_write(
        self,
        path: Path,
        content: str,
        create_backup: bool = True,
    ) -> None:
        """Atomically write content to a file.

        Uses write-to-temp-then-rename pattern for atomicity.

        Args:
            path: Target file path.
            content: Content to write.
            create_backup: If True and file exists, create .bak backup.
        """
        atomic_write(path, content, create_backup=create_backup, logger=logger)

    def _git_commit(self, path: Path, message: str) -> bool:
        """Commit a file change to git.

        Args:
            path: Path to the changed file.
            message: Commit message.

        Returns:
            True if commit succeeded, False otherwise.
        """
        if not self._enable_git:
            return False

        return git_commit(self._repo_root, path, message, logger)

    def save_flow_graph(
        self,
        flow_id: str,
        data: Dict[str, Any],
        etag: Optional[str] = None,
        commit: bool = False,
        commit_message: Optional[str] = None,
    ) -> str:
        """Save a flow graph spec.

        Args:
            flow_id: The flow graph identifier.
            data: The flow graph data to save.
            etag: If provided, verify this matches current ETag (for concurrency).
            commit: If True, commit the change to git.
            commit_message: Custom commit message.

        Returns:
            New ETag after save.

        Raises:
            SpecValidationError: If data fails schema validation.
            ConcurrencyError: If etag doesn't match current file state.
        """
        # Validate
        errors = self.validate_spec("flow_graph", data)
        if errors:
            raise SpecValidationError("flow_graph", errors)

        path = self._flow_graph_path(flow_id)

        # Check ETag for concurrency control
        if etag is not None:
            current_etag = compute_file_etag(path)
            if current_etag is not None and current_etag != etag:
                raise ConcurrencyError("flow_graph", flow_id, etag, current_etag)

        # Serialize
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        # Atomic write
        self._atomic_write(path, content, create_backup=self._backup_on_write)

        # Compute new ETag
        new_etag = compute_etag_bytes(content.encode("utf-8"))

        # Git commit if requested
        if commit or (self._enable_git and commit_message):
            msg = commit_message or f"Update flow graph: {flow_id}"
            self._git_commit(path, msg)

        logger.info("Saved flow graph: %s (etag: %s)", flow_id, new_etag[:16])
        return new_etag

    def save_step_template(
        self,
        template_id: str,
        data: Dict[str, Any],
        etag: Optional[str] = None,
        commit: bool = False,
        commit_message: Optional[str] = None,
    ) -> str:
        """Save a step template spec.

        Args:
            template_id: The template identifier.
            data: The template data to save.
            etag: If provided, verify this matches current ETag (for concurrency).
            commit: If True, commit the change to git.
            commit_message: Custom commit message.

        Returns:
            New ETag after save.

        Raises:
            SpecValidationError: If data fails schema validation.
            ConcurrencyError: If etag doesn't match current file state.
        """
        # Validate
        errors = self.validate_spec("step_template", data)
        if errors:
            raise SpecValidationError("step_template", errors)

        path = self._template_path(template_id)

        # Check ETag for concurrency control
        if etag is not None:
            current_etag = compute_file_etag(path)
            if current_etag is not None and current_etag != etag:
                raise ConcurrencyError("step_template", template_id, etag, current_etag)

        # Serialize
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        # Atomic write
        self._atomic_write(path, content, create_backup=self._backup_on_write)

        # Compute new ETag
        new_etag = compute_etag_bytes(content.encode("utf-8"))

        # Git commit if requested
        if commit or (self._enable_git and commit_message):
            msg = commit_message or f"Update step template: {template_id}"
            self._git_commit(path, msg)

        logger.info("Saved step template: %s (etag: %s)", template_id, new_etag[:16])
        return new_etag

    # =========================================================================
    # Prompt Plan Compilation
    # =========================================================================

    def compile_to_prompt_plan(
        self,
        flow_id: str,
        step_id: Optional[str] = None,
        run_base: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Compile a flow to a prompt plan.

        This is a convenience method that delegates to the SpecCompiler.
        For advanced compilation options, use the SpecCompiler directly.

        Args:
            flow_id: Flow specification ID (e.g., "3-build").
            step_id: Optional step ID. If None, returns plan for first step.
            run_base: Run base directory for artifact paths.

        Returns:
            Compiled prompt plan as dictionary.

        Raises:
            SpecNotFoundError: If flow or station not found.
            ValueError: If step_id not found in flow.
        """
        return _compile_to_prompt_plan(
            self._repo_root,
            flow_id,
            step_id=step_id,
            run_base=run_base,
        )

    # =========================================================================
    # Shred/Merge Overlay (flow.json + flow.ui.json)
    # =========================================================================

    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge overlay into base.

        Arrays are replaced, not merged. Nested dicts are recursively merged.
        """
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_flow_with_ui(self, flow_id: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """Load a flow spec with UI overlay merged.

        Reads flow.json and flow.ui.json, deep merges them.
        Returns merged data and combined ETag.

        Args:
            flow_id: The flow identifier (e.g., "3-build").

        Returns:
            Tuple of (merged_data, combined_etag).

        Raises:
            SpecNotFoundError: If flow.json doesn't exist.
        """
        flow_path = self._flow_path(flow_id)
        ui_path = self._flow_ui_path(flow_id)

        if not flow_path.exists():
            raise SpecNotFoundError("flow", flow_id, flow_path)

        try:
            with open(flow_path, "r", encoding="utf-8") as f:
                flow_data = json.load(f)
        except json.JSONDecodeError as e:
            raise SpecValidationError(
                "flow",
                [ValidationError(path="", message=f"Invalid JSON: {e}")],
            )

        # Load UI overlay if it exists
        ui_data = {}
        if ui_path.exists():
            try:
                with open(ui_path, "r", encoding="utf-8") as f:
                    ui_data = json.load(f)
            except json.JSONDecodeError as e:
                logger.warning("Invalid UI overlay JSON for %s: %s", flow_id, e)

        # Merge
        merged = self._deep_merge(flow_data, ui_data)

        # Combined ETag from both files
        flow_etag = compute_file_etag(flow_path) or ""
        ui_etag = compute_file_etag(ui_path) or ""
        combined_etag = compute_etag_bytes(f"{flow_etag}:{ui_etag}".encode("utf-8"))

        return merged, combined_etag

    def save_flow_with_ui(
        self,
        flow_id: str,
        data: Dict[str, Any],
        ui_keys: Optional[List[str]] = None,
        etag: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Save a flow spec, shredding UI-only fields into flow.ui.json.

        This supports the shred/merge pattern where:
        - flow.json contains runtime-relevant data
        - flow.ui.json contains UI-only overlays (positions, colors, etc.)

        Args:
            flow_id: The flow identifier.
            data: The full flow data (will be split).
            ui_keys: Keys to extract to UI overlay. Defaults to ["ui", "positions", "layout"].
            etag: If provided, verify combined ETag matches.

        Returns:
            Tuple of (flow_etag, ui_etag).
        """
        if ui_keys is None:
            ui_keys = ["ui", "positions", "layout", "style", "viewport"]

        flow_path = self._flow_path(flow_id)
        ui_path = self._flow_ui_path(flow_id)

        # Check ETag for concurrency
        if etag is not None:
            _, current_etag = self.get_flow_with_ui(flow_id)
            if current_etag and current_etag != etag:
                raise ConcurrencyError("flow", flow_id, etag, current_etag)

        # Split data
        flow_data = {}
        ui_data = {}

        for key, value in data.items():
            if key in ui_keys:
                ui_data[key] = value
            else:
                flow_data[key] = value

        # Ensure directories exist
        flow_path.parent.mkdir(parents=True, exist_ok=True)

        # Save flow.json using canonical JSON
        flow_content = canonical_json(flow_data, indent=2) + "\n"
        self._atomic_write(flow_path, flow_content, create_backup=self._backup_on_write)
        flow_etag = compute_etag_bytes(flow_content.encode("utf-8"))

        # Save flow.ui.json only if there's UI data
        ui_etag = ""
        if ui_data:
            ui_content = canonical_json(ui_data, indent=2) + "\n"
            self._atomic_write(ui_path, ui_content, create_backup=self._backup_on_write)
            ui_etag = compute_etag_bytes(ui_content.encode("utf-8"))

        logger.info(
            "Saved flow with UI: %s (flow_etag: %s, ui_etag: %s)",
            flow_id,
            flow_etag[:12],
            ui_etag[:12] if ui_etag else "none",
        )

        return flow_etag, ui_etag

    def save_station(
        self,
        station_id: str,
        data: Dict[str, Any],
        etag: Optional[str] = None,
    ) -> str:
        """Save a station spec to the JSON store.

        Args:
            station_id: The station identifier.
            data: The station data to save.
            etag: If provided, verify this matches current ETag.

        Returns:
            New ETag after save.
        """
        # Validate
        errors = self.validate_spec("station", data)
        if errors:
            raise SpecValidationError("station", errors)

        path = self._station_path(station_id)

        # Check ETag for concurrency control
        if etag is not None:
            current_etag = compute_file_etag(path)
            if current_etag is not None and current_etag != etag:
                raise ConcurrencyError("station", station_id, etag, current_etag)

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize using canonical JSON
        content = canonical_json(data, indent=2) + "\n"

        # Atomic write
        self._atomic_write(path, content, create_backup=self._backup_on_write)

        # Compute new ETag
        new_etag = compute_etag_bytes(content.encode("utf-8"))

        logger.info("Saved station: %s (etag: %s)", station_id, new_etag[:16])
        return new_etag

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def check_spec_exists(self, spec_type: str, spec_id: str) -> bool:
        """Check if a spec file exists.

        Args:
            spec_type: Type of spec ("flow_graph", "step_template").
            spec_id: The spec identifier.

        Returns:
            True if the spec file exists.
        """
        if spec_type == "flow_graph":
            return self._flow_graph_path(spec_id).exists()
        elif spec_type == "step_template":
            return self._template_path(spec_id).exists()
        else:
            logger.warning("Unknown spec type: %s", spec_type)
            return False

    def get_spec_etag(self, spec_type: str, spec_id: str) -> Optional[str]:
        """Get ETag for a spec file without loading it.

        Args:
            spec_type: Type of spec ("flow_graph", "step_template").
            spec_id: The spec identifier.

        Returns:
            ETag string, or None if file doesn't exist.
        """
        if spec_type == "flow_graph":
            path = self._flow_graph_path(spec_id)
        elif spec_type == "step_template":
            path = self._template_path(spec_id)
        else:
            return None

        return compute_file_etag(path)

    def clear_schema_cache(self) -> None:
        """Clear the schema cache."""
        self._schemas.clear()
        logger.debug("Schema cache cleared")


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


_default_manager: Optional[SpecManager] = None


def get_manager(repo_root: Optional[Path] = None) -> SpecManager:
    """Get or create the default SpecManager.

    Args:
        repo_root: Optional repository root. If None, uses auto-detection.

    Returns:
        The SpecManager instance.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = SpecManager(repo_root=repo_root)
    return _default_manager


def reset_manager() -> None:
    """Reset the default SpecManager (useful for testing)."""
    global _default_manager
    _default_manager = None


__all__ = ["SpecManager", "get_manager", "reset_manager"]
