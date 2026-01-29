from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8000")

        # Wait for search input
        search_input = page.locator("#search-input")
        expect(search_input).to_be_visible()

        # Type something
        search_input.fill("test query")

        # Verify clear button appears
        clear_btn = page.locator("#search-clear")
        expect(clear_btn).to_be_visible()

        # Take screenshot of visible button
        page.screenshot(path="verification_visible.png")

        # Click clear button
        clear_btn.click()

        # Verify input is empty
        expect(search_input).to_have_value("")

        # Verify clear button is hidden (CSS should hide it)
        # Note: Playwright .to_be_visible() checks for display:none
        expect(clear_btn).not_to_be_visible()

        # Take screenshot of hidden button
        page.screenshot(path="verification_hidden.png")

        print("Verification successful!")
        browser.close()

if __name__ == "__main__":
    run()
