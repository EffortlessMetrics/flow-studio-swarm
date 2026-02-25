from playwright.sync_api import sync_playwright

def verify_clear_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to Flow Studio...")
        try:
            page.goto("http://localhost:5000")
            page.wait_for_selector('html[data-ui-ready="ready"]', timeout=10000)
            print("UI ready.")
        except Exception as e:
            print(f"Error loading page: {e}")
            # Continue anyway to see if elements exist

        search_input = page.locator('#search-input')
        search_clear = page.locator('#search-clear')

        # Check initial state
        if search_clear.is_visible():
            print("WARNING: Clear button visible initially.")
        else:
            print("SUCCESS: Clear button hidden initially.")

        # Type text
        print("Typing 'test query'...")
        search_input.fill("test query")

        # Check visible
        if search_clear.is_visible():
            print("SUCCESS: Clear button visible after typing.")
            page.screenshot(path="verification_visible.png")

            # Click clear
            search_clear.click()
            print("Clicked clear button.")

            # Check empty
            val = search_input.input_value()
            if val == "":
                print("SUCCESS: Input empty after clear.")
            else:
                print(f"ERROR: Input value '{val}' after clear.")

            # Check hidden
            if not search_clear.is_visible():
                print("SUCCESS: Clear button hidden after clear.")
            else:
                print("ERROR: Clear button visible after clear.")

            page.screenshot(path="verification_cleared.png")

        else:
            print("ERROR: Clear button NOT visible after typing.")
            page.screenshot(path="error_not_visible.png")

        browser.close()

if __name__ == "__main__":
    verify_clear_button()
