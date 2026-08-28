#!/usr/bin/env python3
"""
gen_flows.py - Generate flow diagrams + step tables from config.

Config:
  - Flows:  swarm/config/flows/*.yaml
  - Agents: swarm/config/agents/*.yaml

Docs:
  - Flow docs: swarm/flows/flow-<key>.md

This script updates or checks a single auto-generated section in each
flow doc, bounded by:

    <!-- FLOW AUTOGEN START -->
    ...
    <!-- FLOW AUTOGEN END -->

Usage (from repo root):

    # Regenerate all flows
    uv run swarm/tools/gen_flows.py

    # Check all flows are up-to-date (CI)
    uv run swarm/tools/gen_flows.py --check

    # Only process a single flow key (e.g., 'deploy')
    uv run swarm/tools/gen_flows.py --flow deploy

"""

from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.utils.yaml_utils import load_yaml  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_CONFIG_DIR = REPO_ROOT / "swarm" / "config" / "agents"
FLOW_CONFIG_DIR = REPO_ROOT / "swarm" / "config" / "flows"
FLOW_DOC_DIR = REPO_ROOT / "swarm" / "flows"

AUTOGEN_START = "<!-- FLOW AUTOGEN START -->"
AUTOGEN_END = "<!-- FLOW AUTOGEN END -->"


# ---------------------------------------------------------------------------
# Simple IR
# ---------------------------------------------------------------------------


@dataclass
class Agent:
    key: str
    category: str
    color: str
    model: str
    short_role: str


@dataclass
class FlowStep:
    id: str
    title: str
    role: str
    agents: List[str]


@dataclass
class FlowConfig:
    key: str
    title: str
    description: str
    steps: List[FlowStep]


# ---------------------------------------------------------------------------
# Loading YAML config
# ---------------------------------------------------------------------------


def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = load_yaml(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict at top level in {path}, got {type(data)}")
    return data


def load_agents() -> Dict[str, Agent]:
    agents: Dict[str, Agent] = {}
    if not AGENT_CONFIG_DIR.exists():
        return agents

    for cfg_path in sorted(AGENT_CONFIG_DIR.glob("*.yaml")):
        data = _safe_load_yaml(cfg_path)
        key = data.get("key")
        if not key:
            continue
        agents[key] = Agent(
            key=key,
            category=data.get("category", ""),
            color=data.get("color", ""),
            model=data.get("model", "inherit"),
            short_role=(data.get("short_role") or "").strip(),
        )
    return agents


def load_flows() -> Dict[str, FlowConfig]:
    flows: Dict[str, FlowConfig] = {}
    if not FLOW_CONFIG_DIR.exists():
        return flows

    for cfg_path in sorted(FLOW_CONFIG_DIR.glob("*.yaml")):
        data = _safe_load_yaml(cfg_path)
        key = data.get("key")
        if not key:
            continue

        title = data.get("title", key)
        description = (data.get("description") or "").strip()
        steps_raw = data.get("steps") or []

        steps: List[FlowStep] = []
        for raw in steps_raw:
            if not isinstance(raw, dict):
                continue
            sid = raw.get("id")
            if not sid:
                continue
            step_title = raw.get("title", sid)
            role = (raw.get("role") or raw.get("description") or "").strip()
            agents_list: List[str] = []
            for a in raw.get("agents") or []:
                if isinstance(a, str):
                    agents_list.append(a.strip())
            steps.append(
                FlowStep(
                    id=sid,
                    title=step_title,
                    role=role,
                    agents=agents_list,
                )
            )

        flows[key] = FlowConfig(
            key=key,
            title=title,
            description=description,
            steps=steps,
        )

    return flows


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def render_mermaid(flow: FlowConfig) -> str:
    """
    Render a simple Mermaid graph showing step order and attached agents.

    We stick to a very simple shape the Mermaid renderer can reliably handle.
    """
    lines: List[str] = []
    lines.append("```mermaid")
    lines.append("graph TD")

    # Step nodes
    for idx, step in enumerate(flow.steps, 1):
        node_id = f"{flow.key}_{step.id}"
        agents_text = ", ".join(step.agents)
        label_parts = [f"{idx}. {step.title}"]
        if agents_text:
            label_parts.append(f"({agents_text})")
        label = "\\n".join(label_parts).replace('"', '\\"')
        lines.append(f'  {node_id}["{label}"]')

    # Edges step -> next step
    for i in range(len(flow.steps) - 1):
        a = flow.steps[i]
        b = flow.steps[i + 1]
        lines.append(f"  {flow.key}_{a.id} --> {flow.key}_{b.id}")

    lines.append("```")
    return "\n".join(lines)


def render_steps_table(flow: FlowConfig, agents: Dict[str, Agent]) -> str:
    """
    Render a markdown table describing each step, which agents are involved,
    and what the step does.
    """
    lines: List[str] = []
    lines.append("| # | Step | Agents | Role |")
    lines.append("| - | ---- | ------ | ---- |")

    for idx, step in enumerate(flow.steps, 1):
        agent_cells: List[str] = []
        for akey in step.agents:
            a = agents.get(akey)
            if a and a.short_role:
                agent_cells.append(f"`{akey}` — {a.short_role}")
            else:
                agent_cells.append(f"`{akey}`")
        agents_text = "<br>".join(agent_cells)
        role = step.role.replace("\n", " ").strip()
        lines.append(f"| {idx} | `{step.id}` | {agents_text} | {role} |")

    return "\n".join(lines)


def render_autogen_block(flow: FlowConfig, agents: Dict[str, Agent]) -> str:
    """
    Render the entire auto-generated block including sentinels.

    This keeps the contract explicit and makes it obvious what not to edit.
    """
    mermaid = render_mermaid(flow)
    table = render_steps_table(flow, agents)

    block = f"""{AUTOGEN_START}
### Flow structure

{mermaid}

### Steps

{table}
{AUTOGEN_END}"""
    return block


# ---------------------------------------------------------------------------
# Markdown rewriting
# ---------------------------------------------------------------------------


def update_autogen_section(existing: str, new_block: str) -> Tuple[str, bool]:
    """
    Replace or append the autogen block in the existing markdown.

    Returns:
        (updated_text, changed_flag)
    """
    start_idx = existing.find(AUTOGEN_START)
    end_idx = existing.find(AUTOGEN_END)

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        end_idx += len(AUTOGEN_END)
        before = existing[:start_idx].rstrip()
        after = existing[end_idx:].lstrip("\n")
        updated = before + "\n\n" + new_block + "\n\n" + after
        changed = updated != existing
        return updated, changed

    # No existing block: append at the end
    base = existing.rstrip()
    if base:
        base += "\n\n"
    updated = base + new_block + "\n"
    changed = True
    return updated, changed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def process_flow(
    flow: FlowConfig,
    agents: Dict[str, Agent],
    check: bool,
) -> bool:
    """
    Process a single flow.

    Returns:
        True if OK (no diff or successfully updated),
        False if check mode found differences.
    """
    doc_path = FLOW_DOC_DIR / f"flow-{flow.key}.md"
    if doc_path.exists():
        existing = doc_path.read_text(encoding="utf-8")
    else:
        # Create a minimal doc shell; everything else is generated
        header_lines = [
            f"# {flow.title}",
            "",
            flow.description,
            "",
        ]
        existing = "\n".join(header_lines)

    new_block = render_autogen_block(flow, agents)
    updated, changed = update_autogen_section(existing, new_block)

    if check:
        if changed:
            sys.stderr.write(f"[DIFF] {doc_path}\n")
            diff = difflib.unified_diff(
                existing.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=str(doc_path),
                tofile=f"{doc_path} (generated)",
            )
            sys.stderr.writelines(diff)
            return False
        else:
            print(f"[OK] {doc_path}")
            return True

    # Write updated doc
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(updated, encoding="utf-8")
    if changed:
        print(f"[UPDATE] {doc_path}")
    else:
        print(f"[OK] {doc_path} (no changes)")
    return True


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate flow diagrams + step tables from YAML config."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write files; exit non-zero if any doc is out of date.",
    )
    parser.add_argument(
        "--flow",
        metavar="KEY",
        help="Only process the given flow key (e.g. 'deploy').",
    )
    args = parser.parse_args(argv)

    agents = load_agents()
    flows = load_flows()

    if not flows:
        sys.stderr.write("No flows found in swarm/config/flows.\n")
        return 1

    keys = sorted(flows.keys())
    if args.flow:
        if args.flow not in flows:
            sys.stderr.write(f"Flow {args.flow!r} not found.\n")
            return 1
        keys = [args.flow]

    ok = True
    for key in keys:
        flow = flows[key]
        success = process_flow(flow, agents, check=args.check)
        if not success:
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
