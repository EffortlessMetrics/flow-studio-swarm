"""
Shared helper for the routing context digest test modules.

The digest suite is split by signal family:

- test_routing_context_digest.py         - core shape and verification signals
- test_routing_context_digest_signals.py - diff, forensic, loop signals; budget
"""

import re


def parse_digest(digest: str) -> dict:
    """Split a digest into its key=value clauses.

    Values containing spaces are bracketed (e.g. failed=[a, b]), so split on
    keys rather than on whitespace.
    """
    import re

    return {m.group(1): m.group(2) for m in re.finditer(r"(\w+)=(\[[^\]]*\]|\S+)", digest)}
