"""
compiler.py - Compile specs + context into PromptPlan for SDK execution.

The compiler takes:
- FlowSpec + Step (the orchestrator spine)
- StationSpec (the role contract)
- ContextPack (hydrated context: artifacts + envelopes)
- Run paths (run_base, output locations)

And produces a PromptPlan with:
- ClaudeAgentOptions (tools, sandbox, model, cwd, max_turns)
- system_prompt.append (identity + invariants)
- user_prompt (objective + pointers + required outputs + finalization)
- prompt_hash (for traceability)
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .loader import load_flow, load_fragment, load_fragments, load_station
from .types import (
    FlowSpec,
    FlowStep,
    HandoffContract,
    PromptPlan,
    RoutingKind,
    StationSpec,
    VerificationRequirements,
)

if TYPE_CHECKING:
    from swarm.runtime.context_pack import ContextPack
    from swarm.runtime.engines.models import StepContext

logger = logging.getLogger(__name__)


# =============================================================================
# Flow Key Extraction
# =============================================================================


def extract_flow_key(flow_id: str) -> str:
    """Extract the flow key from a flow ID.

    Flow IDs are typically formatted as "<number>-<key>" (e.g., "3-build").
    This function extracts the key portion for routing purposes.

    Args:
        flow_id: The full flow identifier (e.g., "3-build").

    Returns:
        The flow key (e.g., "build").

    Examples:
        >>> extract_flow_key("3-build")
        'build'
        >>> extract_flow_key("1-signal")
        'signal'
        >>> extract_flow_key("build")  # Already just the key
        'build'
    """
    if "-" in flow_id:
        # Split on first hyphen and take everything after
        parts = flow_id.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return parts[1]
    return flow_id


# =============================================================================
# Template Rendering
# =============================================================================


def render_template(template: str, variables: Dict[str, Any]) -> str:
    """Render a Mustache-style template with {{variable}} substitution.

    Supports nested access like {{step.objective}} and {{run.base}}.

    Args:
        template: Template string with {{variable}} placeholders.
        variables: Dictionary of variable values (can be nested).

    Returns:
        Rendered string with substitutions applied.
    """
    def get_nested(obj: Any, path: str) -> str:
        """Get a nested value from a dict using dot notation."""
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, "")
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return ""
        return str(current) if current else ""

    def replace_match(match: re.Match) -> str:
        var_path = match.group(1).strip()
        return get_nested(variables, var_path)

    return re.sub(r"\{\{([^}]+)\}\}", replace_match, template)


# =============================================================================
# Prompt Building
# =============================================================================


def build_system_append(
    station: StationSpec,
    scent_trail: Optional[str] = None,
) -> str:
    """Build the system prompt append from station identity.

    Combines:
    - Station identity (system_append)
    - Station invariants
    - Scent trail (wisdom from previous runs)

    Args:
        station: The station specification.
        scent_trail: Optional cross-run wisdom content.

    Returns:
        Combined system prompt append text.
    """
    parts: List[str] = []

    # Station identity
    if station.identity.system_append:
        parts.append(station.identity.system_append.strip())

    # Invariants as hard rules
    if station.invariants:
        parts.append("\n## Invariants (Non-Negotiable)")
        for inv in station.invariants:
            parts.append(f"- {inv}")

    # Scent trail (truncated to avoid bloat)
    if scent_trail:
        trail = scent_trail[:1500]  # Cap at 1500 chars
        if len(scent_trail) > 1500:
            trail += "\n... (truncated)"
        parts.append("\n## Lessons from Previous Runs")
        parts.append(trail)

    return "\n".join(parts)


def build_system_append_v2(
    station: StationSpec,
    scent_trail: Optional[str] = None,
    repo_root: Optional[Path] = None,
    policy_invariants_ref: Optional[List[str]] = None,
) -> str:
    """Build the v2 system prompt append with policy fragment loading.

    V2 enhancements over build_system_append:
    - Loads policy invariants from referenced fragment files
    - Includes station-specific invariants after global ones
    - Better structured output with clear sections

    Args:
        station: The station specification.
        scent_trail: Optional cross-run wisdom content.
        repo_root: Repository root for fragment loading.
        policy_invariants_ref: List of fragment paths for policy invariants.

    Returns:
        Combined system prompt append text.
    """
    parts: List[str] = []

    # 1. Station identity (who you are)
    if station.identity.system_append:
        parts.append(station.identity.system_append.strip())

    # 2. Load policy invariants from referenced fragments
    if policy_invariants_ref:
        fragment_content = load_fragments(
            policy_invariants_ref,
            repo_root,
            separator="\n\n",
        )
        if fragment_content:
            parts.append("\n## Policy Invariants (From Fragments)")
            parts.append(fragment_content)

    # 3. Station-specific invariants (always apply)
    if station.invariants:
        parts.append("\n## Station Invariants (Non-Negotiable)")
        for inv in station.invariants:
            parts.append(f"- {inv}")

    # 4. Scent trail (wisdom from previous runs, truncated)
    if scent_trail:
        trail = scent_trail[:1500]
        if len(scent_trail) > 1500:
            trail += "\n... (truncated)"
        parts.append("\n## Lessons from Previous Runs")
        parts.append(trail)

    return "\n".join(parts)


def build_user_prompt(
    station: StationSpec,
    step: FlowStep,
    context_pack: Optional["ContextPack"],
    run_base: Path,
    repo_root: Optional[Path] = None,
) -> str:
    """Build the user prompt from station template + context.

    Constructs a focused, bounded prompt:
    1. Fragments (shared rules, loaded and concatenated)
    2. Objective (from flow step)
    3. Context pointers (from ContextPack)
    4. Input/Output requirements
    5. Handoff instructions

    Args:
        station: The station specification.
        step: The flow step being executed.
        context_pack: Hydrated context with artifacts and envelopes.
        run_base: Run base directory.
        repo_root: Repository root for fragment loading.

    Returns:
        Complete user prompt text.
    """
    parts: List[str] = []

    # 1. Load and concatenate fragments
    if station.runtime_prompt.fragments:
        parts.append("## Guidelines\n")
        for frag_path in station.runtime_prompt.fragments:
            try:
                frag_content = load_fragment(frag_path, repo_root)
                parts.append(frag_content.strip())
                parts.append("")
            except FileNotFoundError:
                logger.warning("Fragment not found: %s", frag_path)

    # 2. Objective (from step)
    parts.append("## Objective\n")
    parts.append(step.objective)
    if step.scope:
        parts.append(f"\n**Scope:** {step.scope}")
    parts.append("")

    # 3. Context pointers (from ContextPack)
    if context_pack:
        if context_pack.upstream_artifacts:
            parts.append("## Available Artifacts\n")
            parts.append("Read these files for context:")
            for name, path in context_pack.upstream_artifacts.items():
                parts.append(f"- `{path}` ({name})")
            parts.append("")

        if context_pack.previous_envelopes:
            parts.append("## Previous Steps\n")
            for env in context_pack.previous_envelopes[-5:]:  # Last 5 envelopes
                status = env.status.upper() if env.status else "?"
                parts.append(f"- **{env.step_id}** [{status}]: {env.summary[:200] if env.summary else 'No summary'}")
            parts.append("")

    # 4. Input/Output requirements
    # Merge station IO with step-specific overrides
    required_inputs = list(station.io.required_inputs) + list(step.inputs)
    required_outputs = list(station.io.required_outputs) + list(step.outputs)

    if required_inputs:
        parts.append("## Required Inputs\n")
        parts.append("These artifacts must exist and be read:")
        for inp in required_inputs:
            parts.append(f"- `{inp}`")
        parts.append("")

    if required_outputs:
        parts.append("## Required Outputs\n")
        parts.append("You MUST produce these artifacts:")
        for out in required_outputs:
            parts.append(f"- `{out}`")
        parts.append("")

    # 5. Template rendering (if station has a template)
    if station.runtime_prompt.template:
        variables = {
            "step": {
                "id": step.id,
                "objective": step.objective,
                "scope": step.scope or "",
            },
            "station": {
                "id": station.id,
                "title": station.title,
            },
            "run": {
                "base": str(run_base),
            },
            "context": {
                "pointers": ", ".join(context_pack.upstream_artifacts.keys()) if context_pack else "",
            },
        }
        rendered = render_template(station.runtime_prompt.template, variables)
        parts.append(rendered)
        parts.append("")

    # 6. Handoff instructions (always appended)
    handoff_path = render_template(
        station.handoff.path_template,
        {"run": {"base": str(run_base)}, "step": {"id": step.id}},
    )
    parts.append("## Finalization (REQUIRED)\n")
    parts.append(f"When complete, write a handoff file to: `{handoff_path}`")
    parts.append("\nThe file MUST be valid JSON with these fields:")
    parts.append("```json")
    parts.append("{")
    for i, field in enumerate(station.handoff.required_fields):
        comma = "," if i < len(station.handoff.required_fields) - 1 else ""
        if field == "status":
            parts.append(f'  "status": "VERIFIED | UNVERIFIED | PARTIAL | BLOCKED"{comma}')
        elif field == "summary":
            parts.append(f'  "summary": "2-paragraph summary of work done"{comma}')
        elif field == "artifacts":
            parts.append(f'  "artifacts": {{"name": "relative/path"}}{comma}')
        elif field == "can_further_iteration_help":
            parts.append(f'  "can_further_iteration_help": "yes | no"{comma}')
        elif field == "proposed_next_step":
            parts.append(f'  "proposed_next_step": "step_id or null"{comma}')
        elif field == "confidence":
            parts.append(f'  "confidence": 0.0 to 1.0{comma}')
        elif field == "blockers":
            parts.append(f'  "blockers": ["blocker1", "blocker2"]{comma}')
    parts.append("}")
    parts.append("```")
    parts.append("\n**DO NOT** finish without writing this file.")

    return "\n".join(parts)


# =============================================================================
# SpecCompiler
# =============================================================================


def merge_verification_requirements(
    station: StationSpec,
    step: FlowStep,
    run_base: Path,
    variables: Dict[str, Any],
) -> VerificationRequirements:
    """Merge station and step verification requirements.

    Station provides defaults; step can override or extend.

    Args:
        station: Station specification with default verification.
        step: Step specification with potential overrides.
        run_base: Run base path for template resolution.
        variables: Template variables for path resolution.

    Returns:
        Merged VerificationRequirements with resolved paths.
    """
    # Collect required artifacts from station IO and step outputs
    artifacts: List[str] = []

    # Station required outputs become verification requirements
    for output_path in station.io.required_outputs:
        resolved = render_template(output_path, variables)
        artifacts.append(resolved)

    # Step outputs also become verification requirements
    for output_path in step.outputs:
        resolved = render_template(output_path, variables)
        if resolved not in artifacts:
            artifacts.append(resolved)

    # Verification commands from step sdk_overrides (if specified)
    commands: List[str] = []
    if step.sdk_overrides.get("verification_commands"):
        for cmd in step.sdk_overrides["verification_commands"]:
            commands.append(render_template(cmd, variables))

    return VerificationRequirements(
        required_artifacts=tuple(artifacts),
        verification_commands=tuple(commands),
    )


def resolve_handoff_contract(
    station: StationSpec,
    variables: Dict[str, Any],
) -> HandoffContract:
    """Resolve the handoff contract with template substitution.

    Args:
        station: Station specification with handoff template.
        variables: Template variables for path resolution.

    Returns:
        HandoffContract with resolved path.
    """
    resolved_path = render_template(station.handoff.path_template, variables)

    return HandoffContract(
        path=resolved_path,
        required_fields=station.handoff.required_fields,
    )


@dataclass
class CompileContext:
    """Context for prompt compilation."""
    flow: FlowSpec
    step: FlowStep
    station: StationSpec
    context_pack: Optional["ContextPack"]
    run_base: Path
    repo_root: Optional[Path]
    scent_trail: Optional[str] = None


class SpecCompiler:
    """Compiler that produces PromptPlans from specs.

    Usage:
        compiler = SpecCompiler(repo_root)
        plan = compiler.compile(flow_id, step_id, context_pack, run_base)
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize the spec compiler.

        Args:
            repo_root: Repository root path for loading specs.
        """
        self.repo_root = repo_root
        self._scent_trail: Optional[str] = None
        self._scent_trail_loaded = False

    def _load_scent_trail(self) -> Optional[str]:
        """Load the scent trail (wisdom from previous runs)."""
        if self._scent_trail_loaded:
            return self._scent_trail

        self._scent_trail_loaded = True

        if not self.repo_root:
            return None

        # Try multiple locations
        paths = [
            self.repo_root / ".runs" / "_wisdom" / "latest.md",
            self.repo_root / "swarm" / "runs" / "_wisdom" / "latest.md",
        ]

        for path in paths:
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        self._scent_trail = content
                        logger.debug("Loaded scent trail from %s", path)
                        return content
                except (OSError, IOError) as e:
                    logger.debug("Failed to read scent trail: %s", e)

        return None

    def compile(
        self,
        flow_id: str,
        step_id: str,
        context_pack: Optional["ContextPack"],
        run_base: Path,
        cwd: Optional[str] = None,
        policy_invariants_ref: Optional[List[str]] = None,
        use_v2: bool = True,
    ) -> PromptPlan:
        """Compile a PromptPlan for a flow step.

        V2 enhancements:
        - Includes verification requirements (merged from station + step)
        - Includes resolved handoff contract
        - Includes flow_key for routing
        - Supports policy invariants from fragment references
        - Full template resolution for paths

        Args:
            flow_id: Flow specification ID (e.g., "3-build").
            step_id: Step ID within the flow.
            context_pack: Hydrated context with artifacts and envelopes.
            run_base: Run base directory for outputs.
            cwd: Working directory for SDK. Defaults to repo_root.
            policy_invariants_ref: Fragment paths for policy invariants.
            use_v2: Use v2 system_append with policy loading (default True).

        Returns:
            Compiled PromptPlan ready for SDK execution.

        Raises:
            FileNotFoundError: If flow or station spec not found.
            ValueError: If step not found in flow.
        """
        # Load flow spec
        flow = load_flow(flow_id, self.repo_root)

        # Extract flow key for routing
        flow_key = extract_flow_key(flow_id)

        # Find step in flow
        step = None
        for s in flow.steps:
            if s.id == step_id:
                step = s
                break

        if not step:
            raise ValueError(f"Step {step_id} not found in flow {flow_id}")

        # Load station spec
        station = load_station(step.station, self.repo_root)

        # Load scent trail
        scent_trail = self._load_scent_trail()

        # Build template variables for path resolution
        variables = {
            "run": {
                "base": str(run_base),
            },
            "step": {
                "id": step.id,
                "objective": step.objective,
                "scope": step.scope or "",
            },
            "flow": {
                "id": flow.id,
                "key": flow_key,
                "version": str(flow.version),
            },
            "station": {
                "id": station.id,
                "title": station.title,
                "version": str(station.version),
            },
        }

        # Build system append (v1 or v2)
        if use_v2:
            # Default policy invariants if not specified
            if policy_invariants_ref is None:
                policy_invariants_ref = list(station.runtime_prompt.fragments)

            system_append = build_system_append_v2(
                station=station,
                scent_trail=scent_trail,
                repo_root=self.repo_root,
                policy_invariants_ref=policy_invariants_ref,
            )
        else:
            system_append = build_system_append(station, scent_trail)

        # Build user prompt
        user_prompt = build_user_prompt(
            station=station,
            step=step,
            context_pack=context_pack,
            run_base=run_base,
            repo_root=self.repo_root,
        )

        # Compute prompt hash for traceability (SHA256 of combined prompts)
        prompt_hash = hashlib.sha256(
            (system_append + user_prompt).encode("utf-8")
        ).hexdigest()[:16]

        # Merge SDK settings (station + step overrides)
        model = step.sdk_overrides.get("model", station.sdk.model)
        permission_mode = step.sdk_overrides.get("permission_mode", station.sdk.permission_mode)
        allowed_tools = tuple(step.sdk_overrides.get("allowed_tools", station.sdk.allowed_tools))
        max_turns = step.sdk_overrides.get("max_turns", station.sdk.max_turns)
        sandbox_enabled = step.sdk_overrides.get("sandbox_enabled", station.sdk.sandbox.enabled)

        # Determine cwd
        effective_cwd = cwd or (str(self.repo_root) if self.repo_root else str(Path.cwd()))

        # V2: Merge verification requirements from station and step
        verification = merge_verification_requirements(
            station=station,
            step=step,
            run_base=run_base,
            variables=variables,
        )

        # V2: Resolve handoff contract with template substitution
        handoff = resolve_handoff_contract(
            station=station,
            variables=variables,
        )

        return PromptPlan(
            # Traceability
            station_id=station.id,
            station_version=station.version,
            flow_id=flow.id,
            flow_version=flow.version,
            step_id=step.id,
            prompt_hash=prompt_hash,
            # SDK Options
            model=model,
            permission_mode=permission_mode,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            sandbox_enabled=sandbox_enabled,
            cwd=effective_cwd,
            # Prompt Content
            system_append=system_append,
            user_prompt=user_prompt,
            # Metadata
            compiled_at=datetime.now(timezone.utc).isoformat(),
            context_pack_size=len(context_pack.previous_envelopes) if context_pack else 0,
            # V2 additions
            verification=verification,
            handoff=handoff,
            flow_key=flow_key,
        )

    def compile_from_context(
        self,
        ctx: "StepContext",
        flow_id: str,
    ) -> PromptPlan:
        """Compile a PromptPlan from a StepContext.

        Convenience method for engine integration.

        Args:
            ctx: Step execution context.
            flow_id: Flow specification ID.

        Returns:
            Compiled PromptPlan.
        """
        context_pack = ctx.extra.get("context_pack") if ctx.extra else None
        return self.compile(
            flow_id=flow_id,
            step_id=ctx.step_id,
            context_pack=context_pack,
            run_base=ctx.run_base,
            cwd=str(ctx.repo_root) if ctx.repo_root else None,
        )


# =============================================================================
# Convenience Function
# =============================================================================


def compile_prompt(
    flow_id: str,
    step_id: str,
    context_pack: Optional["ContextPack"],
    run_base: Path,
    repo_root: Optional[Path] = None,
    cwd: Optional[str] = None,
    policy_invariants_ref: Optional[List[str]] = None,
    use_v2: bool = True,
) -> PromptPlan:
    """Compile a PromptPlan for a flow step (convenience function).

    V2 enhancements:
    - Includes verification requirements (merged from station + step)
    - Includes resolved handoff contract
    - Includes flow_key for routing
    - Supports policy invariants from fragment references

    Args:
        flow_id: Flow specification ID (e.g., "3-build").
        step_id: Step ID within the flow.
        context_pack: Hydrated context with artifacts and envelopes.
        run_base: Run base directory for outputs.
        repo_root: Repository root for loading specs.
        cwd: Working directory for SDK.
        policy_invariants_ref: Fragment paths for policy invariants.
        use_v2: Use v2 system_append with policy loading (default True).

    Returns:
        Compiled PromptPlan ready for SDK execution.
    """
    compiler = SpecCompiler(repo_root)
    return compiler.compile(
        flow_id=flow_id,
        step_id=step_id,
        context_pack=context_pack,
        run_base=run_base,
        cwd=cwd,
        policy_invariants_ref=policy_invariants_ref,
        use_v2=use_v2,
    )
