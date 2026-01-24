// AUTO-GENERATED from swarm/config/flows.yaml
// Do not edit manually. Run: make gen-flow-constants

/** Canonical flow ordering in SDLC sequence */
export const FLOW_KEYS = ["signal", "plan", "build", "review", "gate", "deploy", "wisdom", "reset", "stepwise-demo"] as const;

/** Valid flow keys derived from FLOW_KEYS constant */
export type FlowKey = typeof FLOW_KEYS[number];

/** Flow key to numeric index (1-9) */
export const FLOW_INDEX: Record<FlowKey, number> = {
  signal: 1,
  plan: 2,
  build: 3,
  review: 4,
  gate: 5,
  deploy: 6,
  wisdom: 7,
  reset: 8,
  "stepwise-demo": 9,
};

/** Flow key to display title */
export const FLOW_TITLES: Record<FlowKey, string> = {
  signal: "Signal",
  plan: "Plan",
  build: "Build",
  review: "Review",
  gate: "Gate",
  deploy: "Deploy",
  wisdom: "Wisdom",
  reset: "Reset",
  "stepwise-demo": "Stepwise",
};

/** Flow key to description */
export const FLOW_DESCRIPTIONS: Record<FlowKey, string> = {
  signal: "Raw input to problem statement, requirements, BDD scenarios, early risk assessment",
  plan: "Requirements to ADR, contracts, observability spec, test/work plans, design validation",
  build: "Implement via adversarial microloops, build code and tests, self-verify, produce receipts",
  review: "Harvest PR feedback, cluster into actionable items, apply fixes, flip Draft to Ready",
  gate: "Pre-merge gate, audit receipts, check contracts/security/policy, recommend merge or bounce",
  deploy: "Move approved artifact to production, execute deployment, verify health, create audit trail",
  wisdom: "Analyze artifacts, detect regressions, extract learnings, close feedback loops",
  reset: "Branch synchronization, cleanup, and run archiving. Injected when work branch diverges from upstream.",
  "stepwise-demo": "A 10-step demo flow for testing stepwise execution backends",
};
