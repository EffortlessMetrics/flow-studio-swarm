#!/usr/bin/env python3
"""
Generate a flows ↔ agents index document.

Reads swarm/config/flows/*.yaml and swarm/config/agents/*.yaml
Produces docs/FLOWS_INDEX.md with three sections:
1. By Flow Table - all steps and agents per flow
2. By Agent Table - which flows each agent participates in
3. Quick Reference - cross-index for lookups

Usage:
    uv run swarm/tools/gen_flows_index.py          # Generate index
    uv run swarm/tools/gen_flows_index.py --check  # Verify against existing

Exit codes:
    0 - Success (index generated or check passed)
    1 - Failure (check failed, mismatch detected)
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add repo root to path for imports
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from swarm.utils.yaml_utils import load_yaml
from swarm.config.flow_registry import get_flow_index  # noqa: E402

# Project root (two levels up from this script)
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FLOWS_DIR = PROJECT_ROOT / "swarm" / "config" / "flows"
CONFIG_AGENTS_DIR = PROJECT_ROOT / "swarm" / "config" / "agents"
OUTPUT_FILE = PROJECT_ROOT / "docs" / "FLOWS_INDEX.md"


def load_flow_configs() -> Dict[str, Any]:
    """Load all flow YAML configs."""
    flows = {}
    if not CONFIG_FLOWS_DIR.exists():
        print(f"Error: {CONFIG_FLOWS_DIR} not found")
        sys.exit(2)

    for yaml_file in sorted(CONFIG_FLOWS_DIR.glob("*.yaml")):
        with open(yaml_file, "r") as f:
            flow = load_yaml(f)
            if flow and "key" in flow:
                flows[flow["key"]] = flow

    return flows


def load_agent_configs() -> Dict[str, Any]:
    """Load all agent YAML configs."""
    agents = {}
    if not CONFIG_AGENTS_DIR.exists():
        print(f"Error: {CONFIG_AGENTS_DIR} not found")
        sys.exit(2)

    for yaml_file in sorted(CONFIG_AGENTS_DIR.glob("*.yaml")):
        with open(yaml_file, "r") as f:
            agent = load_yaml(f)
            if agent and "key" in agent:
                agents[agent["key"]] = agent

    return agents


def build_flow_agent_index(flows: Dict[str, Any], agents: Dict[str, Any]) -> Dict[str, List[str]]:
    """Build mapping of agent key -> list of flows (deduplicated per flow)."""
    agent_flows = defaultdict(set)

    for flow_key, flow_data in flows.items():
        # Add steps agents
        for step in flow_data.get("steps", []):
            for agent in step.get("agents", []):
                agent_flows[agent].add(flow_key)

        # Add cross-cutting agents
        for agent in flow_data.get("cross_cutting", []):
            agent_flows[agent].add(flow_key)

    # Convert sets to sorted lists
    return {k: sorted(v) for k, v in agent_flows.items()}


def flow_index(flow_key: str) -> int:
    """Convert flow key to numeric index (1-6)."""
    return get_flow_index(flow_key)


def generate_by_flow_section(flows: Dict[str, Any]) -> str:
    """Generate 'By Flow' section with all steps and agents."""
    lines = ["## By Flow\n"]

    # Sort flows by numeric order
    sorted_flows = sorted(flows.items(), key=lambda x: flow_index(x[0]))

    for flow_key, flow_data in sorted_flows:
        flow_num = flow_index(flow_key)
        title = flow_data.get("title", flow_key)

        lines.append(f"### {flow_num}. {title}\n")
        lines.append("| Step # | Step ID | Agents |")
        lines.append("|--------|---------|--------|")

        steps = flow_data.get("steps", [])
        for step_num, step in enumerate(steps, 1):
            step_id = step.get("id", "?")
            agent_list = ", ".join(step.get("agents", []))
            lines.append(f"| {step_num} | `{step_id}` | {agent_list} |")

        # Add cross-cutting agents note if present
        cross_cutting = flow_data.get("cross_cutting", [])
        if cross_cutting:
            lines.append("")
            lines.append(f"**Cross-cutting agents**: {', '.join(cross_cutting)}")

        lines.append("")

    return "\n".join(lines)


def generate_by_agent_section(
    agents: Dict[str, Any],
    agent_flows: Dict[str, List[str]],
    flows: Dict[str, Any]
) -> str:
    """Generate 'By Agent' section with flows per agent."""
    lines = ["## By Agent\n"]
    lines.append("| Agent | Category | Flows | Short Role |")
    lines.append("|-------|----------|-------|------------|")

    # Sort agents by category then name
    category_order = {
        "shaping": 0,
        "spec": 1,
        "design": 2,
        "implementation": 3,
        "critic": 4,
        "verification": 5,
        "analytics": 6,
        "reporter": 7,
        "infra": 8,
    }

    sorted_agents = sorted(
        agents.items(),
        key=lambda x: (
            category_order.get(x[1].get("category", ""), 99),
            x[0]
        )
    )

    for agent_key, agent_data in sorted_agents:
        category = agent_data.get("category", "unknown")
        short_role = agent_data.get("short_role", "")

        # Get flows for this agent
        flows_for_agent = agent_flows.get(agent_key, [])
        flows_str = ", ".join([f"Flow {flow_index(f)}" for f in sorted(flows_for_agent)])

        # Truncate role if too long
        if len(short_role) > 60:
            short_role = short_role[:57] + "..."

        lines.append(f"| `{agent_key}` | {category} | {flows_str} | {short_role} |")

    lines.append("")
    return "\n".join(lines)


def generate_quick_reference_section(
    flows: Dict[str, Any],
    agents: Dict[str, Any],
    agent_flows: Dict[str, List[str]]
) -> str:
    """Generate quick reference lookups."""
    lines = ["## Quick Reference\n"]

    # Group agents by category
    by_category = defaultdict(list)
    for agent_key, agent_data in agents.items():
        category = agent_data.get("category", "unknown")
        by_category[category].append(agent_key)

    # Agent count by category
    lines.append("### Agents by Category\n")
    category_order = [
        "shaping", "spec", "design", "implementation",
        "critic", "verification", "analytics", "reporter", "infra"
    ]

    for category in category_order:
        if category in by_category:
            count = len(by_category[category])
            agent_list = ", ".join(sorted(by_category[category]))
            lines.append(f"- **{category.title()}** ({count}): {agent_list}")

    lines.append("")

    # Agents per flow
    lines.append("### Agents per Flow\n")
    sorted_flows = sorted(flows.items(), key=lambda x: flow_index(x[0]))

    for flow_key, flow_data in sorted_flows:
        flow_num = flow_index(flow_key)
        # Extract short title, e.g. "Flow 1 - Signal → Spec (Shaping)" -> "Signal → Spec"
        title = flow_data.get("title", flow_key)
        if " - " in title:
            short_title = title.split(" - ", 1)[1].split(" (")[0].strip()
        else:
            short_title = title

        # Collect unique agents in this flow
        flow_agents = set()
        for step in flow_data.get("steps", []):
            flow_agents.update(step.get("agents", []))
        flow_agents.update(flow_data.get("cross_cutting", []))

        count = len(flow_agents)
        agent_list = ", ".join(f"`{a}`" for a in sorted(flow_agents))
        lines.append(f"- **Flow {flow_num}: {short_title}** — {count} agents: {agent_list}")

    lines.append("")

    # Multi-flow agents
    lines.append("### Agents in Multiple Flows\n")
    multi_flow = []
    for agent_key in sorted(agents.keys()):
        flows_list = agent_flows.get(agent_key, [])
        if len(flows_list) > 1:
            flow_nums = ", ".join([f"Flow {flow_index(f)}" for f in flows_list])
            multi_flow.append(f"- `{agent_key}`: {flow_nums}")

    if multi_flow:
        lines.extend(multi_flow)
    else:
        lines.append("(No agents appear in multiple flows)")

    lines.append("")
    return "\n".join(lines)


def generate_index(flows: Dict[str, Any], agents: Dict[str, Any]) -> str:
    """Generate the complete index document."""
    agent_flows = build_flow_agent_index(flows, agents)

    header = """<!-- AUTOGENERATED - DO NOT EDIT MANUALLY -->
<!-- This file is generated by swarm/tools/gen_flows_index.py -->
<!-- To regenerate: uv run swarm/tools/gen_flows_index.py -->

# Flows ↔ Agents Index

This document provides a comprehensive cross-reference of flows and agents in the swarm.

**Metadata:**
- Total Flows: 6
- Total Agents: {agent_count}
- Generated from: `swarm/config/flows/*.yaml` and `swarm/config/agents/*.yaml`

---

""".format(agent_count=len(agents))

    by_flow = generate_by_flow_section(flows)
    by_agent = generate_by_agent_section(agents, agent_flows, flows)
    quick_ref = generate_quick_reference_section(flows, agents, agent_flows)

    footer = """
---

## Notes

- **Cross-cutting agents** appear in multiple flows and are listed separately in each flow
- **Flow numbers** (1-6) follow the SDLC sequence: Signal → Plan → Build → Gate → Deploy → Wisdom
- **Categories** map to semantic role families: shaping, spec/design, implementation, critic, verification, analytics, reporter, infra
- This index is a read-only reference generated from source YAML configs in `swarm/config/`
"""

    return header + by_flow + by_agent + quick_ref + footer


def write_index(content: str) -> bool:
    """Write the generated index to file."""
    # Ensure docs directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    return True


def check_index(content: str) -> bool:
    """Check if generated content matches existing file."""
    if not OUTPUT_FILE.exists():
        print(f"Error: {OUTPUT_FILE} does not exist")
        return False

    with open(OUTPUT_FILE, "r") as f:
        existing = f.read()

    if content.strip() == existing.strip():
        print(f"OK: {OUTPUT_FILE} is up-to-date")
        return True
    else:
        print(f"ERROR: {OUTPUT_FILE} is out of date")
        print("Run: uv run swarm/tools/gen_flows_index.py")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate flows ↔ agents index document"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if index is up-to-date (don't regenerate)"
    )
    args = parser.parse_args()

    # Load configs
    flows = load_flow_configs()
    agents = load_agent_configs()

    if not flows:
        print(f"Warning: No flow configs found in {CONFIG_FLOWS_DIR}")
    if not agents:
        print(f"Warning: No agent configs found in {CONFIG_AGENTS_DIR}")

    # Generate content
    content = generate_index(flows, agents)

    if args.check:
        # Check mode
        success = check_index(content)
        sys.exit(0 if success else 1)
    else:
        # Generate mode
        write_index(content)
        print(f"Generated: {OUTPUT_FILE}")
        print(f"Flows: {len(flows)}, Agents: {len(agents)}")
        sys.exit(0)


if __name__ == "__main__":
    main()
