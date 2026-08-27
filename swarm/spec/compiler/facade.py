"""
Facade compiler that owns the canonical SpecCompiler implementation.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from swarm.spec.loader import load_flow, load_station
from swarm.spec.types import (
    FlowSpec,
    FlowStep,
    HandoffContract,
    PromptPlan,
    StationSpec,
)

from .builder import StepPlanBuilder
from .intent_adapters import intent_from_flow_node, intent_from_flow_step
from .models import CompileContext, StepIntent, StepPlan

if TYPE_CHECKING:
    from swarm.runtime.context_pack import ContextPack
    from swarm.runtime.engines.models import StepContext

logger = logging.getLogger(__name__)


# =============================================================================
# FlowGraph Node Types (per flow_graph.schema.json)
# =============================================================================


@dataclass
class FlowNode:
    """A node in the FlowGraph (from flow_graph.schema.json)."""

    node_id: str
    template_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)
    ui: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepTemplate:
    """A step template (from step_template.schema.json)."""

    id: str
    version: int
    title: str
    station_id: str
    objective: Dict[str, Any]  # ParameterizedObjective
    io_overrides: Dict[str, Any] = field(default_factory=dict)
    routing_defaults: Dict[str, Any] = field(default_factory=dict)
    ui_defaults: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    category: str = "implementation"
    deprecated: bool = False


# =============================================================================
# Flow Key Extraction
# =============================================================================


def extract_flow_key(flow_id: str) -> str:
    """Extract the flow key from a flow ID."""
    if "-" in flow_id:
        parts = flow_id.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return parts[1]
    return flow_id


# =============================================================================
# SpecCompiler
# =============================================================================


class SpecCompiler:
    """Compiler that produces PromptPlans from specs."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize the spec compiler."""
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
                except (OSError, IOError) as exc:
                    logger.debug("Failed to read scent trail: %s", exc)

        return None

    def _intent_from_flow_step(
        self,
        flow: FlowSpec,
        step: FlowStep,
        station: StationSpec,
        flow_key: str,
    ) -> StepIntent:
        """Adapt a FlowSpec step into a StepIntent."""
        return intent_from_flow_step(flow, step, station, flow_key)

    def _intent_from_flow_node(
        self,
        node: FlowNode,
        template: Optional[StepTemplate],
        station: StationSpec,
        context: CompileContext,
    ) -> StepIntent:
        """Adapt a FlowGraph node into a StepIntent."""
        return intent_from_flow_node(node, template, station, context)

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
        """Compile a PromptPlan for a flow step."""
        flow = load_flow(flow_id, self.repo_root)
        flow_key = extract_flow_key(flow_id)

        step = next((s for s in flow.steps if s.id == step_id), None)
        if not step:
            raise ValueError(f"Step {step_id} not found in flow {flow_id}")

        station = load_station(step.station, self.repo_root)
        scent_trail = self._load_scent_trail()

        intent = self._intent_from_flow_step(flow, step, station, flow_key)
        context = CompileContext(
            run_base=run_base,
            repo_root=self.repo_root,
            cwd=cwd,
            context_pack=context_pack,
            scent_trail=scent_trail or "",
        )

        builder = StepPlanBuilder(self.repo_root)
        step_plan = builder.build(
            intent=intent,
            station=station,
            context=context,
            policy_invariants_ref=policy_invariants_ref,
            use_v2=use_v2,
            cwd=cwd,
        )

        handoff = HandoffContract(
            path=step_plan.handoff_path,
            required_fields=step_plan.required_fields,
        )

        return PromptPlan(
            station_id=station.id,
            station_version=station.version,
            flow_id=flow.id,
            flow_version=flow.version,
            step_id=step.id,
            prompt_hash=step_plan.prompt_hash,
            prompt_hash_v2=step_plan.prompt_hash_v2,
            model=step_plan.model,
            permission_mode=step_plan.permission_mode,
            allowed_tools=step_plan.allowed_tools,
            max_turns=step_plan.max_turns,
            sandbox_enabled=step_plan.sandbox_enabled,
            cwd=step_plan.cwd,
            system_append=step_plan.system_append,
            user_prompt=step_plan.user_prompt,
            compiled_at=step_plan.compiled_at,
            context_pack_size=len(context_pack.previous_envelopes) if context_pack else 0,
            output_schema=step_plan.output_schema,
            verification=step_plan.verification,
            handoff=handoff,
            flow_key=flow_key,
            fragment_manifest=tuple(f.path for f in step_plan.fragments_used),
        )

    def compile_from_context(
        self,
        ctx: "StepContext",
        flow_id: str,
    ) -> PromptPlan:
        """Compile a PromptPlan from a StepContext."""
        context_pack = ctx.extra.get("context_pack") if ctx.extra else None
        return self.compile(
            flow_id=flow_id,
            step_id=ctx.step_id,
            context_pack=context_pack,
            run_base=ctx.run_base,
            cwd=str(ctx.repo_root) if ctx.repo_root else None,
        )

    # =========================================================================
    # FlowGraph Compilation Methods
    # =========================================================================

    def compile_step(
        self,
        node: FlowNode,
        template: Optional[StepTemplate],
        context: CompileContext,
    ) -> StepPlan:
        """Compile a single FlowNode into a StepPlan."""
        station_id = self._resolve_station_id(node, template)
        station = load_station(station_id, context.repo_root)

        intent = self._intent_from_flow_node(
            node=node,
            template=template,
            station=station,
            context=context,
        )

        builder = StepPlanBuilder(context.repo_root)
        return builder.build(
            intent=intent,
            station=station,
            context=context,
            use_v2=True,
            cwd=context.cwd,
        )

    def resolve_template(
        self,
        node: FlowNode,
        template_registry: Optional[Dict[str, StepTemplate]] = None,
    ) -> Optional[StepTemplate]:
        """Resolve the StepTemplate for a FlowNode."""
        if not node.template_id:
            return None

        if template_registry and node.template_id in template_registry:
            return template_registry[node.template_id]

        return self._load_template(node.template_id)

    @lru_cache(maxsize=32)
    def _load_template(self, template_id: str) -> Optional[StepTemplate]:
        """Load a StepTemplate from disk."""
        if not self.repo_root:
            return None

        template_path = self.repo_root / "swarm" / "spec" / "templates" / f"{template_id}.yaml"

        if not template_path.exists():
            logger.debug("Template not found: %s", template_path)
            return None

        try:
            from swarm.utils.yaml_utils import load_yaml

            with open(template_path, "r", encoding="utf-8") as handle:
                data = load_yaml(handle)

            return StepTemplate(
                id=data.get("id", template_id),
                version=data.get("version", 1),
                title=data.get("title", template_id),
                station_id=data.get("station_id", ""),
                objective=data.get("objective", {}),
                io_overrides=data.get("io_overrides", {}),
                routing_defaults=data.get("routing_defaults", {}),
                ui_defaults=data.get("ui_defaults", {}),
                constraints=data.get("constraints", {}),
                parameters=data.get("parameters", {}),
                tags=data.get("tags", []),
                category=data.get("category", "implementation"),
                deprecated=data.get("deprecated", False),
            )
        except Exception as exc:
            logger.warning("Failed to load template %s: %s", template_id, exc)
            return None

    def _resolve_station_id(
        self,
        node: FlowNode,
        template: Optional[StepTemplate],
    ) -> str:
        """Resolve the station ID from node or template."""
        if "station_id" in node.overrides:
            return node.overrides["station_id"]
        if template:
            return template.station_id
        return node.node_id

    # =========================================================================
    # Multi-Step Compilation
    # =========================================================================

    def compile_flow(
        self,
        flow_id: str,
        context: CompileContext,
    ) -> "MultiStepPromptPlan":
        """Compile a complete flow into a MultiStepPromptPlan."""
        flow = load_flow(flow_id, context.repo_root)
        flow_key = extract_flow_key(flow_id)

        step_plans: List[StepPlan] = []
        spec_hashes: List[str] = []

        for step in flow.steps:
            station = load_station(step.station, context.repo_root)
            step_plan = self._compile_flow_step(
                flow=flow,
                step=step,
                station=station,
                context=context,
                flow_key=flow_key,
            )

            step_plans.append(step_plan)
            spec_hashes.append(step_plan.prompt_hash)

        spec_hash = hashlib.sha256("".join(spec_hashes).encode()).hexdigest()[:16]

        return MultiStepPromptPlan(
            flow_id=flow_id,
            steps=step_plans,
            spec_hash=spec_hash,
            compiled_at=datetime.now(timezone.utc).isoformat(),
        )

    def _compile_flow_step(
        self,
        flow: FlowSpec,
        step: FlowStep,
        station: StationSpec,
        context: CompileContext,
        flow_key: str,
    ) -> StepPlan:
        """Compile a single FlowStep into a StepPlan."""
        intent = self._intent_from_flow_step(flow, step, station, flow_key)
        builder = StepPlanBuilder(context.repo_root)
        return builder.build(
            intent=intent,
            station=station,
            context=context,
            use_v2=True,
            cwd=context.cwd,
        )


@dataclass(frozen=True)
class MultiStepPromptPlan:
    """Compiled plan for a complete flow with multiple steps."""

    flow_id: str
    steps: List[StepPlan]
    spec_hash: str
    compiled_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "flow_id": self.flow_id,
            "steps": [s.to_dict() for s in self.steps],
            "spec_hash": self.spec_hash,
            "compiled_at": self.compiled_at,
        }
