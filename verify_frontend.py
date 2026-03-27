import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f'file://{os.getcwd()}/swarm/tools/flow_studio_ui/index.html')

    # We load index.html, but if it requires JS to show the modal that involves an API call
    # we can bypass API timeouts by directly making the modal visible
    page.evaluate('document.getElementById("context-budget-modal").classList.add("open");')
    page.evaluate('document.getElementById("context-budget-modal").style.display = "flex";')

    page.screenshot(path='/tmp/screenshot.png')
    browser.close()
