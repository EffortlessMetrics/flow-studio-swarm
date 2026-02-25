from playwright.sync_api import sync_playwright
import os
import time

def verify_search_clear_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app
        print("Navigating to http://localhost:8000")
        page.goto("http://localhost:8000")

        # Wait for search input
        print("Waiting for search input")
        search_input = page.locator("#search-input")
        search_input.wait_for(state="visible", timeout=5000)

        # Type something
        print("Typing 'test query'")
        search_input.fill("test query")

        # Locate clear button
        clear_btn = page.locator("#search-clear-btn")

        # Wait a bit for CSS transition/rendering if any
        time.sleep(0.5)

        # Verify clear button is visible
        if not clear_btn.is_visible():
            print("FAILURE: Clear button NOT visible after typing")
            page.screenshot(path="verification_fail_visible.png")
            browser.close()
            return

        print("SUCCESS: Clear button visible")
        page.screenshot(path="verification_visible.png")

        # Click clear button
        print("Clicking clear button")
        clear_btn.click()

        # Wait a bit
        time.sleep(0.5)

        # Verify input is empty
        value = search_input.input_value()
        if value != "":
            print(f"FAILURE: Input not empty after clear: '{value}'")
            page.screenshot(path="verification_fail_clear.png")
            browser.close()
            return

        print("SUCCESS: Input cleared")

        # Verify clear button is hidden
        if clear_btn.is_visible():
             print("FAILURE: Clear button still visible after clear")
             page.screenshot(path="verification_fail_hidden.png")
             browser.close()
             return

        print("SUCCESS: Clear button hidden")
        page.screenshot(path="verification_final.png")

        browser.close()

if __name__ == "__main__":
    verify_search_clear_button()
