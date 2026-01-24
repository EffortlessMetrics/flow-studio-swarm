from playwright.sync_api import sync_playwright, expect
import time

def verify_kbd_styles():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the local server
        page.goto("http://localhost:8000/index.html")

        # Wait for loading to finish (or at least for the UI to settle)
        # Since we are just serving static files and the API calls will fail (404),
        # we expect the basic UI shell to load.

        # 1. Verify Inspector Panel Hint
        # The inspector panel is #details. It usually has some default content or loading state.
        # However, without API backend, it might show error or empty state.
        # In flow-studio-app.ts, showFlowDetails populates it. But that depends on data.
        # Wait, if I can't load data, I might not see the hint in the inspector panel easily without mocking.

        # However, the shortcuts modal is always accessible via the "?" key or help button.

        # Press '?' to open shortcuts modal
        page.keyboard.press("?")

        # Wait for modal to appear
        modal = page.locator("#shortcuts-modal")
        expect(modal).to_be_visible()

        # Take screenshot of the modal
        page.screenshot(path="verification_modal.png")
        print("Screenshot saved to verification_modal.png")

        browser.close()

if __name__ == "__main__":
    verify_kbd_styles()
