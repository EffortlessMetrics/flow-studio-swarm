#!/usr/bin/env python3
"""
swarm/meta.py - Single source of truth for swarm metadata.

This module computes metadata by introspecting the actual configuration,
eliminating hardcoded counts that can drift. All documentation generators
and invariant checkers should import from here.

Usage:
    from swarm.meta import compute_meta, get_meta

    meta = get_meta()  # Cached singleton
    print(f"Total agents: {meta['agents']['total']}")
    print(f"Selftest steps: {meta['selftest']['total']}")
"""

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

# Ensure swarm/tools is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_TOOLS_DIR = _REPO_ROOT / "swarm" / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))


def _get_repo_root() -> Path:
    """Get repository root directory."""
    return _REPO_ROOT


def _count_domain_agents() -> int:
    """Count domain agent files in .claude/agents/."""
    agents_dir = _get_repo_root() / ".claude" / "agents"
    if not agents_dir.exists():
        return 0
    return len(list(agents_dir.glob("*.md")))


def _count_skills() -> List[str]:
    """Get list of skill names from .claude/skills/."""
    skills_dir = _get_repo_root() / ".claude" / "skills"
    if not skills_dir.exists():
        return []
    skills = []
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skills.append(skill_dir.name)
    return sorted(skills)


def _get_selftest_tiers() -> Dict[str, int]:
    """Get selftest step counts by tier from selftest_config.py."""
    try:
        from selftest_config import SELFTEST_STEPS

        tiers = {"KERNEL": 0, "GOVERNANCE": 0, "OPTIONAL": 0}
        for step in SELFTEST_STEPS:
            tier_name = step.tier.name  # KERNEL, GOVERNANCE, OPTIONAL
            if tier_name in tiers:
                tiers[tier_name] += 1
        return tiers
    except ImportError:
        # Fallback if selftest_config not available
        return {"KERNEL": 1, "GOVERNANCE": 13, "OPTIONAL": 2}


def _get_selftest_steps() -> List[Dict[str, Any]]:
    """Get selftest step details from selftest_config.py."""
    try:
        from selftest_config import SELFTEST_STEPS

        return [step.to_dict() for step in SELFTEST_STEPS]
    except ImportError:
        return []


def compute_meta() -> Dict[str, Any]:
    """
    Compute all swarm metadata by introspecting actual configuration.

    Returns a dictionary with:
    - agents: {domain, built_in, total}
    - selftest: {total, tiers: {KERNEL, GOVERNANCE, OPTIONAL}, steps: [...]}
    - skills: {list, count}
    - flows: {sdlc_count, total_count}

    This is the SINGLE SOURCE OF TRUTH for all counts.
    """
    # Agent counts
    domain_agents = _count_domain_agents()
    built_in_agents = 3  # explore, plan-subagent, general-subagent (fixed)

    # Selftest counts
    selftest_tiers = _get_selftest_tiers()
    selftest_total = sum(selftest_tiers.values())
    selftest_steps = _get_selftest_steps()

    # Skills
    skills_list = _count_skills()

    # Flows (relatively static, but could be computed from flow_registry)
    sdlc_flows = 6  # signal, plan, build, gate, deploy, wisdom

    return {
        "agents": {
            "domain": domain_agents,
            "built_in": built_in_agents,
            "total": domain_agents + built_in_agents,
        },
        "selftest": {
            "total": selftest_total,
            "tiers": selftest_tiers,
            "steps": selftest_steps,
        },
        "skills": {
            "list": skills_list,
            "count": len(skills_list),
        },
        "flows": {
            "sdlc_count": sdlc_flows,
        },
        "version": "computed",  # Indicates this is dynamically computed
    }


@lru_cache(maxsize=1)
def get_meta() -> Dict[str, Any]:
    """
    Get cached swarm metadata.

    Uses lru_cache so repeated calls don't recompute.
    Call compute_meta() directly if you need fresh data.
    """
    return compute_meta()


def print_meta_summary() -> None:
    """Print a human-readable summary of swarm metadata."""
    meta = get_meta()

    print("Swarm Metadata (computed from configuration)")
    print("=" * 50)
    print()
    print("Agents:")
    print(f"  Domain agents:   {meta['agents']['domain']}")
    print(f"  Built-in agents: {meta['agents']['built_in']}")
    print(f"  Total agents:    {meta['agents']['total']}")
    print()
    print("Selftest:")
    print(f"  Total steps:     {meta['selftest']['total']}")
    print(f"  KERNEL:          {meta['selftest']['tiers']['KERNEL']}")
    print(f"  GOVERNANCE:      {meta['selftest']['tiers']['GOVERNANCE']}")
    print(f"  OPTIONAL:        {meta['selftest']['tiers']['OPTIONAL']}")
    print()
    print("Skills:")
    print(f"  Count:           {meta['skills']['count']}")
    print(f"  List:            {', '.join(meta['skills']['list'])}")
    print()
    print("Flows:")
    print(f"  SDLC flows:      {meta['flows']['sdlc_count']}")


if __name__ == "__main__":
    print_meta_summary()
