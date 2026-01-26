from playwright.sync_api import sync_playwright

def test_a11y(page):
    # Mock the runs API to return empty list to trigger "No runs" state
    page.route("**/api/runs*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"runs": [], "total": 0}'
    ))

    # Mock other APIs to prevent errors
    page.route("**/api/flows", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"flows": {}}'
    ))
    page.route("**/api/runs/active", lambda route: route.fulfill(
         status=200, content_type="application/json", body='{"id": null}'
    ))
    page.route("**/api/settings", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{}'
    ))

    page.goto("http://localhost:8000/swarm/tools/flow_studio_ui/index.html")

    # Wait for the empty state to appear
    page.wait_for_selector(".fs-empty-icon")

    # Check if aria-hidden is present
    icon = page.locator(".fs-empty-icon").first
    print(f"Icon HTML: {icon.evaluate('el => el.outerHTML')}")

    if icon.get_attribute("aria-hidden") == "true":
        print("SUCCESS: .fs-empty-icon has aria-hidden='true'")
    else:
        print("FAILURE: .fs-empty-icon MISSING aria-hidden='true'")

    page.screenshot(path="verification/verification.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_a11y(page)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
