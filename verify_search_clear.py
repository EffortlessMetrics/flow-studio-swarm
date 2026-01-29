from playwright.sync_api import sync_playwright, expect

def verify_search_clear():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://localhost:8000/index.html")

            # Locate elements
            search_input = page.get_by_placeholder("Search flows, steps, agents, artifacts...")
            clear_btn = page.locator("#search-clear")

            # Initial state: clear button hidden
            expect(clear_btn).not_to_be_visible()

            # Type something
            search_input.fill("test query")

            # Verify clear button visible
            expect(clear_btn).to_be_visible()
            page.screenshot(path="search_filled.png")
            print("Screenshot saved: search_filled.png")

            # Click clear
            clear_btn.click()

            # Verify input cleared and focused
            expect(search_input).to_have_value("")
            expect(search_input).to_be_focused()

            # Verify clear button hidden again
            expect(clear_btn).not_to_be_visible()

            page.screenshot(path="search_cleared.png")
            print("Screenshot saved: search_cleared.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_search_clear()
