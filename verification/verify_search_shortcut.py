from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print("Navigating to Flow Studio...")
            page.goto("http://127.0.0.1:5000")

            # Wait for search input
            page.wait_for_selector(".search-input")
            print("Search input found.")

            # Take screenshot of the header area (initial state)
            header = page.locator("header")
            header.screenshot(path="verification/search_shortcut_visible.png")
            print("Screenshot taken: visible")

            # Focus the input
            page.focus(".search-input")
            # Wait a bit for CSS transition/update if any
            time.sleep(0.5)
            header.screenshot(path="verification/search_shortcut_focused.png")
            print("Screenshot taken: focused (should be hidden)")

            # Type something
            page.fill(".search-input", "test")
            page.evaluate("document.activeElement.blur()") # Blur to check placeholder-shown logic
            time.sleep(0.5)
            header.screenshot(path="verification/search_shortcut_filled.png")
            print("Screenshot taken: filled (should be hidden)")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
