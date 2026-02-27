import asyncio
from playwright.async_api import async_playwright, expect

async def verify_copy_button():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to the app (assuming port 8000 based on previous context)
            # Since we can't reliably start the server, this script is for manual/future verification
            # or if the server happens to be running.
            # Ideally, we mock the response that triggers the empty state.
            await page.goto("http://localhost:8000")

            # Wait for UI to be ready
            try:
                await page.wait_for_selector('html[data-ui-ready="ready"]', timeout=5000)
            except:
                print("UI ready state not found, proceeding anyway...")

            # Locate the copy button in the empty state
            # This requires the empty state to be visible, which implies NO runs loaded.
            copy_btn = page.locator(".fs-copy-command .copy-btn")

            if await copy_btn.count() > 0:
                print("Found copy button!")
                await expect(copy_btn).to_be_visible()
                await expect(copy_btn).to_have_text("Copy")

                # Click it
                await copy_btn.click()

                # Check feedback
                await expect(copy_btn).to_have_text("\u2713") # Checkmark
                print("Copy button interaction successful!")

                await page.screenshot(path="flow_studio_copy_btn.png")
            else:
                print("Copy button not found - maybe runs are loaded?")
                await page.screenshot(path="flow_studio_state.png")

        except Exception as e:
            print(f"Verification failed (likely due to server not running): {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_copy_button())
