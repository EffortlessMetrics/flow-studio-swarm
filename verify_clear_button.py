from playwright.sync_api import sync_playwright
import os

def verify(page):
    page.goto("http://127.0.0.1:5000")

    # Wait for search input
    search_input = page.locator('[data-uiid="flow_studio.header.search.input"]')
    search_input.wait_for()

    # Type text
    search_input.fill("test")

    # Verify clear button visible
    clear_btn = page.locator('[data-uiid="flow_studio.header.search.clear"]')
    clear_btn.wait_for(state="visible")

    # Screenshot with text
    page.screenshot(path="/home/jules/verification/search_with_text.png")

    # Click clear
    clear_btn.click()

    # Verify input empty and button hidden
    assert search_input.input_value() == ""
    clear_btn.wait_for(state="hidden")

    # Screenshot empty
    page.screenshot(path="/home/jules/verification/search_cleared.png")

if __name__ == "__main__":
    os.makedirs("/home/jules/verification", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            verify(page)
        finally:
            browser.close()
