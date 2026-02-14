from playwright.sync_api import sync_playwright, expect

def verify_search_clear():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to Flow Studio
        page.goto("http://127.0.0.1:5000")

        # Verify search input exists
        search_input = page.locator('[data-uiid="flow_studio.header.search.input"]')
        expect(search_input).to_be_visible()

        # Verify clear button exists and is hidden initially
        search_clear = page.locator('[data-uiid="flow_studio.header.search.clear"]')
        expect(search_clear).to_be_hidden()

        # Type into search input
        search_input.fill("test query")

        # Verify clear button becomes visible
        expect(search_clear).to_be_visible()

        # Take screenshot with text and clear button
        page.screenshot(path="verification/search_with_text.png")

        # Click clear button
        search_clear.click()

        # Verify input is cleared
        expect(search_input).to_have_value("")

        # Verify clear button is hidden again
        expect(search_clear).to_be_hidden()

        # Verify input is focused
        expect(search_input).to_be_focused()

        # Take screenshot after clearing
        page.screenshot(path="verification/search_cleared.png")

        browser.close()

if __name__ == "__main__":
    verify_search_clear()
