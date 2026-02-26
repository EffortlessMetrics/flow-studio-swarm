
"""
Markdown utility functions for sanitizing content.
"""
import re

def escape_markdown_code_block(content: str) -> str:
    """
    Escapes content for inclusion in a Markdown code block.

    Ensures that the content does not break out of the code block by using
    a delimiter that is longer than any sequence of backticks in the content.
    """
    if not content:
        return "```\n```"

    # Find the longest sequence of backticks
    longest_backtick_seq = 0
    for match in re.finditer(r"`+", content):
        longest_backtick_seq = max(longest_backtick_seq, len(match.group(0)))

    # Use at least 3 backticks, or one more than the longest sequence
    delimiter_len = max(3, longest_backtick_seq + 1)
    delimiter = "`" * delimiter_len

    return f"{delimiter}\n{content}\n{delimiter}"

def escape_markdown_inline(content: str) -> str:
    """
    Escapes content for inclusion as inline Markdown code.

    Wraps the content in backticks sequences longer than any inside the content.
    """
    if not content:
        return "``"

    # Find the longest sequence of backticks
    longest_backtick_seq = 0
    for match in re.finditer(r"`+", content):
        longest_backtick_seq = max(longest_backtick_seq, len(match.group(0)))

    delimiter_len = max(1, longest_backtick_seq + 1)
    delimiter = "`" * delimiter_len

    # If content starts or ends with backtick, add spaces
    padded_content = content
    if content.startswith("`") or content.endswith("`"):
        padded_content = f" {content} "

    return f"{delimiter}{padded_content}{delimiter}"
