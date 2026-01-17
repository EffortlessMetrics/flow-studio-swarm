from __future__ import annotations

CREATE_TABLES_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projection version tracking (for schema resilience / rebuild-from-events)
CREATE TABLE IF NOT EXISTS _projection_meta (
    key VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Runs table: one row per run
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR PRIMARY KEY,
    flow_keys VARCHAR[],  -- Array of flow keys executed
    profile_id VARCHAR,
    engine_id VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,  -- running, succeeded, failed, cancelled
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_duration_ms INTEGER DEFAULT 0,
    metadata JSON
);

-- Steps table: one row per step execution
CREATE SEQUENCE IF NOT EXISTS steps_id_seq;
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY DEFAULT nextval('steps_id_seq'),
    run_id VARCHAR NOT NULL,
    flow_key VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    step_index INTEGER,
    agent_key VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,  -- running, succeeded, failed, skipped
    duration_ms INTEGER DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    handoff_status VARCHAR,  -- VERIFIED, UNVERIFIED, PARTIAL, BLOCKED
    routing_decision VARCHAR,  -- advance, loop, terminate, branch
    routing_next_step VARCHAR,
    routing_confidence FLOAT,
    error_message VARCHAR,
    UNIQUE(run_id, flow_key, step_id, started_at)
);

-- Tool calls table: one row per tool invocation
CREATE SEQUENCE IF NOT EXISTS tool_calls_id_seq;
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY DEFAULT nextval('tool_calls_id_seq'),
    run_id VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    tool_name VARCHAR NOT NULL,
    phase VARCHAR,  -- work, finalization, routing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    target_path VARCHAR,  -- For file operations
    diff_lines_added INTEGER,
    diff_lines_removed INTEGER,
    exit_code INTEGER,  -- For bash operations
    error_message VARCHAR
);

-- File changes table: aggregated file modifications per step
CREATE SEQUENCE IF NOT EXISTS file_changes_id_seq;
CREATE TABLE IF NOT EXISTS file_changes (
    id INTEGER PRIMARY KEY DEFAULT nextval('file_changes_id_seq'),
    run_id VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    change_type VARCHAR,  -- created, modified, deleted
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    timestamp TIMESTAMP,
    UNIQUE(run_id, step_id, file_path)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_flow_step ON steps(flow_key, step_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_run_id ON tool_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_step_id ON tool_calls(step_id);
CREATE INDEX IF NOT EXISTS idx_file_changes_run_id ON file_changes(run_id);

-- Events table: raw event storage for idempotent ingestion
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR PRIMARY KEY,
    seq INTEGER NOT NULL,
    run_id VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    kind VARCHAR NOT NULL,
    flow_key VARCHAR NOT NULL,
    step_id VARCHAR,
    agent_key VARCHAR,
    payload JSON,
    ingested_at TIMESTAMP DEFAULT (now())
);

CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_run_kind ON events(run_id, kind);

-- Ingestion state table: offset tracking for incremental ingestion
CREATE TABLE IF NOT EXISTS ingestion_state (
    run_id VARCHAR PRIMARY KEY,
    last_offset INTEGER NOT NULL DEFAULT 0,
    last_seq INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT (now())
);

-- Facts table: inventory marker extraction (REQ_*, SOL_*, TRC_*, etc.)
CREATE SEQUENCE IF NOT EXISTS facts_id_seq;
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY DEFAULT nextval('facts_id_seq'),
    fact_id VARCHAR UNIQUE,
    run_id VARCHAR NOT NULL,
    step_id VARCHAR NOT NULL,
    flow_key VARCHAR NOT NULL,
    agent_key VARCHAR,
    marker_type VARCHAR,  -- REQ, SOL, TRC, ASM, DEC, etc.
    marker_id VARCHAR,    -- e.g., REQ_001
    fact_type VARCHAR,    -- requirement, solution, trace, assumption, decision
    content TEXT,
    priority VARCHAR,     -- MUST, SHOULD, NICE_TO_HAVE
    status VARCHAR,       -- verified, unverified, deprecated
    evidence TEXT,
    created_at TIMESTAMP,
    extracted_at TIMESTAMP DEFAULT (now()),
    metadata JSON,
    UNIQUE(run_id, step_id, marker_id)
);

CREATE INDEX IF NOT EXISTS idx_facts_run_id ON facts(run_id);
CREATE INDEX IF NOT EXISTS idx_facts_marker_type ON facts(run_id, marker_type);
CREATE INDEX IF NOT EXISTS idx_facts_marker_id ON facts(marker_id);

-- Routing decisions table: one row per routing decision after each step
CREATE SEQUENCE IF NOT EXISTS routing_decisions_id_seq;
CREATE TABLE IF NOT EXISTS routing_decisions (
    id INTEGER PRIMARY KEY DEFAULT nextval('routing_decisions_id_seq'),
    run_id VARCHAR NOT NULL,
    step_seq INTEGER NOT NULL,  -- Sequence number within the run
    flow_id VARCHAR NOT NULL,
    station_id VARCHAR NOT NULL,  -- Step/node that made the decision
    routing_mode VARCHAR,  -- deterministic, llm_tiebreak, etc.
    routing_source VARCHAR,  -- navigator/fast_path/deterministic_fallback
    chosen_candidate_id VARCHAR,  -- Selected edge ID
    candidate_count INTEGER DEFAULT 0,  -- Number of candidate edges evaluated
    decision VARCHAR NOT NULL,  -- advance/loop/repeat/detour/terminate/escalate
    target_node VARCHAR,  -- Next node to execute (nullable for terminate)
    timestamp TIMESTAMP NOT NULL,
    terminate BOOLEAN DEFAULT FALSE,  -- Whether flow should terminate
    needs_human BOOLEAN DEFAULT FALSE,  -- Whether human review is recommended
    explanation JSON,  -- Full structured explanation for audit trail
    UNIQUE(run_id, step_seq, station_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_routing_decisions_run_id ON routing_decisions(run_id);
CREATE INDEX IF NOT EXISTS idx_routing_decisions_flow ON routing_decisions(run_id, flow_id);
CREATE INDEX IF NOT EXISTS idx_routing_decisions_station ON routing_decisions(station_id);
CREATE INDEX IF NOT EXISTS idx_routing_decisions_decision ON routing_decisions(decision);
"""
