"""Smoke tests for gen_adapters.py multi-platform generator."""

import subprocess
import sys
import textwrap
from pathlib import Path


def write(path: Path, content: str) -> None:
    """Write content to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def run(cmd: list, cwd: Path) -> tuple[int, str]:
    """Run a command and return (returncode, combined_output)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode, result.stdout


def test_generator_check_all_with_model_tiers(tmp_path: Path) -> None:
    """Test that generator respects model_tier in agent configs."""
    root = tmp_path

    # Create agent config with model_tier
    write(
        root / "swarm" / "config" / "agents" / "demo-agent.yaml",
        """
        key: demo-agent
        flows:
          - demo
        category: verification
        color: blue
        source: project/user
        short_role: Demo agent for testing
        model: inherit
        model_tier: balanced
        """,
    )

    # Create platform profile with model defaults
    write(
        root / "swarm" / "platforms" / "claude.yaml",
        """
        name: claude-code
        platform_key: claude
        agents_dir: .claude/agents
        commands_dir: .claude/commands

        frontmatter:
          allowed_keys:
            - name
            - description
            - model
            - color

        model_defaults:
          tier:
            fast: claude-3-haiku
            balanced: claude-3.5-sonnet
            deep: claude-3-opus
          fallback: claude-3.5-sonnet
        """,
    )

    # Create template
    write(
        root / "swarm" / "templates" / "claude" / "agent_frontmatter.md.tpl",
        """
        ---
        name: {name}
        description: {description}
        model: {model}
        color: {color}
        ---
        """,
    )

    # Create initial agent file with body
    write(
        root / ".claude" / "agents" / "demo-agent.md",
        """
        ---
        name: demo-agent
        description: Demo agent for testing
        model: claude-3.5-sonnet
        color: blue
        ---

        You are the demo agent.

        ## Behavior
        - Do stuff
        """,
    )

    script = Path(__file__).parent.parent / "swarm" / "tools" / "gen_adapters.py"

    # Generate to update with correct model
    rc, out = run(
        [sys.executable, str(script), "--platform", "claude", "--mode", "generate-all"],
        cwd=root,
    )
    assert rc == 0, f"generate-all failed: {out}"
    assert "[INFO] Updating" in out or "[OK]" in out, f"Unexpected output: {out}"

    # Check to verify alignment
    rc, out = run(
        [sys.executable, str(script), "--platform", "claude", "--mode", "check-all"],
        cwd=root,
    )
    assert rc == 0, f"check-all failed: {out}"
    assert "[OK]" in out


def test_generator_platform_override(tmp_path: Path) -> None:
    """Test that per-platform overrides work correctly."""
    root = tmp_path

    # Agent with platform override
    write(
        root / "swarm" / "config" / "agents" / "override-agent.yaml",
        """
        key: override-agent
        flows:
          - demo
        category: verification
        color: blue
        source: project/user
        short_role: Agent with platform override
        model: inherit
        model_tier: balanced

        platforms:
          claude:
            model_tier: deep
        """,
    )

    # Platform profile
    write(
        root / "swarm" / "platforms" / "claude.yaml",
        """
        name: claude-code
        platform_key: claude
        agents_dir: .claude/agents

        model_defaults:
          tier:
            fast: claude-3-haiku
            balanced: claude-3.5-sonnet
            deep: claude-3-opus
          fallback: claude-3.5-sonnet
        """,
    )

    # Template
    write(
        root / "swarm" / "templates" / "claude" / "agent_frontmatter.md.tpl",
        """
        ---
        name: {name}
        description: {description}
        model: {model}
        color: {color}
        ---
        """,
    )

    # Agent file
    write(
        root / ".claude" / "agents" / "override-agent.md",
        """
        ---
        name: override-agent
        description: Agent with platform override
        model: claude-3-opus
        color: blue
        ---

        Body text here.
        """,
    )

    script = Path(__file__).parent.parent / "swarm" / "tools" / "gen_adapters.py"

    # Check that the override results in the correct model
    rc, out = run(
        [sys.executable, str(script), "--platform", "claude", "--mode", "check-all"],
        cwd=root,
    )
    assert rc == 0, f"check-all failed: {out}"


def test_generator_respects_explicit_model(tmp_path: Path) -> None:
    """Test that explicit model in config overrides model_tier."""
    root = tmp_path

    # Agent with explicit model (not inherit)
    write(
        root / "swarm" / "config" / "agents" / "explicit-agent.yaml",
        """
        key: explicit-agent
        flows:
          - demo
        category: verification
        color: blue
        source: project/user
        short_role: Agent with explicit model
        model: claude-3.5-sonnet
        model_tier: fast
        """,
    )

    write(
        root / "swarm" / "platforms" / "claude.yaml",
        """
        name: claude-code
        platform_key: claude
        agents_dir: .claude/agents

        model_defaults:
          tier:
            fast: claude-3-haiku
            balanced: claude-3.5-sonnet
            deep: claude-3-opus
          fallback: claude-3.5-sonnet
        """,
    )

    write(
        root / "swarm" / "templates" / "claude" / "agent_frontmatter.md.tpl",
        """
        ---
        name: {name}
        description: {description}
        model: {model}
        color: {color}
        ---
        """,
    )

    write(
        root / ".claude" / "agents" / "explicit-agent.md",
        """
        ---
        name: explicit-agent
        description: Agent with explicit model
        model: claude-3.5-sonnet
        color: blue
        ---

        Body here.
        """,
    )

    script = Path(__file__).parent.parent / "swarm" / "tools" / "gen_adapters.py"

    # Explicit model should win over tier
    rc, out = run(
        [sys.executable, str(script), "--platform", "claude", "--mode", "check-all"],
        cwd=root,
    )
    assert rc == 0, f"check-all failed: {out}"
