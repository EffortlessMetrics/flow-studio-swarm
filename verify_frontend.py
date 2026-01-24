from playwright.sync_api import sync_playwright, expect
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Mock API responses
    # Mock /api/runs to return empty list
    page.route("**/api/runs**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"runs": [], "total": 0, "limit": 100, "offset": 0, "has_more": false}'
    ))

    # Mock other necessary APIs to avoid errors
    page.route("**/api/flows", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"flows": {}}'
    ))

    # Navigate to the UI
    page.goto("http://localhost:8000")

    # Wait for the empty state to appear
    # The empty state has class "fs-empty run-history-empty"
    # And specifically looking for the copy button
    copy_btn = page.locator(".copy-cmd-btn")

    # Expect it to be visible
    print("Waiting for copy button...")
    expect(copy_btn).to_be_visible()
    print("Copy button found!")

    # Check text inside code block
    code_block = page.locator(".empty-state-command code")
    expect(code_block).to_contain_text("make demo-run")
    print("Command text found!")

    # Take screenshot
    os.makedirs("/home/jules/verification", exist_ok=True)
    screenshot_path = "/home/jules/verification/empty_state.png"
    page.screenshot(path=screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
