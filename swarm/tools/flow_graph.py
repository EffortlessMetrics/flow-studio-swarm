#!/usr/bin/env python3
"""
Emit a simple flow ↔ agent graph derived from swarm/AGENTS.md.

Usage:
  uv run swarm/tools/flow_graph.py --format dot  > flows.dot
  uv run swarm/tools/flow_graph.py --format json > flows.json
  uv run swarm/tools/flow_graph.py --format table
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = ROOT / "swarm" / "AGENTS.md"


@dataclass
class AgentRow:
    """Parsed row from AGENTS.md table."""

    key: str
    flow: str
    role_family: str
    color: str
    source: str
    description: str


def parse_agents_md(path: Path) -> List[AgentRow]:
    """Parse AGENTS.md table and return list of agent rows."""
    rows: List[AgentRow] = []
    if not path.is_file():
        return rows

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        # Skip non-table lines
        if not line.startswith("|"):
            continue
        if line.lower().startswith("| agent") or line.startswith("|---"):
            continue

        # Parse table row
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 7:
            continue

        # parts[0] and parts[-1] are empty (around table delimiters)
        try:
            rows.append(
                AgentRow(
                    key=parts[1],
                    flow=parts[2],
                    role_family=parts[3],
                    color=parts[4],
                    source=parts[5],
                    description=parts[6],
                )
            )
        except IndexError:
            continue

    return rows


def build_flow_graph(rows: List[AgentRow]) -> Dict[str, List[str]]:
    """Build a map from flow -> [agent_key, ...] for project/user agents."""
    graph: Dict[str, List[str]] = {}
    for row in rows:
        if row.source != "project/user":
            continue
        graph.setdefault(row.flow, []).append(row.key)
    return graph


def emit_dot(rows: List[AgentRow]) -> str:
    """Emit Graphviz DOT format."""
    lines: List[str] = []
    lines.append("digraph flows {")
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=box];")

    # Group by flow
    flows_dict: Dict[str, List[AgentRow]] = {}
    for row in rows:
        if row.source != "project/user":
            continue
        flows_dict.setdefault(row.flow, []).append(row)

    # Emit subgraphs per flow
    for flow in sorted(flows_dict.keys()):
        agents = flows_dict[flow]
        flow_safe = flow.replace("-", "_")
        lines.append(f"  subgraph cluster_{flow_safe} {{")
        lines.append(f'    label="{flow}";')

        for agent in agents:
            agent_id = f"{flow_safe}_{agent.key.replace('-', '_')}"
            lines.append(
                f'    "{agent_id}" [label="{agent.key}", style=filled, fillcolor={agent.color}];'
            )

        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)


def emit_json(rows: List[AgentRow]) -> str:
    """Emit JSON format."""
    graph = build_flow_graph(rows)
    return json.dumps(graph, indent=2, sort_keys=True)


def emit_table(rows: List[AgentRow]) -> str:
    """Emit simple table format."""
    lines: List[str] = []
    lines.append("Flow     | Agent")
    lines.append("---------|------------------------------")

    # Sort by flow, then agent
    sorted_rows = sorted(
        [r for r in rows if r.source == "project/user"],
        key=lambda r: (r.flow, r.key),
    )

    for row in sorted_rows:
        lines.append(f"{row.flow:8} | {row.key}")

    return "\n".join(lines)


def main() -> None:
    """Parse arguments and emit graph."""
    parser = argparse.ArgumentParser(description="Emit flow ↔ agent graph from swarm/AGENTS.md.")
    parser.add_argument(
        "--format",
        choices=["dot", "json", "table"],
        default="dot",
        help="Output format (default: dot)",
    )
    args = parser.parse_args()

    rows = parse_agents_md(AGENTS_MD)

    if args.format == "json":
        print(emit_json(rows))
    elif args.format == "table":
        print(emit_table(rows))
    else:  # dot
        print(emit_dot(rows))


if __name__ == "__main__":
    main()
