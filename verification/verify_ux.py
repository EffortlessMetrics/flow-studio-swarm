from playwright.sync_api import sync_playwright, expect

def test_ux(page):
    page.goto("http://localhost:5000")

    # Wait for UI ready
    page.wait_for_selector("html[data-ui-ready='ready']")

    # 1. Verify Inspector UX Improvement
    print("Verifying Inspector UX...")
    # The inspector should now use quick-commands even when a flow is loaded (via showFlowDetails logic)
    details = page.locator("#details")
    expect(details).to_be_visible()

    # Check for Quick Commands in Inspector
    quick_commands = details.locator(".quick-commands")
    expect(quick_commands).to_be_visible()

    # Check individual command line
    command_line = quick_commands.locator(".command-line").first
    expect(command_line).to_be_visible()

    # Check for Copy button in command line
    cmd_copy_btn = command_line.locator("button.copy-btn")
    expect(cmd_copy_btn).to_be_visible()

    # 2. Verify Canvas Empty State UX Fix
    print("Verifying Canvas Empty State...")

    # Force empty state to be visible (simulate no runs loaded or manual toggle)
    page.evaluate('document.getElementById("canvas-empty-state").style.display = "flex"')

    # Verify Empty State is visible
    empty_state = page.locator("#canvas-empty-state")
    expect(empty_state).to_be_visible()

    # Verify pointer-events on container
    pointer_events = empty_state.evaluate("el => getComputedStyle(el).pointerEvents")
    print(f"Empty State pointer-events: {pointer_events}")
    assert pointer_events == "none", f"Expected pointer-events: none, got {pointer_events}"

    # Verify Legend z-index
    legend = page.locator("#legend")
    z_index = legend.evaluate("el => getComputedStyle(el).zIndex")
    print(f"Legend z-index: {z_index}")
    assert z_index == "4", f"Expected z-index: 4, got {z_index}"

    # Verify Copy Button (inside Empty State) is clickable
    copy_btn = empty_state.locator("button.copy-btn").first
    expect(copy_btn).to_be_visible()

    # Check computed pointer-events of the button (should be auto)
    btn_pointer = copy_btn.evaluate("el => getComputedStyle(el).pointerEvents")
    print(f"Copy button pointer-events: {btn_pointer}")
    assert btn_pointer == "auto", f"Expected pointer-events: auto, got {btn_pointer}"

    # Click it (verifies interactability)
    copy_btn.click()

    page.screenshot(path="verification/verification.png")
    print("Verification successful!")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        try:
            test_ux(page)
        finally:
            browser.close()
