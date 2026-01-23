#!/usr/bin/env python3
"""
run_layout_review.py - UI Review Capture Tool for Flow Studio

This tool captures DOM snapshots, SDK state, and screenshots for each
registered screen in Flow Studio. The artifacts are written to
swarm/runs/ui-review/<timestamp>/ for Claude/MCP consumption.

Usage:
    # Ensure Flow Studio is running first:
    make flow-studio

    # Then run the review:
    uv run swarm/tools/run_layout_review.py

    # Or with custom base URL:
    FLOW_STUDIO_BASE_URL=http://localhost:8000 uv run swarm/tools/run_layout_review.py

    # Use ux_manifest.json scenes as fallback (when API unavailable):
    uv run swarm/tools/run_layout_review.py --use-manifest

Output structure:
    swarm/runs/ui-review/<timestamp>/
        flows.default/
            dom.html          # HTML snapshot
            state.json        # SDK state (getState() + getGraphState())
            screenshot.png    # Visual capture (if Playwright available)
        flows.selftest/
            ...
        summary.json          # Run summary with all screens and errors

Dependencies:
    - httpx (required)
    - playwright (optional, for screenshots and SDK state extraction)

Issue: #21
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: uv add httpx")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

BASE_URL = os.environ.get("FLOW_STUDIO_BASE_URL", "http://localhost:5000")
RUN_ID = time.strftime("%Y%m%d-%H%M%S")
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "swarm" / "runs" / "ui-review" / RUN_ID
UX_MANIFEST_PATH = REPO_ROOT / "ux_manifest.json"


@dataclass
class ScreenCapture:
    """Captured artifacts for a single screen."""

    screen_id: str
    route: str
    dom_html: Optional[str] = None
    state_json: Optional[Dict[str, Any]] = None
    screenshot_path: Optional[Path] = None
    errors: List[str] = field(default_factory=list)


# ============================================================================
# Core Functions
# ============================================================================


def load_screens_from_manifest() -> List[Dict[str, Any]]:
    """
    Load screens from ux_manifest.json as a fallback when API is unavailable.

    The ux_manifest.json references layout_spec.ts which defines screens.
    This function provides a hardcoded fallback based on the manifest structure.
    """
    if not UX_MANIFEST_PATH.exists():
        return []

    try:
        _manifest = json.loads(UX_MANIFEST_PATH.read_text(encoding="utf-8"))  # noqa: F841
        # The manifest references layout_spec.ts but doesn't embed screens directly.
        # We define the known screens here as a fallback mirror of layout_spec.ts
        # This allows offline review without the API running.
        fallback_screens = [
            {
                "id": "flows.default",
                "route": "/",
                "title": "Flows - Default",
                "description": "Main Flow Studio screen with run selector, flow list, graph canvas, and inspector.",
            },
            {
                "id": "flows.selftest",
                "route": "/?modal=selftest",
                "title": "Flows - Selftest Modal",
                "description": "Selftest plan / results modal and controls.",
            },
            {
                "id": "flows.shortcuts",
                "route": "/?modal=shortcuts",
                "title": "Flows - Shortcuts Modal",
                "description": "Keyboard shortcuts reference modal.",
            },
            {
                "id": "flows.validation",
                "route": "/?tab=validation",
                "title": "Flows - Validation View",
                "description": "Governance validation results and FR status badges.",
            },
            {
                "id": "flows.tour",
                "route": "/?tour=first-edit",
                "title": "Flows - Tour Mode",
                "description": "Guided tour overlay with step-by-step navigation.",
            },
        ]
        return fallback_screens
    except Exception:
        return []


def fetch_layout_screens(client: httpx.Client) -> List[Dict[str, Any]]:
    """Fetch the layout screen registry from the API."""
    resp = client.get(f"{BASE_URL}/api/layout_screens", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("screens", [])


def fetch_html(client: httpx.Client, route: str) -> str:
    """Fetch the HTML for a given route."""
    url = f"{BASE_URL}{route}" if route.startswith("/") else f"{BASE_URL}/{route}"
    resp = client.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_sdk_state(client: httpx.Client) -> Optional[Dict[str, Any]]:
    """
    Fetch SDK state via a helper endpoint.

    Note: This requires the UI to expose state via an API endpoint,
    or we need to use Playwright to execute JS in the browser.
    For now, we return a placeholder until browser integration is added.
    """
    # Try to get state from health endpoint as a proxy
    try:
        resp = client.get(f"{BASE_URL}/api/health", timeout=30)
        if resp.status_code == 200:
            return {"health": resp.json(), "note": "SDK state requires browser execution"}
    except Exception:
        pass
    return None


@dataclass
class PlaywrightCaptureResult:
    """Result from Playwright-based capture."""

    screenshot_captured: bool = False
    sdk_state: Optional[Dict[str, Any]] = None
    dom_html: Optional[str] = None
    errors: List[str] = field(default_factory=list)


def capture_with_playwright(route: str, screenshot_path: Path) -> PlaywrightCaptureResult:
    """
    Capture screenshot, SDK state, and DOM using Playwright.

    This is more accurate than HTTP-based capture because it:
    - Waits for data-ui-ready="ready" before capture
    - Executes JavaScript to get SDK state (window.__flowStudio.getState())
    - Captures the actual rendered DOM

    Returns a PlaywrightCaptureResult with all captured data.
    """
    result = PlaywrightCaptureResult()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result.errors.append(
            "Playwright not installed. Install with: uv add playwright && playwright install chromium"
        )
        return result

    try:
        url = f"{BASE_URL}{route}" if route.startswith("/") else f"{BASE_URL}/{route}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Wait for UI ready signal
            try:
                page.wait_for_selector('html[data-ui-ready="ready"]', timeout=15000)
            except Exception as e:
                result.errors.append(f"Timeout waiting for data-ui-ready: {e}")
                # Continue anyway, we may still get partial data

            # Small delay for rendering to stabilize
            page.wait_for_timeout(500)

            # Capture screenshot
            try:
                page.screenshot(path=str(screenshot_path))
                result.screenshot_captured = True
            except Exception as e:
                result.errors.append(f"Screenshot failed: {e}")

            # Capture SDK state via JavaScript
            try:
                sdk_state = page.evaluate("""() => {
                    if (window.__flowStudio) {
                        return {
                            state: window.__flowStudio.getState ? window.__flowStudio.getState() : null,
                            graphState: window.__flowStudio.getGraphState ? window.__flowStudio.getGraphState() : null,
                            layoutScreens: window.__flowStudio.getLayoutScreens ? window.__flowStudio.getLayoutScreens() : null,
                            allUIIDs: window.__flowStudio.getAllKnownUIIDs ? window.__flowStudio.getAllKnownUIIDs() : null,
                            sdkVersion: "captured-via-playwright"
                        };
                    }
                    return { error: "window.__flowStudio not found" };
                }""")
                result.sdk_state = sdk_state
            except Exception as e:
                result.errors.append(f"SDK state extraction failed: {e}")

            # Capture rendered DOM
            try:
                result.dom_html = page.content()
            except Exception as e:
                result.errors.append(f"DOM capture failed: {e}")

            browser.close()

    except Exception as e:
        result.errors.append(f"Playwright capture failed: {e}")

    return result


def capture_screenshot_playwright(route: str, dest_path: Path) -> bool:
    """
    Capture a screenshot using Playwright (if available).

    Returns True if successful, False otherwise.

    NOTE: This is a legacy wrapper. Prefer capture_with_playwright() for
    full SDK state + DOM + screenshot capture.
    """
    result = capture_with_playwright(route, dest_path)
    return result.screenshot_captured


def capture_screen(
    client: Optional[httpx.Client], screen: Dict[str, Any], use_playwright: bool = True
) -> ScreenCapture:
    """
    Capture all artifacts for a single screen.

    Args:
        client: HTTP client for API-based capture (optional if using Playwright)
        screen: Screen specification dict with id, route, title, description
        use_playwright: If True, prefer Playwright for DOM/state/screenshot capture

    Returns:
        ScreenCapture with all captured artifacts and any errors
    """
    screen_id = screen["id"]
    route = screen["route"]

    capture = ScreenCapture(screen_id=screen_id, route=route)
    dest = OUT_DIR / screen_id
    dest.mkdir(parents=True, exist_ok=True)

    screenshot_path = dest / "screenshot.png"

    # Try Playwright-based capture first (more accurate)
    if use_playwright:
        pw_result = capture_with_playwright(route, screenshot_path)

        # Use Playwright DOM if available
        if pw_result.dom_html:
            capture.dom_html = pw_result.dom_html
            (dest / "dom.html").write_text(capture.dom_html, encoding="utf-8")

        # Use Playwright SDK state if available
        if pw_result.sdk_state:
            capture.state_json = pw_result.sdk_state
            (dest / "state.json").write_text(
                json.dumps(capture.state_json, indent=2), encoding="utf-8"
            )

        # Screenshot
        if pw_result.screenshot_captured:
            capture.screenshot_path = screenshot_path

        # Collect errors
        capture.errors.extend(pw_result.errors)

    # Fallback to HTTP-based capture if Playwright didn't get DOM
    if not capture.dom_html and client:
        try:
            base_route = route.split("?")[0] if "?" in route else route
            capture.dom_html = fetch_html(client, base_route)
            (dest / "dom.html").write_text(capture.dom_html, encoding="utf-8")
        except Exception as e:
            capture.errors.append(f"Failed to fetch HTML via HTTP: {e}")

    # Fallback to API-based state if Playwright didn't get it
    if not capture.state_json and client:
        try:
            capture.state_json = fetch_sdk_state(client)
            if capture.state_json:
                (dest / "state.json").write_text(
                    json.dumps(capture.state_json, indent=2), encoding="utf-8"
                )
        except Exception as e:
            capture.errors.append(f"Failed to fetch state via API: {e}")

    # Write skip marker if no screenshot
    if not capture.screenshot_path:
        (dest / "screenshot.skip").write_text(
            "Screenshot not captured. Install Playwright: uv add playwright && playwright install chromium"
        )

    # Write screen metadata
    (dest / "screen_spec.json").write_text(json.dumps(screen, indent=2), encoding="utf-8")

    return capture


def write_summary(captures: List[ScreenCapture]) -> None:
    """Write a summary report of all captured screens."""
    summary = {
        "run_id": RUN_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_url": BASE_URL,
        "screens": [],
    }

    for capture in captures:
        screen_summary = {
            "id": capture.screen_id,
            "route": capture.route,
            "has_dom": capture.dom_html is not None,
            "has_state": capture.state_json is not None,
            "has_screenshot": capture.screenshot_path is not None,
            "errors": capture.errors,
        }
        summary["screens"].append(screen_summary)

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Capture DOM, SDK state, and screenshots for Flow Studio screens"
    )
    parser.add_argument(
        "--use-manifest",
        action="store_true",
        help="Use ux_manifest.json fallback screens instead of fetching from API",
    )
    parser.add_argument(
        "--no-playwright",
        action="store_true",
        help="Disable Playwright-based capture (HTTP only, no screenshots/SDK state)",
    )
    args = parser.parse_args()

    print("[ui-review] Starting layout review")
    print(f"[ui-review] Base URL: {BASE_URL}")
    print(f"[ui-review] Output: {OUT_DIR}")
    print(f"[ui-review] Playwright capture: {'disabled' if args.no_playwright else 'enabled'}")

    # Ensure output directory exists
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    captures: List[ScreenCapture] = []
    screens: List[Dict[str, Any]] = []
    client: Optional[httpx.Client] = None

    # Determine screen source
    if args.use_manifest:
        print("[ui-review] Using ux_manifest.json fallback screens")
        screens = load_screens_from_manifest()
        if not screens:
            print("[ui-review] ERROR: Could not load screens from ux_manifest.json")
            return 1
        print(f"[ui-review] Found {len(screens)} screens from manifest fallback")
    else:
        # Try API first
        try:
            client = httpx.Client()
            client.get(f"{BASE_URL}/api/health", timeout=5)
            screens = fetch_layout_screens(client)
            print(f"[ui-review] Found {len(screens)} screens from /api/layout_screens")
        except Exception as e:
            print(f"[ui-review] WARNING: Flow Studio API not reachable at {BASE_URL}")
            print(f"[ui-review] Error: {e}")
            print("[ui-review] Falling back to ux_manifest.json screens...")

            screens = load_screens_from_manifest()
            if not screens:
                print("[ui-review] ERROR: No fallback screens available")
                print("[ui-review] Start Flow Studio with: make flow-studio")
                return 1
            print(f"[ui-review] Found {len(screens)} screens from manifest fallback")

    # Capture each screen
    for screen in screens:
        screen_id = screen["id"]
        print(f"[ui-review] Capturing screen: {screen_id} ({screen['route']})")
        capture = capture_screen(client, screen, use_playwright=not args.no_playwright)
        captures.append(capture)

        if capture.errors:
            for err in capture.errors:
                print(f"  [warn] {err}")

    # Cleanup
    if client:
        client.close()

    # Write summary
    write_summary(captures)

    # Report results
    print("\n[ui-review] Complete!")
    print(f"[ui-review] Artifacts written to: {OUT_DIR}")
    print(f"[ui-review] Screens captured: {len(captures)}")

    success_count = sum(1 for c in captures if not c.errors)
    if success_count < len(captures):
        print(f"[ui-review] Screens with errors: {len(captures) - success_count}")

    # List artifact locations
    print("\n[ui-review] Artifact summary:")
    for capture in captures:
        status = "OK" if not capture.errors else f"WARN ({len(capture.errors)} errors)"
        has_screenshot = "+" if capture.screenshot_path else "-"
        has_state = "+" if capture.state_json else "-"
        has_dom = "+" if capture.dom_html else "-"
        print(
            f"  {capture.screen_id}: [{status}] dom:{has_dom} state:{has_state} screenshot:{has_screenshot}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
