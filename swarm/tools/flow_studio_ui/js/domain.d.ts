/**
 * Flow Studio Domain Types
 *
 * These types define the core data structures used throughout Flow Studio.
 * They serve as the contract between:
 * - Python backend (FastAPI endpoints)
 * - JavaScript frontend (browser modules)
 * - Tests and tooling
 *
 * Usage in JS files:
 *   /** @typedef {import("./domain").FlowGraph} FlowGraph *\/
 *   /** @param {FlowGraph} graph *\/
 *   export function renderGraph(graph) { ... }
 */

// ============================================================================
// Flow Keys & Constants
// ============================================================================

/** Valid flow keys in the SDLC */
export type FlowKey = "signal" | "plan" | "build" | "gate" | "deploy" | "wisdom";

/** Run types distinguish examples from active work */
export type RunType = "example" | "active";

/** Status values for steps/artifacts */
export type StepStatus = "done" | "in_progress" | "not_started" | "complete" | "partial" | "missing" | "n/a";

/** Artifact presence status */
export type ArtifactStatus = "present" | "missing" | "unknown";

/** UI mode for author vs operator views */
export type UIMode = "author" | "operator";

/** View mode for graph display */
export type ViewMode = "agents" | "artifacts";

// ============================================================================
// Graph Data (Cytoscape)
// ============================================================================

/** Node types in the flow graph */
export type NodeType = "step" | "agent" | "artifact";

/** Edge types connecting nodes */
export type EdgeType = "step-sequence" | "step-agent" | "step-artifact";

/** A node in the flow graph */
export interface FlowGraphNode {
  /** Cytoscape element wrapper */
  data: {
    id: string;
    type: NodeType;
    label: string;
    flow?: FlowKey;
    step_id?: string | null;
    agent_key?: string | null;
    order?: number | null;
    color?: string | null;
    status?: ArtifactStatus | null;
    is_decision?: boolean;
  };
}

/** An edge in the flow graph */
export interface FlowGraphEdge {
  data: {
    id: string;
    type: EdgeType;
    source: string;
    target: string;
  };
}

/** Graph data returned by /api/graph/:flow endpoints */
export interface FlowGraph {
  nodes: FlowGraphNode[];
  edges: FlowGraphEdge[];
}

/** Serialized graph state from getCurrentGraphState() */
export interface GraphState {
  version: "flow_graph.v1";
  flow_key: FlowKey | null;
  run_id: string | null;
  view_mode: ViewMode;
  timestamp: string;
  nodes: SerializedNode[];
  edges: SerializedEdge[];
}

/** Flattened node for serialization (no `data` wrapper) */
export interface SerializedNode {
  id: string;
  type: NodeType;
  label: string;
  flow?: FlowKey;
  step_id?: string | null;
  order?: number | null;
  color?: string | null;
  status?: ArtifactStatus | null;
}

/** Flattened edge for serialization */
export interface SerializedEdge {
  id: string;
  type: EdgeType;
  source: string;
  target: string;
}

/** Node data passed to click handlers (flattened from Cytoscape) */
export interface NodeData {
  id: string;
  type: NodeType;
  label: string;
  flow?: FlowKey;
  step_id?: string;
  agent_key?: string;
  order?: number;
  color?: string;
  status?: ArtifactStatus;
  is_decision?: boolean;
}

// ============================================================================
// Runs API
// ============================================================================

/** A run entry from /api/runs */
export interface Run {
  run_id: string;
  run_type: RunType;
  title?: string;
  description?: string;
  created_at?: string;
}

/** Response from /api/runs */
export interface RunsResponse {
  runs: Run[];
}

/** Step status within a flow */
export interface StepStatusData {
  status: StepStatus;
  artifacts?: Record<string, ArtifactStatus>;
}

/** Flow status within a run */
export interface FlowStatusData {
  status: StepStatus;
  steps: Record<string, StepStatusData>;
}

/** Response from /api/runs/:id/summary */
export interface RunSummary {
  run_id: string;
  title?: string;
  flows: Record<FlowKey, FlowStatusData>;
}

/** Timeline event from /api/runs/:id/timeline */
export interface TimelineEvent {
  timestamp: string;
  flow: FlowKey;
  step_id: string;
  event_type: string;
  message?: string;
}

/** Response from /api/runs/:id/timeline */
export interface RunTimeline {
  events: TimelineEvent[];
}

// ============================================================================
// Flows API
// ============================================================================

/** A flow entry from /api/flows */
export interface Flow {
  key: FlowKey;
  title: string;
  description?: string;
  step_count: number;
}

/** Response from /api/flows */
export interface FlowsResponse {
  flows: Flow[];
}

/** Step definition within a flow */
export interface FlowStep {
  id: string;
  order: number;
  role: string;
  agents: string[];
  artifacts?: string[];
  human_only?: boolean;
}

/** Response from /api/flows/:key */
export interface FlowDetail {
  key: FlowKey;
  title: string;
  description?: string;
  steps: FlowStep[];
  agents: string[];
}

// ============================================================================
// Comparison API
// ============================================================================

/** Step comparison data */
export interface StepComparison {
  step_id: string;
  run_a: { status: StepStatus };
  run_b: { status: StepStatus };
  change: "improved" | "regressed" | "unchanged";
}

/** Response from /api/runs/compare */
export interface ComparisonData {
  run_a: string;
  run_b: string;
  flow: FlowKey;
  summary: {
    improved: number;
    regressed: number;
    unchanged: number;
  };
  steps: StepComparison[];
}

// ============================================================================
// Search API
// ============================================================================

/** Search result types */
export type SearchResultType = "flow" | "step" | "agent" | "artifact";

/** A single search result */
export interface SearchResult {
  type: SearchResultType;
  id: string;
  label: string;
  flow?: FlowKey;
  step_id?: string;
  agent_key?: string;
  score?: number;
}

/** Response from /api/search */
export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

// ============================================================================
// Governance & Validation
// ============================================================================

/** FR check result */
export interface FRCheck {
  status: "pass" | "fail" | "warn";
  message?: string;
  fix?: string;
}

/** Agent validation data */
export interface AgentValidation {
  file: string;
  checks: Record<string, FRCheck>;
  has_issues: boolean;
  has_warnings: boolean;
  issues?: Array<{
    error_type: string;
    problem: string;
    fix_action: string;
  }>;
}

/** Flow validation data */
export interface FlowValidation {
  file: string;
  checks: Record<string, FRCheck>;
  has_issues: boolean;
  has_warnings: boolean;
  issues?: Array<{
    error_type: string;
    problem: string;
    fix_action: string;
  }>;
}

/** Step extraction data from validation */
export interface StepValidation {
  id: string;
  agents: string[];
  role: string;
  human_only: boolean;
  line: number;
}

/** Skill validation data */
export interface SkillValidation {
  file: string;
  valid: boolean;
  issues?: Array<{
    error_type: string;
    problem: string;
    fix_action: string;
  }>;
}

/** Response from /api/validation */
export interface ValidationData {
  version: string;
  timestamp: string;
  summary: {
    status: "PASS" | "FAIL";
    total_checks: number;
    passed: number;
    failed: number;
    warnings: number;
    agents_with_issues: string[];
    flows_with_issues: string[];
    steps_with_issues: string[];
  };
  agents: Record<string, AgentValidation>;
  flows: Record<string, FlowValidation>;
  steps: Record<string, StepValidation[]>;
  skills: Record<string, SkillValidation>;
}

/** Kernel status in governance */
export interface KernelStatus {
  status: "HEALTHY" | "BROKEN" | "unknown";
  error?: string;
}

/**
 * Normalized selftest status using the 4-state model.
 * The API may return legacy values (GREEN/YELLOW/RED/UNKNOWN) which should be
 * normalized to this model in the UI layer.
 */
export type NormalizedSelftestStatus = "ok" | "warning" | "error" | "unknown";

/**
 * Legacy selftest status values from the API.
 * These are converted to NormalizedSelftestStatus in the UI layer.
 */
export type LegacySelftestStatus = "GREEN" | "YELLOW" | "RED" | "UNKNOWN";

/** Selftest results in governance */
export interface SelftestStatus {
  status: LegacySelftestStatus | NormalizedSelftestStatus;
  mode: "strict" | "degraded" | "kernel-only" | "unknown";
  kernel_ok: boolean;
  governance_ok: boolean;
  optional_ok: boolean;
  failed_steps: string[];
  degraded_steps: string[];
  degradations?: Array<{
    step_id: string;
    severity: "CRITICAL" | "WARNING" | "INFO";
    timestamp: string;
    message: string;
    remediation?: string;
  }>;
  critical_passed?: number;
  critical_failed?: number;
  warning_passed?: number;
  warning_failed?: number;
  info_passed?: number;
  info_failed?: number;
}

/** Agent stats in governance */
export interface AgentStats {
  total: number;
  by_status: {
    healthy: number;
    invalid?: number;
  };
  invalid_agents?: string[];
}

/** Flow stats in governance */
export interface FlowStats {
  total: number;
  healthy: number;
  invalid_flows?: string[];
}

/** Response from /platform/status */
export interface GovernanceStatus {
  timestamp: string;
  governance: {
    kernel: KernelStatus;
    selftest: SelftestStatus;
  };
  agents: AgentStats;
  flows: FlowStats;
  hints?: {
    summary?: string;
    detailed?: string;
  };
}

// ============================================================================
// Selftest API
// ============================================================================

/** Selftest tier levels */
export type SelftestTier = "kernel" | "governance" | "optional";

/** A step in the selftest plan */
export interface SelftestStep {
  id: string;
  tier: SelftestTier;
  severity: "critical" | "warning" | "info";
  category: string;
  description?: string;
  depends_on: string[];
  ac_ids?: string[];
}

/** Response from /api/selftest/plan */
export interface SelftestPlan {
  steps: SelftestStep[];
  summary: {
    total: number;
    by_tier: {
      kernel: number;
      governance: number;
      optional: number;
    };
  };
}

// ============================================================================
// Tours API
// ============================================================================

/** A tour step */
export interface TourStep {
  target: string;
  title: string;
  content: string;
  position?: "top" | "bottom" | "left" | "right";
}

/** A tour definition */
export interface Tour {
  id: string;
  title: string;
  description?: string;
  steps: TourStep[];
}

/** Response from /api/tours */
export interface ToursResponse {
  tours: Tour[];
}

// ============================================================================
// UI State
// ============================================================================

/** The global UI state object shape */
export interface UIState {
  // Cytoscape instance (typed as `any` since Cytoscape has its own types)
  cy: any | null;

  // Current selection
  currentFlowKey: FlowKey | null;
  currentRunId: string | null;
  compareRunId: string | null;

  // Cached API data
  runStatus: Partial<RunSummary>;
  comparisonData: ComparisonData | null;
  availableRuns: Run[];

  // Governance state
  governanceStatus: GovernanceStatus | null;
  validationData: ValidationData | null;
  governanceOverlayEnabled: boolean;

  // UI mode
  currentMode: UIMode;
  currentViewMode: ViewMode;

  // Search state
  searchDebounceTimer: ReturnType<typeof setTimeout> | null;
  searchSelectedIndex: number;
  searchResults: SearchResult[];

  // Navigation
  currentStepIndex: number;

  // Selftest state
  selftestPlan: SelftestPlan | null;
  selftestPlanCache: SelftestPlan | null;
}

/** Status icons mapping */
export interface StatusIcons {
  done: string;
  in_progress: string;
  not_started: string;
  complete: string;
  partial: string;
  missing: string;
  "n/a": string;
}

// ============================================================================
// Module Callback Types
// ============================================================================

/** Callbacks for runs_flows module configuration */
export interface RunsFlowsCallbacks {
  onFlowDetails?: (detail: FlowDetail) => void;
  onNodeClick?: (nodeData: NodeData) => void;
  onURLUpdate?: () => void;
  updateFlowListGovernance?: () => void;
}

/** Options for graph rendering */
export interface RenderGraphOptions {
  onNodeClick?: (nodeData: NodeData) => void;
}

/** Options for focus node animation */
export interface FocusNodeOptions {
  padding?: number;
}

// ============================================================================
// Resolution Hints
// ============================================================================

/** A resolution hint for governance issues */
export interface ResolutionHint {
  type: "failure" | "advisory" | "workaround";
  step?: string;
  root_cause: string;
  command: string;
  docs: string;
}

// ============================================================================
// Boundary Review API
// ============================================================================

/** Summary of an assumption made during execution */
export interface AssumptionSummary {
  assumption_id: string;
  statement: string;
  rationale: string;
  impact_if_wrong: string;
  confidence: "high" | "medium" | "low";
  status: "active" | "resolved" | "invalidated";
  tags: string[];
  flow_introduced?: string;
  step_introduced?: string;
  agent?: string;
  timestamp?: string;
}

/** Summary of a decision made during execution */
export interface DecisionSummary {
  decision_id: string;
  decision_type: string;
  subject: string;
  decision: string;
  rationale: string;
  supporting_evidence: string[];
  conditions: string[];
  assumptions_applied: string[];
  flow?: string;
  step?: string;
  agent?: string;
  timestamp?: string;
}

/** Summary of a detour taken during execution */
export interface DetourSummary {
  detour_id: string;
  from_step: string;
  to_step: string;
  reason: string;
  detour_type: string;
  evidence_path?: string;
  timestamp?: string;
}

/** Verification result for a step */
export interface VerificationSummary {
  step_id: string;
  station_id?: string;
  status: string;
  verified: boolean;
  can_further_iteration_help?: boolean;
  issues: string[];
  timestamp?: string;
}

/** Inventory marker delta */
export interface InventoryDelta {
  marker_type: string;
  label: string;
  count: number;
  delta: number;
}

/** Response from /api/runs/:id/boundary-review */
export interface BoundaryReviewResponse {
  run_id: string;
  scope: "flow" | "run";
  current_flow?: FlowKey;

  assumptions_count: number;
  assumptions_high_risk: number;
  assumptions: AssumptionSummary[];

  decisions_count: number;
  decisions: DecisionSummary[];

  detours_count: number;
  detours: DetourSummary[];

  verification_passed: number;
  verification_failed: number;
  verifications: VerificationSummary[];

  inventory_deltas: InventoryDelta[];

  has_evolution_patches: boolean;
  evolution_patch_count: number;

  confidence_score: number;
  uncertainty_notes: string[];

  timestamp: string;
}

// ============================================================================
// Backends API
// ============================================================================

/** Backend capability flags */
export interface BackendCapabilities {
  supports_stepwise: boolean;
  supports_stream: boolean;
  supports_stub: boolean;
}

/** A backend option for execution */
export interface BackendOption {
  id: string;
  name: string;
  description: string;
  capabilities: BackendCapabilities;
  requires_env?: string[];
}

/** Response from /api/backends */
export interface BackendsResponse {
  backends: BackendOption[];
  default_backend: string;
}

// ============================================================================
// Run Events API
// ============================================================================

/** A structured event from run execution */
export interface RunEvent {
  event: string;
  timestamp: string;
  flow_key?: FlowKey;
  step_id?: string;
  station_id?: string;
  data?: Record<string, unknown>;
}

/** Response from /api/runs/:id/events (JSON mode) */
export interface RunEventsResponse {
  run_id: string;
  events: RunEvent[];
}

// ============================================================================
// Transcript & Receipt API
// ============================================================================

/** LLM message in a transcript */
export interface TranscriptMessage {
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp?: string;
  tool_calls?: unknown[];
}

/** Response from /api/runs/:id/flows/:flow/steps/:step/transcript */
export interface StepTranscriptResponse {
  run_id: string;
  flow_key: FlowKey;
  step_id: string;
  messages: TranscriptMessage[];
  token_count?: number;
}

/** Response from /api/runs/:id/flows/:flow/steps/:step/receipt */
export interface StepReceiptResponse {
  run_id: string;
  flow_key: FlowKey;
  step_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  input_tokens?: number;
  output_tokens?: number;
  error?: string;
}

// ============================================================================
// Wisdom API
// ============================================================================

/** Flow status entry in wisdom summary */
export interface WisdomFlowStatus {
  flow_key: FlowKey;
  status: "complete" | "partial" | "missing";
  step_count: number;
  verified_count: number;
}

/** Wisdom summary for a run */
export interface WisdomSummary {
  run_id: string;
  flows: WisdomFlowStatus[];
  total_assumptions: number;
  total_decisions: number;
  high_risk_assumptions: number;
  has_learnings: boolean;
  has_evolution_patches: boolean;
  labels: string[];
  key_artifacts: string[];
}
