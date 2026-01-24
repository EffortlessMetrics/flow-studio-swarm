/** Canonical flow ordering in SDLC sequence */
export declare const FLOW_KEYS: readonly ["signal", "plan", "build", "review", "gate", "deploy", "wisdom", "reset", "stepwise-demo"];
/** Valid flow keys derived from FLOW_KEYS constant */
export type FlowKey = typeof FLOW_KEYS[number];
/** Flow key to numeric index (1-9) */
export declare const FLOW_INDEX: Record<FlowKey, number>;
/** Flow key to display title */
export declare const FLOW_TITLES: Record<FlowKey, string>;
/** Flow key to description */
export declare const FLOW_DESCRIPTIONS: Record<FlowKey, string>;
