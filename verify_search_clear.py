from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()

    print("Navigating to Flow Studio...")
    page.goto("http://localhost:5000")

    # Wait for page to load
    page.wait_for_selector("#search-input")

    print("Typing search query...")
    search_input = page.locator("#search-input")
    search_input.fill("test query")

    # Wait for clear button to appear
    clear_button = page.locator("#search-clear")
    if clear_button.is_visible():
        print("Clear button is visible.")
    else:
        print("ERROR: Clear button is NOT visible.")

    page.screenshot(path="verification_search_filled.png")

    print("Clicking clear button...")
    clear_button.click()

    # Verify input is cleared
    value = search_input.input_value()
    if value == "":
        print("Search input cleared successfully.")
    else:
        print(f"ERROR: Search input not cleared. Value: '{value}'")

    # Verify button is hidden
    if not clear_button.is_visible():
        print("Clear button is hidden.")
    else:
        print("ERROR: Clear button is still visible.")

    page.screenshot(path="verification_search_cleared.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
