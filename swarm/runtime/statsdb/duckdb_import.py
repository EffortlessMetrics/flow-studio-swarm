from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_duckdb = None


def _get_duckdb():
    """Lazy import of duckdb module."""
    global _duckdb
    if _duckdb is None:
        try:
            import duckdb

            _duckdb = duckdb
        except ImportError:
            logger.warning("DuckDB not available - stats will not be persisted")
            return None
    return _duckdb
