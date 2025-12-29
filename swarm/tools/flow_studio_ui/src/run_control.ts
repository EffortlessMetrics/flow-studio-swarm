// swarm/tools/flow_studio_ui/src/run_control.ts
// Run Control panel module for Flow Studio
//
// This module handles:
// - Starting, pausing, resuming, and canceling runs
// - Run state management and UI updates
// - Integration with the API client

import { flowStudioApi, type RunState, type RunInfo, type SSEEvent } from "./api/client.js";
import { state } from "./state.js";
import type { FlowKey } from "./domain.js";

// ============================================================================
// Types
// ============================================================================

/**
 * Run control state
 */
interface RunControlState {
  /** Current run ID being controlled */
  activeRunId: string | null;
  /** Current run state */
  runState: RunState;
  /** Current step being executed */
  currentStep: string | null;
  /** Progress percentage (0-100) */
  progress: number;
  /** Error message if any */
  error: string | null;
  /** Whether an action is in progress */
  isLoading: boolean;
  /** Unsubscribe function for SSE */
  unsubscribe: (() => void) | null;
  /** ETag for optimistic locking */
  etag: string | null;
}

/**
 * Callbacks for run control events
 */
export interface RunControlCallbacks {
  /** Called when a run starts */
  onRunStart?: (runId: string) => void;
  /** Called when a run state changes */
  onStateChange?: (state: RunState, runId: string) => void;
  /** Called when a run completes */
  onRunComplete?: (runId: string) => void;
  /** Called when a run fails */
  onRunFailed?: (runId: string, error: string) => void;
  /** Called when run needs to be selected in the UI */
  onSelectRun?: (runId: string) => Promise<void>;
}

// ============================================================================
// Module State
// ============================================================================

const _state: RunControlState = {
  activeRunId: null,
  runState: "pending",
  currentStep: null,
  progress: 0,
  error: null,
  isLoading: false,
  unsubscribe: null,
  etag: null,
};

let _callbacks: RunControlCallbacks = {};

// ============================================================================
// Configuration
// ============================================================================

/**
 * Configure callbacks for run control events.
 */
export function configure(callbacks: RunControlCallbacks = {}): void {
  _callbacks = { ..._callbacks, ...callbacks };
}

// ============================================================================
// State Accessors
// ============================================================================

/**
 * Get the current run control state.
 */
export function getRunControlState(): Readonly<RunControlState> {
  return { ..._state };
}

/**
 * Check if there's an active run.
 */
export function hasActiveRun(): boolean {
  return _state.activeRunId !== null &&
         (_state.runState === "running" || _state.runState === "paused");
}

// ============================================================================
// Run Control Actions
// ============================================================================

/**
 * Start a new run.
 *
 * @param flowId - Flow ID to run (defaults to current flow)
 * @param options - Optional run configuration
 */
export async function startRun(
  flowId?: string,
  options?: {
    runId?: string;
    context?: Record<string, unknown>;
    startStep?: string;
    mode?: "execute" | "preview" | "validate";
  }
): Promise<void> {
  if (_state.isLoading) return;

  const targetFlowId = flowId || state.currentFlowKey || "signal";

  _state.isLoading = true;
  _state.error = null;
  updateUI();

  try {
    const runInfo = await flowStudioApi.startRun(targetFlowId, options);

    _state.activeRunId = runInfo.run_id;
    _state.runState = runInfo.state || "running";
    _state.currentStep = runInfo.currentStep || null;
    _state.progress = runInfo.progress || 0;
    _state.isLoading = false;

    // Subscribe to run events
    subscribeToRunEvents(runInfo.run_id);

    if (_callbacks.onRunStart) {
      _callbacks.onRunStart(runInfo.run_id);
    }

    if (_callbacks.onSelectRun) {
      await _callbacks.onSelectRun(runInfo.run_id);
    }

    updateUI();
  } catch (err) {
    _state.isLoading = false;
    _state.error = (err as Error).message || "Failed to start run";
    console.error("Failed to start run", err);
    updateUI();
  }
}

/**
 * Pause the current run.
 */
export async function pauseRun(): Promise<void> {
  if (!_state.activeRunId || _state.isLoading || _state.runState !== "running") {
    return;
  }

  _state.isLoading = true;
  updateUI();

  try {
    await flowStudioApi.pauseRun(_state.activeRunId, _state.etag || undefined);
    _state.runState = "paused";
    _state.isLoading = false;

    if (_callbacks.onStateChange) {
      _callbacks.onStateChange("paused", _state.activeRunId);
    }

    updateUI();
  } catch (err) {
    _state.isLoading = false;
    _state.error = (err as Error).message || "Failed to pause run";
    console.error("Failed to pause run", err);
    updateUI();
  }
}

/**
 * Resume the current paused run.
 */
export async function resumeRun(): Promise<void> {
  if (!_state.activeRunId || _state.isLoading || _state.runState !== "paused") {
    return;
  }

  _state.isLoading = true;
  updateUI();

  try {
    await flowStudioApi.resumeRun(_state.activeRunId, _state.etag || undefined);
    _state.runState = "running";
    _state.isLoading = false;

    if (_callbacks.onStateChange) {
      _callbacks.onStateChange("running", _state.activeRunId);
    }

    updateUI();
  } catch (err) {
    _state.isLoading = false;
    _state.error = (err as Error).message || "Failed to resume run";
    console.error("Failed to resume run", err);
    updateUI();
  }
}

/**
 * Cancel the current run.
 */
export async function cancelRun(): Promise<void> {
  if (!_state.activeRunId || _state.isLoading) {
    return;
  }

  // Only allow cancel if running or paused
  if (_state.runState !== "running" && _state.runState !== "paused") {
    return;
  }

  _state.isLoading = true;
  updateUI();

  try {
    await flowStudioApi.cancelRun(_state.activeRunId, _state.etag || undefined);

    const runId = _state.activeRunId;

    // Unsubscribe from events
    if (_state.unsubscribe) {
      _state.unsubscribe();
      _state.unsubscribe = null;
    }

    _state.runState = "failed";
    _state.isLoading = false;
    _state.error = "Run canceled";

    if (_callbacks.onRunFailed) {
      _callbacks.onRunFailed(runId, "Run canceled by user");
    }

    // Reset after a short delay
    setTimeout(() => {
      resetState();
      updateUI();
    }, 2000);

    updateUI();
  } catch (err) {
    _state.isLoading = false;
    _state.error = (err as Error).message || "Failed to cancel run";
    console.error("Failed to cancel run", err);
    updateUI();
  }
}

// ============================================================================
// SSE Subscription
// ============================================================================

/**
 * Subscribe to run events via SSE.
 */
function subscribeToRunEvents(runId: string): void {
  // Clean up existing subscription
  if (_state.unsubscribe) {
    _state.unsubscribe();
  }

  _state.unsubscribe = flowStudioApi.subscribeToRun(runId, handleSSEEvent);
}

/**
 * Handle incoming SSE events.
 */
function handleSSEEvent(event: SSEEvent): void {
  switch (event.type) {
    case "step_start":
      _state.currentStep = event.stepId || null;
      break;

    case "step_end":
      // Calculate progress based on completed steps
      if (event.payload?.progress !== undefined) {
        _state.progress = event.payload.progress as number;
      }
      break;

    case "complete":
      _state.runState = "completed";
      _state.progress = 100;
      if (_state.unsubscribe) {
        _state.unsubscribe();
        _state.unsubscribe = null;
      }
      if (_callbacks.onRunComplete && _state.activeRunId) {
        _callbacks.onRunComplete(_state.activeRunId);
      }
      break;

    case "error":
      _state.runState = "failed";
      _state.error = (event.payload?.error as string) || "Run failed";
      if (_state.unsubscribe) {
        _state.unsubscribe();
        _state.unsubscribe = null;
      }
      if (_callbacks.onRunFailed && _state.activeRunId) {
        _callbacks.onRunFailed(_state.activeRunId, _state.error);
      }
      break;
  }

  updateUI();
}

// ============================================================================
// State Management
// ============================================================================

/**
 * Reset the run control state.
 */
function resetState(): void {
  if (_state.unsubscribe) {
    _state.unsubscribe();
  }

  _state.activeRunId = null;
  _state.runState = "pending";
  _state.currentStep = null;
  _state.progress = 0;
  _state.error = null;
  _state.isLoading = false;
  _state.unsubscribe = null;
  _state.etag = null;
}

/**
 * Set the active run to monitor (for existing runs).
 */
export async function setActiveRun(runId: string): Promise<void> {
  if (_state.activeRunId === runId) return;

  // Clean up existing subscription
  if (_state.unsubscribe) {
    _state.unsubscribe();
    _state.unsubscribe = null;
  }

  try {
    const { data, etag } = await flowStudioApi.getRunState(runId);

    _state.activeRunId = runId;
    _state.runState = data.status as RunState;
    _state.currentStep = data.current_step;
    _state.etag = etag;
    _state.error = data.error;

    // Subscribe to events if run is active
    if (_state.runState === "running" || _state.runState === "paused") {
      subscribeToRunEvents(runId);
    }

    updateUI();
  } catch (err) {
    console.error("Failed to get run state", err);
    // Run might not exist in backend - just show idle state
    resetState();
    updateUI();
  }
}

/**
 * Clear the active run (e.g., when selecting a different run in the UI).
 */
export function clearActiveRun(): void {
  resetState();
  updateUI();
}

// ============================================================================
// UI Updates
// ============================================================================

/**
 * Update the run control UI based on current state.
 */
function updateUI(): void {
  const playBtn = document.getElementById("run-control-play") as HTMLButtonElement | null;
  const pauseBtn = document.getElementById("run-control-pause") as HTMLButtonElement | null;
  const resumeBtn = document.getElementById("run-control-resume") as HTMLButtonElement | null;
  const cancelBtn = document.getElementById("run-control-cancel") as HTMLButtonElement | null;
  const statusText = document.getElementById("run-control-status-text");
  const statusContainer = document.getElementById("run-control-status");

  if (!playBtn || !pauseBtn || !resumeBtn || !cancelBtn || !statusText || !statusContainer) {
    return;
  }

  // Remove all state classes
  statusContainer.classList.remove(
    "run-control-status--pending",
    "run-control-status--running",
    "run-control-status--paused",
    "run-control-status--completed",
    "run-control-status--failed"
  );

  // Handle loading state
  if (_state.isLoading) {
    playBtn.disabled = true;
    pauseBtn.disabled = true;
    resumeBtn.disabled = true;
    cancelBtn.disabled = true;
    statusText.textContent = "Processing...";
    statusText.className = "run-control-status-text run-control-status-text--loading";
    return;
  }

  // Update based on run state
  switch (_state.runState) {
    case "pending":
      // No active run - can start
      playBtn.disabled = false;
      playBtn.style.display = "";
      pauseBtn.disabled = true;
      pauseBtn.style.display = "";
      resumeBtn.style.display = "none";
      cancelBtn.disabled = true;
      statusText.textContent = "No active run";
      statusText.className = "muted";
      statusContainer.classList.add("run-control-status--pending");
      break;

    case "running":
      // Run in progress - can pause or cancel
      playBtn.disabled = true;
      playBtn.style.display = "";
      pauseBtn.disabled = false;
      pauseBtn.style.display = "";
      resumeBtn.style.display = "none";
      cancelBtn.disabled = false;
      statusText.textContent = _state.currentStep
        ? `Running: ${_state.currentStep}`
        : "Running...";
      statusText.className = "run-control-status-text run-control-status-text--running";
      statusContainer.classList.add("run-control-status--running");
      break;

    case "paused":
      // Run paused - can resume or cancel
      playBtn.style.display = "none";
      pauseBtn.style.display = "none";
      resumeBtn.disabled = false;
      resumeBtn.style.display = "";
      cancelBtn.disabled = false;
      statusText.textContent = _state.currentStep
        ? `Paused at: ${_state.currentStep}`
        : "Paused";
      statusText.className = "run-control-status-text run-control-status-text--paused";
      statusContainer.classList.add("run-control-status--paused");
      break;

    case "completed":
      // Run completed - can start new
      playBtn.disabled = false;
      playBtn.style.display = "";
      pauseBtn.disabled = true;
      pauseBtn.style.display = "";
      resumeBtn.style.display = "none";
      cancelBtn.disabled = true;
      statusText.textContent = "Completed";
      statusText.className = "run-control-status-text run-control-status-text--completed";
      statusContainer.classList.add("run-control-status--completed");
      break;

    case "failed":
      // Run failed - can start new
      playBtn.disabled = false;
      playBtn.style.display = "";
      pauseBtn.disabled = true;
      pauseBtn.style.display = "";
      resumeBtn.style.display = "none";
      cancelBtn.disabled = true;
      statusText.textContent = _state.error || "Failed";
      statusText.className = "run-control-status-text run-control-status-text--failed";
      statusContainer.classList.add("run-control-status--failed");
      break;
  }

  // Add progress indicator if running
  if (_state.runState === "running" && _state.progress > 0) {
    const progressBar = statusContainer.querySelector(".run-control-progress");
    if (progressBar) {
      (progressBar as HTMLElement).style.width = `${_state.progress}%`;
    }
  }
}

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize the run control panel.
 * Call this during app initialization to wire up event handlers.
 */
export function initRunControl(): void {
  const playBtn = document.getElementById("run-control-play");
  const pauseBtn = document.getElementById("run-control-pause");
  const resumeBtn = document.getElementById("run-control-resume");
  const cancelBtn = document.getElementById("run-control-cancel");

  if (playBtn) {
    playBtn.addEventListener("click", () => {
      void startRun();
    });
  }

  if (pauseBtn) {
    pauseBtn.addEventListener("click", () => {
      void pauseRun();
    });
  }

  if (resumeBtn) {
    resumeBtn.addEventListener("click", () => {
      void resumeRun();
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      void cancelRun();
    });
  }

  // Initial UI update
  updateUI();
}

// ============================================================================
// Exports for SDK
// ============================================================================

export {
  startRun as start,
  pauseRun as pause,
  resumeRun as resume,
  cancelRun as cancel,
};
