import type { SSEEvent } from "../api/client.js";
import type { FlowKey, CytoscapeInstance } from "../domain.js";
/**
 * Playback state
 */
type PlaybackState = "stopped" | "playing" | "paused";
/**
 * Routing decision for display
 */
interface RoutingDecision {
    timestamp: string;
    fromStep: string;
    toStep: string;
    reason: string;
    loopIteration?: number;
}
/**
 * Step output for display
 */
interface StepOutput {
    timestamp: string;
    stepId: string;
    agentKey?: string;
    status: "success" | "error";
    duration?: number;
    artifacts?: string[];
}
/**
 * Playback options
 */
interface RunPlaybackOptions {
    /** Cytoscape instance to animate */
    cy?: CytoscapeInstance;
    /** Container for output display */
    outputContainer?: HTMLElement;
    /** Container for routing decisions */
    routingContainer?: HTMLElement;
    /** Callback when step starts */
    onStepStart?: (event: SSEEvent) => void;
    /** Callback when step ends */
    onStepEnd?: (event: SSEEvent) => void;
    /** Callback when routing decision is made */
    onRoutingDecision?: (decision: RoutingDecision) => void;
    /** Callback when playback completes */
    onComplete?: () => void;
    /** Callback on error */
    onError?: (error: string) => void;
    /** Animation duration in ms */
    animationDuration?: number;
}
/**
 * Run playback component for real-time execution visualization.
 *
 * Features:
 * - SSE subscription for live events
 * - Node animation during execution
 * - Routing decision visualization
 * - Step output display
 * - Pause/resume/stop controls
 */
export declare class RunPlayback {
    private runId;
    private flowKey;
    private options;
    private unsubscribe;
    private playbackState;
    private events;
    private routingDecisions;
    private stepOutputs;
    private currentStepId;
    constructor(options?: RunPlaybackOptions);
    /**
     * Start playback for a run
     */
    start(runId: string, flowKey?: FlowKey): Promise<void>;
    /**
     * Pause playback (stop processing events but keep subscription)
     */
    pause(): void;
    /**
     * Resume paused playback
     */
    resume(): void;
    /**
     * Stop playback and clean up
     */
    stop(): void;
    /**
     * Get current playback state
     */
    getState(): PlaybackState;
    /**
     * Get all received events
     */
    getEvents(): SSEEvent[];
    /**
     * Get routing decisions
     */
    getRoutingDecisions(): RoutingDecision[];
    /**
     * Get step outputs
     */
    getStepOutputs(): StepOutput[];
    /**
     * Handle an incoming SSE event
     */
    private handleEvent;
    /**
     * Handle step_start event
     */
    private handleStepStart;
    /**
     * Handle step_end event
     */
    private handleStepEnd;
    /**
     * Handle routing_decision event
     */
    private handleRoutingDecision;
    /**
     * Handle artifact_created event
     */
    private handleArtifactCreated;
    /**
     * Handle complete event
     */
    private handleComplete;
    /**
     * Handle error event
     */
    private handleError;
    /**
     * Animate a node to a new state
     */
    private animateNode;
    /**
     * Animate an edge (highlight the path)
     */
    private animateEdge;
    /**
     * Focus the view on a node
     */
    private focusNode;
    /**
     * Reset all nodes to idle state
     */
    private resetNodeStates;
    /**
     * Render a step output to the output container
     */
    private renderStepOutput;
    /**
     * Render a routing decision to the routing container
     */
    private renderRoutingDecision;
    /**
     * Clear all output displays
     */
    clearOutputs(): void;
    /**
     * Destroy the playback component
     */
    destroy(): void;
}
/**
 * Create a new run playback instance
 */
export declare function createRunPlayback(options?: RunPlaybackOptions): RunPlayback;
export {};
/**
 * CSS class names used by this component:
 *
 * Node animation:
 * - .node-running - Pulsing animation for running nodes
 *
 * Output display:
 * - .playback-output - Output item container
 * - .playback-output--success - Success state
 * - .playback-output--error - Error state
 * - .playback-output__icon - Status icon
 * - .playback-output__step - Step ID
 * - .playback-output__agent - Agent key
 * - .playback-output__duration - Duration text
 *
 * Routing display:
 * - .playback-routing - Routing item container
 * - .playback-routing__header - Header with from/to/arrow
 * - .playback-routing__from - Source step
 * - .playback-routing__arrow - Arrow indicator
 * - .playback-routing__to - Target step
 * - .playback-routing__iteration - Loop iteration badge
 * - .playback-routing__reason - Decision reason
 */
