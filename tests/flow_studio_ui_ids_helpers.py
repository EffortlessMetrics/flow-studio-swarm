"""
Helpers for Flow Studio UI ID tests.
"""

import re
from typing import List, Tuple

# Pattern for valid data-uiid values
UIID_PATTERN = re.compile(
    r"^flow_studio"  # Screen prefix
    r"(\.[a-z][a-z0-9_]*)+"  # Region and components (snake_case)
    r"(:[a-zA-Z0-9_:-]+)?$"  # Optional dynamic ID suffix
    r"|^flow_studio$"  # OR just the root "flow_studio"
)

# Known valid regions
VALID_REGIONS = {
    "header",  # Top bar with search, mode toggle, etc.
    "sidebar",  # Left navigation panel
    "canvas",  # Main graph area
    "inspector",  # Right details panel
    "modal",  # Modal dialogs (selftest, shortcuts)
    "sdlc_bar",  # SDLC progress bar
}

# Layout-based names that should NOT be used
BANNED_PATTERNS = [
    (r"leftcol", "leftCol"),
    (r"rightcol", "rightCol"),
    (r"\.row\d+", "row<N>"),
    (r"\.col\d+", "col<N>"),
    (r"\.column\d+", "column<N>"),
    (r"\.top\.", "top"),
    (r"\.bottom\.", "bottom"),
    (r"\.left\.", "left"),
    (r"\.right\.", "right"),
]


def get_flow_studio_html() -> str:
    """Load the Flow Studio HTML from the UI module."""
    from swarm.tools.flow_studio_ui import get_index_html

    return get_index_html()


def extract_uiids_from_html(html: str) -> List[Tuple[str, int]]:
    """
    Extract all data-uiid attribute values from HTML DOM elements.

    Skips UIIDs found inside <script> tags (which are JavaScript strings,
    not actual DOM attributes).

    Returns:
        List of (uiid_value, line_number) tuples
    """
    uiids = []
    pattern = re.compile(r'data-uiid="([^"]+)"')

    # Track whether we're inside a script tag
    in_script = False
    script_start = re.compile(r"<script\b", re.IGNORECASE)
    script_end = re.compile(r"</script>", re.IGNORECASE)

    for line_num, line in enumerate(html.split("\n"), start=1):
        # Handle script tag transitions
        if script_start.search(line):
            in_script = True
        if script_end.search(line):
            in_script = False
            continue  # Skip the closing script line

        # Skip lines inside script tags
        if in_script:
            continue

        for match in pattern.finditer(line):
            value = match.group(1)
            # Skip JavaScript template literals (e.g., ${id} in compiled JS)
            if "${" in value:
                continue
            uiids.append((value, line_num))

    return uiids


def validate_uiid(uiid: str) -> List[str]:
    """
    Validate a single data-uiid value against the contract.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check overall pattern
    if not UIID_PATTERN.match(uiid):
        errors.append(f"'{uiid}' does not match pattern flow_studio[.<region>.<thing>][:{id}]")
        return errors

    # Extract region (skip validation for root "flow_studio")
    parts = uiid.split(".")
    if len(parts) >= 2:
        region = parts[1].split(":")[0]  # Remove dynamic ID suffix if present
        if region not in VALID_REGIONS:
            errors.append(
                f"'{uiid}' uses unknown region '{region}' (valid: {', '.join(sorted(VALID_REGIONS))})"
            )

    # Check for banned layout-based patterns
    for pattern, description in BANNED_PATTERNS:
        if re.search(pattern, uiid, re.IGNORECASE):
            errors.append(f"'{uiid}' contains banned layout-based pattern '{description}'")

    return errors
