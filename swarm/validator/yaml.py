# swarm/validator/yaml.py
"""Custom YAML frontmatter parser with no external dependencies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional


class SimpleYAMLParser:
    """
    Custom YAML parser with no external dependencies.

    Handles simple YAML patterns used in swarm:
    - String values (quoted or unquoted)
    - Lists (inline [...] or multi-line with -)
    - Booleans, nulls
    - Comments

    Does NOT handle: anchors, tags, complex nested structures.
    """

    RE_FRONTMATTER = re.compile(r"^---\s*$")
    RE_YAML_FIELD = re.compile(r"^([a-zA-Z0-9_\-]+):\s*(.*)$")

    @staticmethod
    def _check_unclosed_quote(value: str, line_num: int) -> None:
        """
        Check if a value has an unclosed quote.

        Args:
            value: The value string to check
            line_num: 1-based line number for error message

        Raises:
            ValueError: If value starts with a quote but doesn't end with one
        """
        if value.startswith('"') and not value.endswith('"'):
            raise ValueError(f"Unclosed quote on line {line_num}")
        if value.startswith("'") and not value.endswith("'"):
            raise ValueError(f"Unclosed quote on line {line_num}")

    @staticmethod
    def parse(
        content: str,
        file_path: Optional[Path] = None,
        strict: bool = False,
        is_frontmatter: bool = True,
    ) -> Dict[str, Any]:
        """
        Parse YAML content (either frontmatter or raw YAML).

        Args:
            content: File content (with or without frontmatter delimiters)
            file_path: Optional path for error messages
            strict: If True, raise error on malformed (non-comment) lines
            is_frontmatter: If True (default), expects --- delimiters;
                           if False, parses raw YAML without delimiters

        Returns:
            Dict of frontmatter/YAML fields

        Raises:
            ValueError: If content is malformed
        """
        if not content or not content.strip():
            if is_frontmatter:
                raise ValueError("file is empty or contains only whitespace")
            else:
                raise ValueError("content is empty or contains only whitespace")

        lines = content.split("\n")

        # Handle frontmatter format (with --- delimiters)
        # Track line offset for accurate error reporting (1-based)
        line_offset = 1  # Lines in content are 1-based

        if is_frontmatter:
            if not lines or not SimpleYAMLParser.RE_FRONTMATTER.match(lines[0]):
                raise ValueError("frontmatter must start with '---' on line 1")

            fm_end = -1
            for i in range(1, len(lines)):
                if SimpleYAMLParser.RE_FRONTMATTER.match(lines[i]):
                    fm_end = i
                    break

            if fm_end == -1:
                raise ValueError("frontmatter not terminated with '---'")

            fm_lines = lines[1:fm_end]
            line_offset = 2  # Frontmatter content starts after first ---
        else:
            # Raw YAML without delimiters
            fm_lines = lines

        # Parse fields
        fields: Dict[str, Any] = {}
        i = 0
        while i < len(fm_lines):
            line = fm_lines[i]
            stripped = line.strip()
            # Calculate actual line number (1-based) for error messages
            actual_line_num = i + line_offset

            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            # Match key: value
            m = SimpleYAMLParser.RE_YAML_FIELD.match(stripped)
            if not m:
                # If strict mode and line is not a comment/empty, error
                if strict:
                    raise ValueError(
                        f"Malformed YAML on line {actual_line_num} "
                        f"(not a key: value pair): '{stripped}'"
                    )
                i += 1
                continue

            key, value = m.groups()
            value = value.strip()

            # Check for unclosed quotes
            SimpleYAMLParser._check_unclosed_quote(value, actual_line_num)

            # Check for multi-line list (next line starts with -)
            if not value and i + 1 < len(fm_lines):
                next_line = fm_lines[i + 1].strip()
                if next_line.startswith("-"):
                    # Collect list items
                    items = []
                    j = i + 1
                    while j < len(fm_lines):
                        item_line = fm_lines[j].strip()
                        # Skip empty lines
                        if not item_line:
                            j += 1
                            continue
                        # Skip comments in list
                        if item_line.startswith("#"):
                            j += 1
                            continue
                        if item_line.startswith("-"):
                            item_text = item_line[1:].strip()
                            # Skip empty list items
                            if item_text:
                                items.append(item_text)
                            j += 1
                        else:
                            break
                    fields[key] = items
                    i = j
                    continue

            # Parse scalar values
            if value.lower() == "true":
                fields[key] = True
            elif value.lower() == "false":
                fields[key] = False
            elif value.lower() in ("null", "~", "") or not value.strip():
                # Empty or whitespace-only values treated as null
                fields[key] = None
            elif value.startswith("[") and value.endswith("]"):
                # Inline list: [item1, item2, ...]
                inner = value[1:-1].strip()
                if not inner:
                    fields[key] = []
                else:
                    items = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
                    fields[key] = items
            else:
                # String value - strip quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    fields[key] = value[1:-1]
                else:
                    fields[key] = value

            i += 1

        return fields
