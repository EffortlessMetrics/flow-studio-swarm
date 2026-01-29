from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://localhost:8000/index.html")

            # Locate search input
            search_input = page.locator("#search-input")
            clear_btn = page.locator("#search-clear")

            # Initial state: clear button hidden
            expect(clear_btn).not_to_be_visible()

            # Type something
            search_input.fill("test")

            # State: clear button visible
            expect(clear_btn).to_be_visible()

            # Screenshot 1: Button Visible
            page.screenshot(path="verification_visible.png")
            print("Taken screenshot: verification_visible.png")

            # Click clear
            clear_btn.click()

            # State: input empty, clear button hidden, input focused
            expect(search_input).to_have_value("")
            expect(clear_btn).not_to_be_visible()
            expect(search_input).to_be_focused()

            # Screenshot 2: cleared
            page.screenshot(path="verification_cleared.png")
            print("Taken screenshot: verification_cleared.png")

        finally:
            browser.close()

if __name__ == "__main__":
    run()
