from playwright.sync_api import sync_playwright, expect
import os

def verify_clear_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Log console messages
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))

        page.goto("http://localhost:8000")

        # Wait for UI ready
        print("Waiting for UI ready...")
        expect(page.locator("html")).to_have_attribute("data-ui-ready", "ready", timeout=10000)
        print("UI is ready.")

        # 1. Type into search input
        search_input = page.locator("#search-input")
        search_input.fill("test search")

        # 2. Verify clear button appears
        clear_btn = page.locator("#search-clear-btn")
        expect(clear_btn).to_be_visible()
        print("Clear button is visible.")

        # Screenshot with text and button
        os.makedirs("/home/jules/verification", exist_ok=True)
        page.screenshot(path="/home/jules/verification/search_with_text.png")

        # Debug: Check if element exists
        exists = page.evaluate("!!document.getElementById('search-clear-btn')")
        print(f"Button exists in DOM: {exists}")

        # 3. Click clear button using JS evaluation
        print("Clicking clear button via JS...")
        page.evaluate("document.getElementById('search-clear-btn').click()")
        print("JS Click command sent.")

        # 4. Verify input is cleared
        print("Verifying input is cleared...")
        expect(search_input).to_have_value("")
        print("Input cleared.")

        # 5. Verify input is focused
        expect(search_input).to_be_focused()

        # 6. Verify clear button is hidden
        expect(clear_btn).not_to_be_visible()

        # Screenshot after clear
        page.screenshot(path="/home/jules/verification/search_cleared.png")

        browser.close()

if __name__ == "__main__":
    verify_clear_button()
