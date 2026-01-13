"""JSON Schema definitions for structured output.

This module contains the canonical JSON schemas used for structured output
in the Claude SDK integration. These schemas define the expected format for:

- HandoffEnvelope: Structured output for step completion handoffs
- RoutingSignal: Structured output for routing decisions between steps

These schemas are used with the SDK's output_format parameter for reliable
JSON extraction.
"""

from typing import Any, Dict

# =============================================================================
# Structured Output Schemas (for output_format)
# =============================================================================

# JSON Schema for HandoffEnvelope structured output
HANDOFF_ENVELOPE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "step_id": {
            "type": "string",
            "description": "The step ID that produced this envelope",
        },
        "flow_key": {
            "type": "string",
            "description": "The flow key (signal, plan, build, gate, deploy, wisdom)",
        },
        "run_id": {
            "type": "string",
            "description": "The run identifier",
        },
        "status": {
            "type": "string",
            "enum": ["VERIFIED", "UNVERIFIED", "PARTIAL", "BLOCKED"],
            "description": "Execution status: VERIFIED (complete), UNVERIFIED (tests fail or incomplete), PARTIAL (some work done but blocked), BLOCKED (cannot proceed)",
        },
        "summary": {
            "type": "string",
            "description": "2-paragraph summary of what was accomplished and any issues encountered (max 2000 chars)",
            "maxLength": 2000,
        },
        "artifacts": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Map of artifact names to relative paths from run base",
        },
        "file_changes": {
            "type": "object",
            "description": "Files created/modified/deleted during this step",
            "properties": {
                "created": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "modified": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "deleted": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "proposed_next_step": {
            "type": ["string", "null"],
            "description": "The step_id that should execute next, or null if flow should terminate",
        },
        "notes_for_next_step": {
            "type": "string",
            "description": "Context the next agent should know",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in this handoff (1.0 = very confident)",
        },
        "can_further_iteration_help": {
            "type": "string",
            "enum": ["yes", "no"],
            "description": "For microloops: can another iteration improve the result?",
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601 timestamp",
        },
    },
    "required": ["step_id", "flow_key", "run_id", "status", "summary", "confidence"],
}

# JSON Schema for RoutingSignal structured output
ROUTING_SIGNAL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["advance", "loop", "terminate", "branch"],
            "description": "Routing decision: advance (next step), loop (back to target), terminate (end flow), branch (conditional route)",
        },
        "next_step_id": {
            "type": ["string", "null"],
            "description": "The step_id to execute next (for advance/loop/branch)",
        },
        "route": {
            "type": ["string", "null"],
            "description": "Named route identifier for branch routing",
        },
        "reason": {
            "type": "string",
            "description": "Human-readable explanation for this decision (max 300 chars)",
            "maxLength": 300,
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in this routing decision",
        },
        "needs_human": {
            "type": "boolean",
            "description": "Whether human review is required before proceeding",
        },
        "factors_considered": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 50},
                    "impact": {
                        "type": "string",
                        "enum": [
                            "strongly_favors",
                            "favors",
                            "neutral",
                            "against",
                            "strongly_against",
                        ],
                    },
                    "evidence": {"type": "string", "maxLength": 100},
                    "weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
            "description": "Factors considered in the routing decision",
        },
        "risks_identified": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk": {"type": "string", "maxLength": 100},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "mitigation": {"type": "string", "maxLength": 100},
                },
            },
            "description": "Risks identified during routing analysis",
        },
    },
    "required": ["decision", "reason", "confidence", "needs_human"],
}
