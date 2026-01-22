from playwright.sync_api import sync_playwright, expect
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8000/index.html")

        # Wait for body to be ready
        page.wait_for_selector("body")

        # Press Tab to focus the skip link
        page.keyboard.press("Tab")

        # Wait for transition
        time.sleep(0.5)

        # Get the focused element
        focused = page.evaluate("document.activeElement")

        # Take a screenshot
        page.screenshot(path="verification/skip_link_focused_v2.png")

        # Verify the skip link is focused and visible
        skip_link = page.locator(".skip-to-content")
        expect(skip_link).to_be_visible()
        expect(skip_link).to_have_text("Skip to content")
        expect(skip_link).to_be_focused()

        print("Verification successful!")
        browser.close()

if __name__ == "__main__":
    run()
