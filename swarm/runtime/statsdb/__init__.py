from __future__ import annotations

from .cli import main
from .db import StatsDB
from .duckdb_import import _get_duckdb
from .events import CANONICAL_EVENT_KINDS, EVENT_KIND_ALIASES, normalize_event_kind, parse_event_ts
from .models import Fact, RoutingDecisionRecord, RunStats, StepStats, ToolBreakdown
from .rebuild import rebuild_stats_db
from .schema_sql import CREATE_TABLES_SQL
from .singleton import close_stats_db, get_stats_db
from .versions import (
    PROJECTION_VERSION,
    SCHEMA_VERSION,
    _check_projection_version,
    _rename_old_db,
    _set_projection_version,
)

__all__ = [
    "CANONICAL_EVENT_KINDS",
    "CREATE_TABLES_SQL",
    "EVENT_KIND_ALIASES",
    "Fact",
    "PROJECTION_VERSION",
    "RoutingDecisionRecord",
    "RunStats",
    "SCHEMA_VERSION",
    "StatsDB",
    "StepStats",
    "ToolBreakdown",
    "_check_projection_version",
    "_get_duckdb",
    "_rename_old_db",
    "_set_projection_version",
    "close_stats_db",
    "get_stats_db",
    "main",
    "normalize_event_kind",
    "parse_event_ts",
    "rebuild_stats_db",
]
