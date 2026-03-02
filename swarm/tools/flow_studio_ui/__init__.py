"""Flow Studio UI package.

This package contains the HTML/CSS/JS template for the Flow Studio web interface.
The template was extracted from the Flask implementation to decouple UI from backend.
"""

from pathlib import Path

# Cache the HTML at module load time to avoid per-request disk I/O.
# This eliminates ~18s delays on Windows caused by Defender scanning
# the ~334KB HTML file on each request.
_UI_DIR = Path(__file__).parent

# Eagerly load at import time so the Defender scan happens during server startup,
# not on the first user request.
_INDEX_HTML_CACHE: str = (_UI_DIR / "index.html").read_text(encoding="utf-8")


def get_index_html() -> str:
    """Load the Flow Studio UI HTML template.

    The HTML is cached at module import time to avoid per-request disk reads.
    On Windows, this prevents Defender from scanning the file on every request.

    Returns:
        str: Complete HTML document for the Flow Studio UI.
    """
    return _INDEX_HTML_CACHE


__all__ = ["get_index_html"]
