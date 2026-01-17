"""
Shared dataclasses and helpers for spec compilation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from swarm.spec.types import VerificationRequirements

# Compiler version for traceability
COMPILER_VERSION = "1.0.0"


@dataclass(frozen=True)
class SystemPromptSpec:
    """Compiled system prompt specification."""
    preset: str  # "default", "claude_code", "minimal", "custom"
    preset_content: str  # Resolved preset content
    append: str  # Station identity + invariants
    combined: str  # Final combined system prompt
    invariants: Tuple[str, ...]  # Explicit invariants
    tone: str  # "neutral", "analytical", "critical", "supportive"
    scent_trail: str  # Wisdom from previous runs


@dataclass(frozen=True)
class UserPromptSpec:
    """Compiled user prompt specification."""
    objective: str  # Primary objective
    scope: str  # Scope constraint
    context_section: str  # Compiled context pointers
    guidelines: str  # Compiled guidelines from fragments
    finalization_instructions: str  # Handoff file instructions
    combined: str  # Final combined user prompt


@dataclass(frozen=True)
class OutputFormatSpec:
    """Output format specification for handoff envelope."""
    handoff_path: str  # Resolved path
    schema_ref: str  # Path to JSON schema
    required_fields: Tuple[str, ...]  # Required envelope fields
    status_values: Tuple[str, ...]  # Valid status values
    example: Dict[str, Any]  # Example envelope


@dataclass(frozen=True)
class SdkOptionsSpec:
    """SDK options for Claude execution."""
    model: str  # Full model ID
    model_tier: str  # Shorthand tier
    permission_mode: str  # "default", "bypassPermissions", "planMode"
    allowed_tools: Tuple[str, ...]  # Explicit tool list
    denied_tools: Tuple[str, ...]  # Denied tools
    tool_profile: str  # Tool profile name
    max_turns: int  # Maximum conversation turns
    sandbox_enabled: bool  # Sandbox mode
    cwd: str  # Working directory


@dataclass(frozen=True)
class TraceabilitySpec:
    """Traceability metadata for audit trail."""
    station_id: str
    station_version: int
    template_id: str  # Optional template reference
    template_version: int
    flow_id: str
    flow_version: int
    flow_key: str
    step_id: str
    prompt_hash: str  # SHA-256 truncated
    compiled_at: str  # ISO timestamp
    compiler_version: str
    run_id: str  # Optional run correlation
    iteration: int  # Microloop iteration


@dataclass(frozen=True)
class FragmentReference:
    """Reference to a loaded fragment for audit."""
    path: str
    hash: str  # Content hash
    version: str  # Optional version


@dataclass(frozen=True)
class VerificationCommand:
    """Command for post-execution verification."""
    command: str
    success_pattern: str
    timeout_seconds: int
    description: str


@dataclass(frozen=True)
class VerificationSpec:
    """Post-execution verification requirements."""
    required_artifacts: Tuple[str, ...]
    verification_commands: Tuple[VerificationCommand, ...]
    gate_status_on_fail: str  # "UNVERIFIED" or "BLOCKED"


@dataclass(frozen=True)
class StepPlan:
    """Compiled plan for a single step, ready for SDK execution."""
    step_id: str
    station_id: str
    system_prompt: str  # Combined system prompt
    user_prompt: str  # Combined user prompt
    allowed_tools: Tuple[str, ...]
    permission_mode: str
    max_turns: int
    output_schema: Dict[str, Any]  # JSON schema for structured output
    prompt_hash: str  # Deterministic hash for reproducibility
    prompt_hash_v2: str  # Deterministic hash for full prompt content

    # Extended fields for full schema compliance
    system_append: str = ""
    model: str = "sonnet"
    model_tier: str = "sonnet"
    sandbox_enabled: bool = True
    cwd: str = ""
    station_version: int = 1
    flow_id: str = ""
    flow_version: int = 1
    flow_key: str = ""
    compiled_at: str = ""
    compiler_version: str = COMPILER_VERSION
    handoff_path: str = ""
    required_fields: Tuple[str, ...] = ("status", "summary", "artifacts")
    verification: VerificationRequirements = field(
        default_factory=lambda: VerificationRequirements()
    )
    fragments_used: Tuple[FragmentReference, ...] = ()
    template_id: str = ""
    template_version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching prompt_plan.schema.json."""
        traceability = {
            "station_id": self.station_id,
            "station_version": self.station_version,
            "flow_id": self.flow_id,
            "flow_version": self.flow_version,
            "flow_key": self.flow_key,
            "step_id": self.step_id,
            "prompt_hash": self.prompt_hash,
            "compiled_at": self.compiled_at,
            "compiler_version": self.compiler_version,
        }
        if self.prompt_hash_v2:
            traceability["prompt_hash_v2"] = self.prompt_hash_v2
        if self.template_id:
            traceability["template_id"] = self.template_id
            traceability["template_version"] = self.template_version

        return {
            "system_prompt": {
                "preset": "claude_code",
                "append": self.system_append,
                "combined": self.system_prompt,
                "invariants": [],
                "tone": "neutral",
            },
            "user_prompt": {
                "objective": "",
                "combined": self.user_prompt,
            },
            "output_format": {
                "handoff_path": self.handoff_path,
                "required_fields": list(self.required_fields),
                "schema_ref": "handoff_envelope.schema.json",
            },
            "sdk_options": {
                "model": self.model,
                "model_tier": self.model_tier,
                "permission_mode": self.permission_mode,
                "tools": {
                    "allowed": list(self.allowed_tools),
                },
                "max_turns": self.max_turns,
                "sandbox": {
                    "enabled": self.sandbox_enabled,
                },
                "cwd": self.cwd,
            },
            "traceability": traceability,
            "fragments_used": [
                {"path": f.path, "hash": f.hash, "version": f.version}
                for f in self.fragments_used
            ],
            "verification": {
                "required_artifacts": list(self.verification.required_artifacts),
                "verification_commands": list(self.verification.verification_commands),
            },
        }


@dataclass
class CompileContext:
    """Context for compilation including run information."""
    run_id: str = ""
    run_base: Path = field(default_factory=lambda: Path("swarm/runs/default"))
    repo_root: Optional[Path] = None
    cwd: Optional[str] = None
    iteration: int = 1
    context_pack: Optional[Any] = None
    scent_trail: str = ""


@dataclass(frozen=True)
class StepIntent:
    """Source-agnostic intent for a single step."""
    flow_id: str
    flow_key: str
    step_id: str
    station_id: str
    objective: str
    scope: Optional[str]
    required_inputs: Tuple[str, ...]
    required_outputs: Tuple[str, ...]
    handoff_path_template: str
    required_fields: Tuple[str, ...]
    sdk_overrides: Dict[str, Any]
    verification_overrides: Dict[str, Any]
    params: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None
    template_version: Optional[int] = None
    flow_version: int = 1


@dataclass(frozen=True)
class FlowTemplateVars:
    """Template variables for flow info, with string fallback to flow key."""
    id: str
    key: str
    version: str

    def __str__(self) -> str:
        return self.key


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """Dedupe items while preserving first-seen order."""
    seen: set = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
