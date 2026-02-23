from playwright.sync_api import sync_playwright, expect

def verify_clear_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8000")

        # Wait for search input
        search_input = page.get_by_role("textbox", name="Search flows, steps, agents, and artifacts")
        search_input.wait_for()

        # Type something
        search_input.fill("test search")

        # Verify clear button appears
        clear_btn = page.get_by_role("button", name="Clear search")
        expect(clear_btn).to_be_visible()

        # Take screenshot with text
        page.screenshot(path="verification_with_text.png")

        # Click clear button
        clear_btn.click()

        # Verify input is empty
        expect(search_input).to_have_value("")

        # Verify button disappears (wait for CSS transition if any, or just check visibility)
        # It uses display: none via CSS ~ selector
        expect(clear_btn).not_to_be_visible()

        # Take screenshot cleared
        page.screenshot(path="verification_cleared.png")

        browser.close()

if __name__ == "__main__":
    verify_clear_search()
