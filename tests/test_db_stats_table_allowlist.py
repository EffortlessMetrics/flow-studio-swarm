"""Guardrail: /db/stats may only count tables from a fixed allowlist.

SQL identifiers cannot be bound as query parameters, so the stats endpoint
interpolates the table name into the COUNT query. These tests pin the
allowlist that keeps that interpolation constrained to fixed literals, so the
pattern cannot drift into accepting caller-controlled input.
"""

from __future__ import annotations

import inspect

from swarm.api.routes.db import COUNTABLE_TABLES, get_db_stats


class TestCountableTablesAllowlist:
    """The allowlist is the control that makes the interpolation safe."""

    def test_allowlist_is_immutable(self):
        """A frozenset cannot be mutated at runtime by another module."""
        assert isinstance(COUNTABLE_TABLES, frozenset)

    def test_allowlist_contains_expected_tables(self):
        """The projection's countable tables."""
        assert COUNTABLE_TABLES == {
            "runs",
            "steps",
            "tool_calls",
            "file_changes",
            "events",
            "facts",
        }

    def test_allowlist_entries_are_plain_identifiers(self):
        """Every allowlisted name is a bare SQL identifier.

        No quoting, whitespace, comment markers, or statement separators, so
        interpolating any member cannot alter the query's structure.
        """
        for table in COUNTABLE_TABLES:
            assert table.isidentifier(), f"{table!r} is not a plain identifier"
            assert table.islower(), f"{table!r} should be lowercase"

    def test_stats_endpoint_checks_allowlist_before_querying(self):
        """The membership check must precede the query in safe_count()."""
        source = inspect.getsource(get_db_stats)

        assert "COUNTABLE_TABLES" in source, "safe_count() must consult the allowlist"
        assert "if table not in COUNTABLE_TABLES" in source, (
            "safe_count() must reject tables outside the allowlist"
        )

        guard = source.index("if table not in COUNTABLE_TABLES")
        query = source.index("SELECT COUNT(*)")
        assert guard < query, "allowlist check must happen before the query executes"

    def test_every_counted_table_is_allowlisted(self):
        """No call site may pass a table the allowlist would reject.

        Guards against a new counter being added without extending the
        allowlist, which would silently return 0 instead of a real count.
        """
        source = inspect.getsource(get_db_stats)

        counted = {
            line.split('safe_count("')[1].split('"')[0]
            for line in source.splitlines()
            if 'safe_count("' in line
        }

        assert counted, "expected safe_count() call sites"
        assert counted <= COUNTABLE_TABLES, (
            f"counted tables not in allowlist: {sorted(counted - COUNTABLE_TABLES)}"
        )
