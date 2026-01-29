from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Navigate to the local server
            page.goto("http://localhost:8000/swarm/tools/flow_studio_ui/index.html")

            # Wait for UI to be ready (or at least loaded)
            page.wait_for_selector('html[data-ui-ready]')

            # Locate search input and clear button
            search_input = page.locator('[data-uiid="flow_studio.header.search.input"]')
            clear_btn = page.locator('[data-uiid="flow_studio.header.search.clear"]')

            # Ensure input is empty and button is hidden initially
            expect(search_input).to_have_value("")
            expect(clear_btn).not_to_be_visible()

            # Type something
            search_input.fill("hello")

            # Verify button becomes visible
            expect(clear_btn).to_be_visible()

            # Take screenshot of visible button
            page.screenshot(path="verification/search_active.png")

            # Click clear button
            clear_btn.click()

            # Verify input is cleared and button is hidden
            expect(search_input).to_have_value("")
            expect(clear_btn).not_to_be_visible()

            # Verify input has focus
            expect(search_input).to_be_focused()

            # Take final screenshot
            page.screenshot(path="verification/search_cleared.png")

            print("Verification successful!")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification/error.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    run()
