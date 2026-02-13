from playwright.sync_api import sync_playwright, expect
import os

def verify_search_clear(page):
    page.goto("http://127.0.0.1:5000")

    # 1. Type into search input
    search_input = page.get_by_role("textbox", name="Search flows, steps, agents, and artifacts")
    search_input.fill("test query")

    # 2. Verify clear button appears
    clear_btn = page.locator("#search-clear")
    # Wait for visibility (CSS transition might delay it slightly, but playwright waits)
    expect(clear_btn).to_be_visible()

    page.screenshot(path="/home/jules/verification/1_search_filled.png")
    print("Screenshot 1: Search filled, clear button visible")

    # 3. Click clear button
    clear_btn.click()

    # 4. Verify input is empty
    expect(search_input).to_have_value("")

    # 5. Verify clear button disappears
    expect(clear_btn).not_to_be_visible()

    page.screenshot(path="/home/jules/verification/2_search_cleared.png")
    print("Screenshot 2: Search cleared, button hidden")

if __name__ == "__main__":
    os.makedirs("/home/jules/verification", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_search_clear(page)
        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="/home/jules/verification/failure.png")
            raise
        finally:
            browser.close()
