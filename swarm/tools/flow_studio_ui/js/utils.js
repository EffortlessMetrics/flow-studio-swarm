// swarm/tools/flow_studio_ui/src/utils.ts
// Utility functions for Flow Studio
// ============================================================================
// Time and Duration Formatting
// ============================================================================
/**
 * Format duration in seconds to human-readable form
 */
export function formatDuration(seconds) {
    if (seconds == null)
        return "—";
    if (seconds < 60)
        return `${Math.round(seconds)}s`;
    if (seconds < 3600)
        return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
}
/**
 * Format ISO timestamp to time only (HH:MM)
 */
export function formatTime(isoString) {
    if (!isoString)
        return "—";
    const d = new Date(isoString);
    return d.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    });
}
/**
 * Format ISO timestamp to date + time
 */
export function formatDateTime(isoString) {
    if (!isoString)
        return "—";
    const d = new Date(isoString);
    return (d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
        " " +
        d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }));
}
// ============================================================================
// HTML Utilities
// ============================================================================
/**
 * Escape HTML special characters to prevent XSS
 */
export function escapeHtml(text) {
    if (!text)
        return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
// ============================================================================
// Clipboard Utilities
// ============================================================================
/**
 * Copy text to clipboard
 */
export function copyToClipboard(text) {
    return navigator.clipboard.writeText(text).catch(err => {
        console.error("Copy failed", err);
    });
}
/**
 * Create a copy button element
 */
export function createCopyButton(text, label = "Copy") {
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = label;
    btn.title = "Copy to clipboard";
    btn.setAttribute("aria-label", "Copy to clipboard");
    btn.addEventListener("click", () => {
        void copyToClipboard(text);
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => {
            btn.textContent = label;
            btn.classList.remove("copied");
        }, 1500);
    });
    return btn;
}
/**
 * Create a path display with copy button
 */
export function createPathWithCopy(path) {
    const container = document.createElement("div");
    container.className = "path-with-copy";
    const pathSpan = document.createElement("span");
    pathSpan.className = "mono";
    pathSpan.textContent = path;
    container.appendChild(pathSpan);
    container.appendChild(createCopyButton(path, "Copy"));
    return container;
}
/**
 * Create quick commands section with copy buttons
 */
export function createQuickCommands(commands) {
    const container = document.createElement("div");
    container.className = "quick-commands";
    const label = document.createElement("div");
    label.className = "kv-label";
    label.textContent = "Quick commands";
    container.appendChild(label);
    commands.forEach(cmd => {
        const line = document.createElement("div");
        line.className = "command-line";
        const cmdText = document.createElement("span");
        cmdText.className = "command-text";
        cmdText.textContent = "$ " + cmd;
        line.appendChild(cmdText);
        line.appendChild(createCopyButton(cmd, "Copy"));
        container.appendChild(line);
    });
    return container;
}
// ============================================================================
// Focus Trap Utilities
// ============================================================================
/**
 * Selector for focusable elements
 */
const FOCUSABLE_SELECTOR = [
    "a[href]",
    "button:not([disabled])",
    "input:not([disabled])",
    "textarea:not([disabled])",
    "select:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
    "[contenteditable]"
].join(", ");
/**
 * Get all focusable elements within a container
 */
export function getFocusableElements(container) {
    return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
        .filter(el => el.offsetParent !== null); // Filter out hidden elements
}
/**
 * Create a focus trap within a container.
 *
 * - Traps Tab/Shift+Tab to cycle within the container
 * - Moves focus into the container on creation
 * - Returns cleanup function to remove the trap
 *
 * @param container - The element to trap focus within
 * @param initialFocusEl - Element to focus initially (defaults to first focusable)
 */
export function createFocusTrap(container, initialFocusEl) {
    const focusableElements = getFocusableElements(container);
    // Focus initial element or first focusable
    if (initialFocusEl && focusableElements.includes(initialFocusEl)) {
        initialFocusEl.focus();
    }
    else if (focusableElements.length > 0) {
        focusableElements[0].focus();
    }
    else {
        // If no focusable elements, make container focusable temporarily
        container.setAttribute("tabindex", "-1");
        container.focus();
    }
    function handleKeyDown(e) {
        if (e.key !== "Tab")
            return;
        const elements = getFocusableElements(container);
        if (elements.length === 0)
            return;
        const firstEl = elements[0];
        const lastEl = elements[elements.length - 1];
        if (e.shiftKey) {
            // Shift+Tab: if on first element, go to last
            if (document.activeElement === firstEl) {
                e.preventDefault();
                lastEl.focus();
            }
        }
        else {
            // Tab: if on last element, go to first
            if (document.activeElement === lastEl) {
                e.preventDefault();
                firstEl.focus();
            }
        }
    }
    container.addEventListener("keydown", handleKeyDown);
    return {
        cleanup: () => {
            container.removeEventListener("keydown", handleKeyDown);
        }
    };
}
export function createModalFocusManager(modal, contentSelector) {
    let invoker = null;
    let focusTrap = null;
    let isModalOpen = false;
    function open(inv) {
        if (isModalOpen)
            return;
        invoker = inv ?? document.activeElement;
        isModalOpen = true;
        const content = modal.querySelector(contentSelector);
        if (content) {
            // Small delay to ensure modal is visible before focusing
            setTimeout(() => {
                focusTrap = createFocusTrap(content);
            }, 50);
        }
    }
    function close() {
        if (!isModalOpen)
            return;
        isModalOpen = false;
        // Cleanup focus trap
        if (focusTrap) {
            focusTrap.cleanup();
            focusTrap = null;
        }
        // Restore focus to invoker
        if (invoker && "focus" in invoker && typeof invoker.focus === "function") {
            invoker.focus();
        }
        invoker = null;
    }
    return {
        open,
        close,
        isOpen: () => isModalOpen
    };
}
