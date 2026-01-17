"""
Compiler package shim to preserve swarm.spec.compiler imports.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

_LAZY_ATTRS: Dict[str, str] = {
    # compiler_legacy exports
    "CLAUDE_CODE_PRESET": "swarm.spec.compiler.prompt_parts",
    "SYSTEM_PRESETS": "swarm.spec.compiler.prompt_parts",
    "TOOL_PROFILES": "swarm.spec.compiler_legacy",
    "ExpandedTemplate": "swarm.spec.compiler_legacy",
    "FlowNode": "swarm.spec.compiler_legacy",
    "MultiStepPromptPlan": "swarm.spec.compiler_legacy",
    "SpecCompiler": "swarm.spec.compiler_legacy",
    "StepTemplate": "swarm.spec.compiler_legacy",
    "TemplateMetadata": "swarm.spec.compiler_legacy",
    "build_system_append": "swarm.spec.compiler.prompt_parts",
    "build_system_append_v2": "swarm.spec.compiler.prompt_parts",
    "build_user_prompt": "swarm.spec.compiler_legacy",
    "compile_prompt": "swarm.spec.compiler_legacy",
    "expand_flow_graph": "swarm.spec.compiler_legacy",
    "expand_template": "swarm.spec.compiler_legacy",
    "extract_flow_key": "swarm.spec.compiler_legacy",
    "get_template_categories": "swarm.spec.compiler_legacy",
    "list_templates": "swarm.spec.compiler_legacy",
    "load_template": "swarm.spec.compiler_legacy",
    "merge_verification_requirements": "swarm.spec.compiler_legacy",
    "render_template": "swarm.spec.compiler.prompt_parts",
    "resolve_handoff_contract": "swarm.spec.compiler_legacy",
    # models exports
    "COMPILER_VERSION": "swarm.spec.compiler.models",
    "CompileContext": "swarm.spec.compiler.models",
    "FlowTemplateVars": "swarm.spec.compiler.models",
    "FragmentReference": "swarm.spec.compiler.models",
    "OutputFormatSpec": "swarm.spec.compiler.models",
    "SdkOptionsSpec": "swarm.spec.compiler.models",
    "StepIntent": "swarm.spec.compiler.models",
    "StepPlan": "swarm.spec.compiler.models",
    "SystemPromptSpec": "swarm.spec.compiler.models",
    "TraceabilitySpec": "swarm.spec.compiler.models",
    "UserPromptSpec": "swarm.spec.compiler.models",
    "VerificationCommand": "swarm.spec.compiler.models",
    "VerificationSpec": "swarm.spec.compiler.models",
    "_dedupe_preserve_order": "swarm.spec.compiler.models",
    # builder exports
    "StepPlanBuilder": "swarm.spec.compiler.builder",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY_ATTRS.get(name)
    if not module_name:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_ATTRS.keys()))


__all__ = sorted(_LAZY_ATTRS.keys())
