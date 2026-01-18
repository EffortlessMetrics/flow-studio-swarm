from __future__ import annotations

from swarm.tools.flow_studio_ui import get_index_html as _get_index_html


def get_index_html() -> str:
    return _get_index_html()


__all__ = ["get_index_html"]
