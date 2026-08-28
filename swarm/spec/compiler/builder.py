"""
StepPlanBuilder implementation for compiling intents into step plans.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from swarm.config.model_registry import resolve_station_model
from swarm.config.tool_profiles import resolve_tool_profile

from ..loader import load_fragment
from ..types import StationSpec, VerificationRequirements
from .models import (
    COMPILER_VERSION,
    CompileContext,
    FlowTemplateVars,
    FragmentReference,
    StepIntent,
    StepPlan,
    _dedupe_preserve_order,
)
from .prompt_parts import (
    SYSTEM_PRESETS,
    build_system_append,
    build_system_append_v2,
    render_template,
)

logger = logging.getLogger(__name__)


class StepPlanBuilder:
    """Build a StepPlan from a StepIntent and compile context."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root

    def _resolve_cwd(self, *, cwd: Optional[str], context: CompileContext) -> str:
        """Resolve the effective working directory with consistent precedence."""
        if cwd is not None and str(cwd).strip():
            return str(cwd)
        if context.cwd and str(context.cwd).strip():
            return str(context.cwd)
        if context.repo_root:
            return str(context.repo_root)
        return str(Path.cwd())

    def build(
        self,
        intent: StepIntent,
        station: StationSpec,
        context: CompileContext,
        policy_invariants_ref: Optional[List[str]] = None,
        use_v2: bool = True,
        cwd: Optional[str] = None,
    ) -> StepPlan:
        """Build a StepPlan for the given intent and station."""
        upstream_artifacts, previous_envelopes = self._extract_context(context.context_pack)
        variables = self._build_variables(
            intent=intent,
            station=station,
            context=context,
            upstream_artifacts=upstream_artifacts,
        )

        system_append = self._build_system_append(
            station=station,
            scent_trail=context.scent_trail,
            policy_invariants_ref=policy_invariants_ref,
            use_v2=use_v2,
        )
        system_prompt = self._build_system_prompt(station, system_append)
        user_prompt = self._build_user_prompt(
            intent=intent,
            station=station,
            variables=variables,
            upstream_artifacts=upstream_artifacts,
            previous_envelopes=previous_envelopes,
        )

        system_prompt, system_includes = self._process_fragment_includes(system_prompt)
        user_prompt, user_includes = self._process_fragment_includes(user_prompt)

        # Audit manifest: station-declared fragments, policy invariants, and any
        # inline {{fragment:...}} includes that actually resolved. Order is
        # declaration-first so the manifest reads the way the prompt is built.
        fragment_paths = list(station.runtime_prompt.fragments)
        if policy_invariants_ref:
            fragment_paths.extend(policy_invariants_ref)
        fragment_paths.extend(system_includes)
        fragment_paths.extend(user_includes)
        fragment_paths = _dedupe_preserve_order(fragment_paths)
        fragments_used = self._collect_fragment_references(fragment_paths)

        prompt_hash = self._compute_prompt_hash(system_append, user_prompt)
        prompt_hash_v2 = self._compute_prompt_hash_v2(system_prompt, user_prompt)
        output_schema = self._build_output_schema(station)
        handoff_path = render_template(intent.handoff_path_template, variables)
        verification = self._build_verification(intent, variables)
        sdk_options = self._merge_sdk_options(station, intent.sdk_overrides)
        effective_cwd = self._resolve_cwd(cwd=cwd, context=context)

        return StepPlan(
            step_id=intent.step_id,
            station_id=station.id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allowed_tools=sdk_options["allowed_tools"],
            permission_mode=sdk_options["permission_mode"],
            max_turns=sdk_options["max_turns"],
            output_schema=output_schema,
            prompt_hash=prompt_hash,
            prompt_hash_v2=prompt_hash_v2,
            system_append=system_append,
            model=sdk_options["model"],
            model_tier=sdk_options["model_tier"],
            sandbox_enabled=sdk_options["sandbox_enabled"],
            cwd=effective_cwd,
            station_version=station.version,
            flow_id=intent.flow_id,
            flow_version=intent.flow_version,
            flow_key=intent.flow_key,
            compiled_at=datetime.now(timezone.utc).isoformat(),
            compiler_version=COMPILER_VERSION,
            handoff_path=handoff_path,
            required_fields=intent.required_fields,
            verification=verification,
            fragments_used=tuple(fragments_used),
            template_id=intent.template_id or "",
            template_version=intent.template_version or 0,
        )

    def _extract_context(
        self,
        context_pack: Optional[Any],
    ) -> Tuple[Dict[str, Any], List[Any]]:
        """Normalize context pack inputs for prompt assembly."""
        if not context_pack:
            return {}, []

        if hasattr(context_pack, "upstream_artifacts"):
            upstream = context_pack.upstream_artifacts or {}
            previous = context_pack.previous_envelopes or []
            return upstream, previous

        if isinstance(context_pack, dict):
            upstream = context_pack.get("upstream_artifacts", {}) or {}
            previous = context_pack.get("previous_envelopes", []) or []
            return upstream, previous

        return {}, []

    def _infer_run_id(self, run_base: Path, flow_key: str) -> str:
        """Infer run_id from run_base when not provided."""
        if flow_key and run_base.name == flow_key:
            return run_base.parent.name
        return run_base.name

    def _build_variables(
        self,
        intent: StepIntent,
        station: StationSpec,
        context: CompileContext,
        upstream_artifacts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build template variables for substitution."""
        run_id = context.run_id or self._infer_run_id(context.run_base, intent.flow_key)
        context_pointers = ", ".join(str(k) for k in upstream_artifacts.keys())
        flow_vars = FlowTemplateVars(
            id=intent.flow_id,
            key=intent.flow_key,
            version=str(intent.flow_version),
        )

        return {
            "run": {
                "base": str(context.run_base),
                "id": run_id,
            },
            "step": {
                "id": intent.step_id,
                "objective": intent.objective,
                "scope": intent.scope or "",
            },
            "station": {
                "id": station.id,
                "title": station.title,
                "version": str(station.version),
            },
            "flow": flow_vars,
            "params": intent.params,
            "context": {
                "pointers": context_pointers,
            },
        }

    def _build_system_append(
        self,
        station: StationSpec,
        scent_trail: Optional[str],
        policy_invariants_ref: Optional[List[str]],
        use_v2: bool,
    ) -> str:
        """Build system append content for station identity + invariants."""
        if use_v2:
            if policy_invariants_ref is None:
                policy_invariants_ref = list(station.runtime_prompt.fragments)
            return build_system_append_v2(
                station=station,
                scent_trail=scent_trail,
                repo_root=self.repo_root,
                policy_invariants_ref=policy_invariants_ref,
            )
        return build_system_append(station, scent_trail)

    def _build_system_prompt(self, station: StationSpec, system_append: str) -> str:
        """Combine system preset with station append."""
        preset = getattr(station.identity, "preset", "default")
        preset_content = ""
        if preset == "custom":
            preset_content = getattr(station.identity, "preset_content", "")
        elif preset in SYSTEM_PRESETS:
            preset_content = SYSTEM_PRESETS[preset]

        parts: List[str] = []
        if preset_content:
            parts.append(preset_content)
        if system_append:
            parts.append(system_append)
        return "\n".join(parts)

    def _build_user_prompt(
        self,
        intent: StepIntent,
        station: StationSpec,
        variables: Dict[str, Any],
        upstream_artifacts: Dict[str, Any],
        previous_envelopes: List[Any],
    ) -> str:
        """Build the user prompt from intent and station runtime prompt."""
        parts: List[str] = []

        if station.runtime_prompt.fragments:
            parts.append("## Guidelines\n")
            for frag_path in station.runtime_prompt.fragments:
                try:
                    frag_content = load_fragment(frag_path, self.repo_root)
                    parts.append(frag_content.strip())
                    parts.append("")
                except FileNotFoundError:
                    logger.warning("Fragment not found: %s", frag_path)

        parts.append("## Objective\n")
        objective = intent.objective
        if "{{" in objective:
            objective = render_template(objective, variables)
        parts.append(objective)
        if intent.scope:
            scope = intent.scope
            if "{{" in scope:
                scope = render_template(scope, variables)
            parts.append(f"\n**Scope:** {scope}")
        parts.append("")

        if upstream_artifacts:
            parts.append("## Available Artifacts\n")
            parts.append("Read these files for context:")
            for name, path in upstream_artifacts.items():
                parts.append(f"- `{path}` ({name})")
            parts.append("")

        if previous_envelopes:
            parts.append("## Previous Steps\n")
            for env in previous_envelopes[-5:]:
                if hasattr(env, "status"):
                    status = env.status.upper() if env.status else "?"
                    summary = env.summary[:200] if env.summary else "No summary"
                    step_id = env.step_id
                else:
                    status_val = env.get("status") if isinstance(env, dict) else None
                    status = status_val.upper() if status_val else "?"
                    summary_val = env.get("summary") if isinstance(env, dict) else None
                    summary = summary_val[:200] if summary_val else "No summary"
                    step_id = env.get("step_id") if isinstance(env, dict) else "unknown"
                parts.append(f"- **{step_id}** [{status}]: {summary}")
            parts.append("")

        if intent.required_inputs:
            parts.append("## Required Inputs\n")
            parts.append("These artifacts must exist and be read:")
            for inp in intent.required_inputs:
                resolved = render_template(inp, variables)
                parts.append(f"- `{resolved}`")
            parts.append("")

        if intent.required_outputs:
            parts.append("## Required Outputs\n")
            parts.append("You MUST produce these artifacts:")
            for out in intent.required_outputs:
                resolved = render_template(out, variables)
                parts.append(f"- `{resolved}`")
            parts.append("")

        if station.runtime_prompt.template:
            rendered = render_template(station.runtime_prompt.template, variables)
            parts.append(rendered)
            parts.append("")

        handoff_path = render_template(intent.handoff_path_template, variables)
        parts.append("## Finalization (REQUIRED)\n")
        parts.append(f"When complete, write a handoff file to: `{handoff_path}`")
        parts.append("\nThe file MUST be valid JSON with these fields:")
        parts.append("```json")
        parts.append("{")
        for i, field in enumerate(intent.required_fields):
            comma = "," if i < len(intent.required_fields) - 1 else ""
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

    def _build_output_schema(self, station: StationSpec) -> Dict[str, Any]:
        """Build JSON schema for structured output."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": list(station.handoff.required_fields),
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["VERIFIED", "UNVERIFIED", "PARTIAL", "BLOCKED"],
                },
                "summary": {"type": "string"},
                "artifacts": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "can_further_iteration_help": {
                    "type": "string",
                    "enum": ["yes", "no"],
                },
                "proposed_next_step": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "blockers": {"type": "array", "items": {"type": "string"}},
            },
        }

    def _build_verification(
        self,
        intent: StepIntent,
        variables: Dict[str, Any],
    ) -> VerificationRequirements:
        """Build verification requirements from intent."""
        artifacts: List[str] = []

        for output_path in intent.required_outputs:
            resolved = render_template(output_path, variables)
            if resolved not in artifacts:
                artifacts.append(resolved)

        for artifact in intent.verification_overrides.get("required_artifacts", []):
            resolved = render_template(artifact, variables)
            if resolved not in artifacts:
                artifacts.append(resolved)

        commands: List[str] = []
        for cmd in intent.verification_overrides.get("verification_commands", []):
            commands.append(render_template(cmd, variables))

        return VerificationRequirements(
            required_artifacts=tuple(artifacts),
            verification_commands=tuple(commands),
        )

    def _merge_sdk_options(
        self,
        station: StationSpec,
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge SDK options from station with overrides."""
        sdk = station.sdk
        category = station.category.value

        raw_model = overrides.get("model", sdk.model)
        resolved_model = resolve_station_model(raw_model, category=category)

        raw_allowed_tools = overrides.get("allowed_tools", sdk.allowed_tools)
        if isinstance(raw_allowed_tools, str):
            resolved_tools = resolve_tool_profile(raw_allowed_tools, category=category)
        elif raw_allowed_tools:
            resolved_tools = tuple(raw_allowed_tools)
        else:
            resolved_tools = resolve_tool_profile("inherit", category=category)

        return {
            "model": resolved_model,
            "model_tier": raw_model,
            "permission_mode": overrides.get("permission_mode", sdk.permission_mode),
            "allowed_tools": resolved_tools,
            "max_turns": overrides.get("max_turns", sdk.max_turns),
            "sandbox_enabled": overrides.get("sandbox_enabled", sdk.sandbox.enabled),
        }

    def _process_fragment_includes(self, content: str) -> Tuple[str, List[str]]:
        """Resolve {{fragment:...}} includes in prompt content.

        Returns:
            Tuple of (rendered content, fragment paths that were successfully
            resolved). The resolved paths feed the audit manifest so a receipt
            records inline includes, not just station-declared fragments.
        """
        pattern = r"\{\{fragment:([^}]+)\}\}"
        resolved: List[str] = []

        def replace_fragment(match: re.Match) -> str:
            frag_path = match.group(1).strip()
            if not frag_path.endswith(".md"):
                frag_path = f"{frag_path}.md"
            try:
                rendered = load_fragment(frag_path, self.repo_root)
            except FileNotFoundError:
                logger.warning("Fragment include not found: %s", frag_path)
                return f"[Fragment not found: {frag_path}]"
            resolved.append(frag_path)
            return rendered

        return re.sub(pattern, replace_fragment, content), resolved

    def _collect_fragment_references(
        self,
        fragment_paths: Iterable[str],
    ) -> List[FragmentReference]:
        """Collect fragment references for audit trail."""
        refs: List[FragmentReference] = []

        for frag_path in fragment_paths:
            try:
                content = load_fragment(frag_path, self.repo_root)
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
                refs.append(
                    FragmentReference(
                        path=frag_path,
                        hash=content_hash,
                        version="",
                    )
                )
            except FileNotFoundError:
                logger.warning("Fragment not found for audit: %s", frag_path)

        return refs

    def _compute_prompt_hash(self, system_append: str, user_prompt: str) -> str:
        """Compute deterministic hash for system append + user prompt."""
        combined = system_append + user_prompt
        full_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return full_hash[:16]

    def _compute_prompt_hash_v2(self, system_prompt: str, user_prompt: str) -> str:
        """Compute deterministic hash for the full system + user prompt."""
        combined = system_prompt + "\n---\n" + user_prompt
        full_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return full_hash[:16]
